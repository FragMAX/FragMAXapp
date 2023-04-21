import os
import sys
import signal
import logging
import asyncio
import argparse
from typing import Set, Dict, Optional, Tuple
from asyncio import Event, Task
from asyncio.streams import StreamReader, StreamWriter
from contextlib import asynccontextmanager
from jobs.messages import deserialize_command, StartJobsSet, CancelJobs
from jobs.jobsd.runner import JobFailedException
from jobs.jobsd.nodes import (
    get_job_nodes,
    get_root_nodes,
    mark_job_started,
    mark_job_finished,
    JobNode,
)
from jobs.jobsd.runners import get_runners
import conf

log = logging.getLogger(__name__)

READ_CHUNK_SIZE = 1024


class CPUThrottle:
    def __init__(self, max_cpus):
        self._max_cpus = max_cpus
        self._cpus_allocated = 0
        self._cpus_allocated_changed = Event()

    @property
    def cpus_allocated(self):
        return self._cpus_allocated

    @cpus_allocated.setter
    def cpus_allocated(self, v):
        self._cpus_allocated = v
        self._cpus_allocated_changed.set()

    @asynccontextmanager
    async def jobs_limit(self, cpus):
        while self.cpus_allocated + cpus > self._max_cpus:
            log.info(
                f"CPU allocation exhausted, allocated {self.cpus_allocated}/{self._max_cpus}"
            )
            await self._cpus_allocated_changed.wait()
            self._cpus_allocated_changed.clear()

        try:
            self.cpus_allocated += cpus
            log.info(f"allocated {cpus}, total allocation {self.cpus_allocated}")
            yield
        finally:
            # make sure we count down,
            # event if the job failed or was cancelled
            self.cpus_allocated -= cpus


class NOPThrottle:
    """
    No-OP throttle, i.e. one that does not limit
    jobs launching in any ways
    """

    @asynccontextmanager
    async def jobs_limit(self, cpus):
        yield


def _get_throttle(max_cpus):
    if max_cpus:
        return CPUThrottle(max_cpus)

    # no CPU limit requested, use a No-op throttle
    return NOPThrottle()


class _JobTasks:
    def __init__(self) -> None:
        self._tasks: Dict[Tuple[str, str], Task] = {}

    def add(self, project_id, job_id, task: Task):
        self._tasks[(project_id, job_id)] = task

    def get(self, project_id, job_id) -> Optional[Task]:
        return self._tasks.get((project_id, job_id))

    def remove(self, project_id, job_id):
        """
        remove a task with specified IDs combo
        if task is not found, this becomes a NOP
        """
        task_key = (project_id, job_id)
        if task_key in self._tasks:
            del self._tasks[task_key]


class JobsTable:
    def __init__(self, job_runners, max_cpus: Optional[int]):
        self.jobs_nodes: Set[JobNode] = set()
        self.job_tasks = _JobTasks()
        self.job_runners = job_runners
        self.throttle = _get_throttle(max_cpus)

    def command_received(self):
        for runner in self.job_runners.values():
            runner.command_received()

    def add_pending_job(self, job_node: JobNode):
        self.jobs_nodes.add(job_node)

    def _get_runner(self, job_node):
        return self.job_runners[job_node.run_on].run_job

    async def _throttled_runner(self, job_node):
        runner = self._get_runner(job_node)

        async with self.throttle.jobs_limit(job_node.cpus):
            mark_job_started(job_node)
            await runner(
                job_node.program, job_node.arguments, job_node.stdout, job_node.stderr
            )

    def start_job(self, job_node: JobNode):
        log.info(f"run job '{job_node.description}' on {job_node.run_on}")
        job_task = asyncio.create_task(self._throttled_runner(job_node))

        self.job_tasks.add(job_node.project_id, job_node.db_job_id, job_task)

        return job_task

    def cancel_job(self, project_id, job_id):
        log.info(f"canceling job {project_id}-{job_id}")

        job_task = self.job_tasks.get(project_id, job_id)
        if job_task is None:
            log.info(f"unknown job {project_id}-{job_id}")
            return

        if job_task.done():
            log.info(f"job {project_id}-{job_id} already finished")
            return

        job_task.cancel()

    def job_finished(self, job_node: JobNode):
        # if the job is running,
        # remove it's asyncio task entry
        self.job_tasks.remove(job_node.project_id, job_node.db_job_id)

        # remove the job node entry
        self.jobs_nodes.remove(job_node)

        # mark it as finished in db
        mark_job_finished(job_node)


async def run_jobs_tree(root: JobNode, jobs_table: JobsTable):
    try:
        # run all dependencies
        co = [run_jobs_tree(dep, jobs_table) for dep in root.previous_jobs]
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


async def start_jobs_set(command: StartJobsSet, jobs_table):
    log.info(f"starting jobs set with ID {command.project_id}-{command.jobs_set_id}")

    job_nodes = get_job_nodes(command.project_id, command.jobs_set_id)
    for node in job_nodes:
        jobs_table.add_pending_job(node)

    root_nodes = get_root_nodes(job_nodes)
    await run_jobs_roots(root_nodes, jobs_table)


def cancel_jobs(command: CancelJobs, jobs_table: JobsTable):
    for job_id in command.job_ids:
        jobs_table.cancel_job(command.project_id, job_id)


async def handle_command(command, jobs_table: JobsTable):
    jobs_table.command_received()

    if command.LABEL == "start_jobs_set":
        asyncio.create_task(start_jobs_set(command, jobs_table))
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


async def run(cpu_limit):
    exit_event = init_signals()
    jobs_table = JobsTable(get_runners(), cpu_limit)

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
    parser.add_argument(
        "--cpu-limit",
        type=int,
        help="throttel jobs to use max number of specified CPU",
        default=None,
    )

    return parser.parse_args()


def set_uid_gid(uid, gid):
    if gid is not None:
        os.setgid(gid)

    if uid is not None:
        os.setuid(uid)


def setup_daemon(uid, gid):
    # set-up logging to goto stdout
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(name)s: %(message)s",
    )
    # make sure the log is flushed after each new line
    sys.stdout.reconfigure(line_buffering=True)

    # switch uid/gid if requested
    set_uid_gid(uid, gid)


def main():
    args = parse_args()
    setup_daemon(args.uid, args.gid)
    asyncio.run(run(args.cpu_limit))
