import os
import sys
import signal
import logging
import asyncio
import argparse
from typing import List
from asyncio import Event
from asyncio.streams import StreamReader, StreamWriter
from contextlib import asynccontextmanager
from jobs.messages import deserialize_command, Job, GetJobsReply, StartJobs, CancelJobs
from jobs.jobsd.runner import JobFailedException
from jobs.jobsd.job_graphs import get_job_nodes_trees, get_root_jobs, JobNode
from jobs.jobsd.jobids import JobIDs
from jobs.jobsd.runners import get_runners
import conf

log = logging.getLogger(__name__)

READ_CHUNK_SIZE = 1024


class JobsThrottle:
    def __init__(self, max_jobs):
        self.max_jobs = max_jobs
        self._running_jobs = 0
        self.running_jobs_changed = Event()

    @property
    def running_jobs(self):
        return self._running_jobs

    @running_jobs.setter
    def running_jobs(self, v):
        self._running_jobs = v
        self.running_jobs_changed.set()

    @asynccontextmanager
    async def jobs_limit(self):
        while self.running_jobs >= self.max_jobs:
            await self.running_jobs_changed.wait()
            self.running_jobs_changed.clear()

        try:
            self.running_jobs += 1
            yield
        finally:
            # make sure we count down,
            # event if the job failed or was cancelled
            self.running_jobs -= 1


class JobsTable:
    def __init__(self, job_runners):
        self.job_ids = JobIDs(conf.DATABASE_DIR)
        self.jobs_nodes = set()
        self.job_tasks = {}
        self.job_runners = job_runners
        self.throttle = JobsThrottle(conf.JOBSD_MAX_JOBS)

    def command_received(self):
        for runner in self.job_runners.values():
            runner.command_received()

    def add_pending_job(self, job_node: JobNode):
        def _expand_path_template(path, job_id):
            """
            emulate slurms's '%j' template,
            i.e. replace it with job ID
            """
            return path.replace("%j", f"{job_id}")

        job_id = self.job_ids.next()

        job_node.job.id = job_id
        job_node.job.stdout = _expand_path_template(job_node.job.stdout, job_id)
        job_node.job.stderr = _expand_path_template(job_node.job.stderr, job_id)

        self.jobs_nodes.add(job_node)

    def get_jobs(self) -> List[Job]:
        return [node.job for node in self.jobs_nodes]

    def _get_runner(self, job_node):
        return self.job_runners[job_node.run_on].run_job

    async def _throttled_runner(self, job_node):
        job = job_node.job
        runner = self._get_runner(job_node)

        async with self.throttle.jobs_limit():
            job.mark_as_started()
            await runner(job.program, job.arguments, job.stdout, job.stderr)

    def start_job(self, job_node: JobNode):
        log.info(f"run job '{job_node.job.name}' on {job_node.run_on}")
        job_task = asyncio.create_task(self._throttled_runner(job_node))

        self.job_tasks[job_node.job.id] = job_task

        return job_task

    def cancel_job(self, job_id):
        log.info(f"canceling job {job_id}")
        if job_id not in self.job_tasks:
            log.info(f"unknown job {job_id}")
            return

        job_task = self.job_tasks[job_id]
        if job_task.done():
            log.info(f"job {job_id} already finished")
            return

        job_task.cancel()

    def job_finished(self, job_node: JobNode):
        # if the job is running,
        # remove it's asyncio task entry
        job_id = job_node.job.id
        if job_id in self.job_tasks:
            del self.job_tasks[job_id]

        # remove the job node entry
        self.jobs_nodes.remove(job_node)


async def run_jobs_tree(root: JobNode, jobs_table: JobsTable):
    try:
        # run all dependencies
        co = [run_jobs_tree(dep, jobs_table) for dep in root.run_after]
        await asyncio.gather(*co)

        # run this job
        await jobs_table.start_job(root)

    except JobFailedException:
        raise

    finally:
        jobs_table.job_finished(root)


async def run_jobs_roots(roots, jobs_table):
    try:
        co = [run_jobs_tree(tree, jobs_table) for tree in roots]
        await asyncio.gather(*co)
    except JobFailedException:
        # we can ignore exception here, as it have been
        # handled while it was unwinding the call stack
        pass


async def start_jobs(command: StartJobs, jobs_table):
    log.info(f"starting '{command.name}' jobs set")

    job_nodes = get_job_nodes_trees(command.jobs)
    for job_node in job_nodes:
        jobs_table.add_pending_job(job_node)

    job_roots = get_root_jobs(job_nodes)
    await run_jobs_roots(job_roots, jobs_table)


def get_jobs(jobs_table: JobsTable):
    reply = GetJobsReply()
    reply.jobs = jobs_table.get_jobs()

    return reply


def cancel_jobs(command: CancelJobs, jobs_table: JobsTable):
    for job_id in command.job_ids:
        jobs_table.cancel_job(job_id)


async def handle_command(command, jobs_table: JobsTable):
    jobs_table.command_received()

    if command.LABEL == "get_jobs":
        return get_jobs(jobs_table)
    elif command.LABEL == "start_jobs":
        asyncio.create_task(start_jobs(command, jobs_table))
    elif command.LABEL == "cancel_jobs":
        cancel_jobs(command, jobs_table)
    else:
        assert False, f"unexpected command {command.LABEL}"


async def read_long_line(reader: StreamReader):
    """
    read input from stream reader until we find '\n'

    We need this custom function, as the standard StreamReader.readline()
    method have a limit on how long lines it can read.

    We can hit that limit, when processing a large 'start_jobs' command.
    """
    line = b""

    # read data in chunks, until we find '\n'
    while True:
        chunk = await reader.read(READ_CHUNK_SIZE)
        line += chunk

        if chunk[-1] == 10:
            # '\n' found, we are done
            break

    return line


async def client_connected(
    reader: StreamReader, writer: StreamWriter, jobs_table: JobsTable
):
    line = await read_long_line(reader)
    command = deserialize_command(line)
    reply = await handle_command(command, jobs_table)

    if reply is not None:
        reply_json = reply.serialize()
        writer.write(reply_json.encode())

    writer.close()
    await writer.wait_closed()


def init_signals():
    loop = asyncio.get_event_loop()
    exit_event = asyncio.Event()
    for signum in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(signum, lambda: exit_event.set())

    return exit_event


async def run():
    exit_event = init_signals()

    jobs_table = JobsTable(get_runners())

    server = await asyncio.start_unix_server(
        lambda r, w: client_connected(r, w, jobs_table), conf.JOBSD_SOCKET
    )
    serv_task = asyncio.create_task(server.serve_forever())
    log.info(f"reading commands socket '{conf.JOBSD_SOCKET}'")

    # run until we get a signal to exit
    await exit_event.wait()

    # disconnect from the socket and exit
    serv_task.cancel()
    log.info("bye bye")


def parse_args():
    parser = argparse.ArgumentParser(description="jobs daemon")

    parser.add_argument("--uid", type=int, help="run with specified UID (user ID)")
    parser.add_argument("--gid", type=int, help="run with specified GID (group ID)")

    return parser.parse_args()


def set_uid_gid(uid, gid):
    if gid is not None:
        os.setgid(gid)

    if uid is not None:
        os.setuid(uid)


def setup_daemon():
    args = parse_args()

    # set-up logging to goto stdout
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(name)s: %(message)s",
    )
    # make sure the log is flushed after each new line
    sys.stdout.reconfigure(line_buffering=True)

    # switch uid/gid if requested
    set_uid_gid(args.uid, args.gid)


def main():
    setup_daemon()
    asyncio.run(run())
