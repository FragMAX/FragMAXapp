#!/usr/bin/env python
from typing import List
import asyncio
from asyncio.subprocess import PIPE
import signal
from pathlib import Path
from struct import pack, unpack
from jobs.messages import deserialize_command, Job, GetJobsReply, StartJobs, CancelJobs
from jobs.job_graphs import to_linked_job_nodes, get_root_jobs, JobNode
import conf


class JobIDs:
    """
    keep track of Job IDs sequence

    the next available ID is stored on disk,
    which allows to continue job IDs sequence
    after jobsd restart
    """

    NEXT_ID_FORMAT = "!L"

    def __init__(self, persistence_dir):
        """
        persistence_dir - directory where to job IDs persistence data file is stored
        """
        self._next_id_file = Path(persistence_dir, "jobsd.data")
        self._next_id = self._get_stored_next_id()

    def _get_stored_next_id(self):
        if not self._next_id_file.is_file():
            # no stored IDs found, start from the beginning
            return 1

        # load next job ID from the file
        (res,) = unpack(self.NEXT_ID_FORMAT, self._next_id_file.read_bytes())

        return res

    def next(self):
        res = self._next_id

        # calculate new next ID and
        # store it on disk
        self._next_id += 1
        self._next_id_file.write_bytes(pack(self.NEXT_ID_FORMAT, self._next_id))

        return str(res)


class JobsTable:
    def __init__(self):
        self.job_ids = JobIDs(conf.DATABASE_DIR)
        self.jobs_nodes = set()
        self.job_tasks = {}

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

    def start_job(self, job_node: JobNode):
        job = job_node.job

        job.mark_as_started()

        job_task = asyncio.create_task(run_job(job.program, job.stdout, job.stderr))
        self.job_tasks[job.id] = job_task

        return job_task

    def cancel_job(self, job_id):
        print(f"canceling job {job_id}")
        if job_id not in self.job_tasks:
            print(f"unknown job {job_id}")
            return

        job_task = self.job_tasks[job_id]
        if job_task.done():
            print(f"job {job_id} already finished")
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


async def log_output(stream, log_file):
    with open(log_file, "wb") as log:
        while True:
            buf = await stream.read(1024 * 4)
            if not buf:
                break

            log.write(buf)
            log.flush()


def append_to_log(log_file, message):
    with open(log_file, "ab") as log:
        log.write(f"{message}\n".encode())


class _JobFailedException(Exception):
    pass


async def run_job(program, stdout_log, stderr_log):
    try:
        print(f"'{program}' started")

        proc = await asyncio.create_subprocess_exec(program, stdout=PIPE, stderr=PIPE)

        await asyncio.gather(
            log_output(proc.stdout, stdout_log), log_output(proc.stderr, stderr_log)
        )

    except asyncio.CancelledError:
        proc.terminate()
        append_to_log(stderr_log, "Job terminated by the user.")
        raise _JobFailedException()
    except OSError as ex:
        append_to_log(stderr_log, f"Failed to launch job:\n{ex}")
        raise _JobFailedException()
    finally:
        print(f"'{program}' terminated")


async def run_jobs_tree(root: JobNode, jobs_table: JobsTable):
    try:
        co = [run_jobs_tree(dep, jobs_table) for dep in root.run_after]
        await asyncio.gather(*co)

        print(f"running job '{root.job.name}'")

        await jobs_table.start_job(root)

    except _JobFailedException:
        raise

    finally:
        jobs_table.job_finished(root)
        print(f"done running {root.job.name}")


async def run_jobs_roots(roots, jobs_table):
    try:
        co = [run_jobs_tree(tree, jobs_table) for tree in roots]
        await asyncio.gather(*co)
    except _JobFailedException:
        # we can ignore exception here, as it have been
        # handled while it was unwinding the call stack
        pass


async def start_jobs(command: StartJobs, jobs_table):
    print(f"starting '{command.name}' jobs set")

    job_nodes = to_linked_job_nodes(command.jobs)
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
    if command.LABEL == "get_jobs":
        return get_jobs(jobs_table)
    elif command.LABEL == "start_jobs":
        asyncio.create_task(start_jobs(command, jobs_table))
    elif command.LABEL == "cancel_jobs":
        cancel_jobs(command, jobs_table)
    else:
        assert False, f"unexpected command {command.LABEL}"


async def client_connected(reader, writer, jobs_table: JobsTable):
    line = await reader.readline()
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


async def main():
    exit_event = init_signals()

    jobs_table = JobsTable()

    server = await asyncio.start_unix_server(
        lambda r, w: client_connected(r, w, jobs_table), conf.JOBSD_SOCKET
    )
    serv_task = asyncio.create_task(server.serve_forever())

    # run until we get a signal to exit
    await exit_event.wait()

    # disconnect from the socket and exit
    serv_task.cancel()
    print("bye bye")


if __name__ == "__main__":
    asyncio.run(main())
