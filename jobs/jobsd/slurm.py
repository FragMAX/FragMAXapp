import time
import asyncio
import asyncssh
import logging
from typing import Iterable
from asyncio.subprocess import PIPE
from contextlib import asynccontextmanager
from jobs.jobsd.slurm_parser import parse_sbatch_reply, parse_sacct_reply

log = logging.getLogger(__name__)


class SSHConnectionParams:
    def __init__(self, host, username, key_file):
        self.host = host
        self.username = username
        self.key_file = key_file


class FrontEndConnection:
    # time since last usage, in seconds, before we drop the SSH connection
    CONNECTION_TIMEOUT = 42

    def __init__(self, ssh_params: SSHConnectionParams):
        self.ssh_params = ssh_params
        # reference counter for SSH connection
        self.conn_users = 0
        self.conn_last_usage = 0
        self.ssh_conn = None
        self.ssh_conn_lock = asyncio.Lock()

    async def _connect_if_needed(self):
        async with self.ssh_conn_lock:
            if self.ssh_conn is not None:
                # already connected
                return

            log.info("opening ssh connection")
            self.ssh_conn = await asyncssh.connect(
                self.ssh_params.host,
                # skip checking host's fingerprint
                known_hosts=None,
                # don't try to look-up cert files, as it may fail due
                # to insufficient permissions on the file system
                x509_trusted_cert_paths=None,
                username=self.ssh_params.username,
                client_keys=[self.ssh_params.key_file],
            )
            asyncio.create_task(self._disconnect_timeout())

    async def _disconnect_timeout(self):
        def time_to_sleep():
            now = time.monotonic()
            time_to_sleep = (self.conn_last_usage + self.CONNECTION_TIMEOUT) - now

            return time_to_sleep

        while self.conn_users > 0:
            while (tts := time_to_sleep()) > 0:
                await asyncio.sleep(tts)

        async with self.ssh_conn_lock:
            log.info(
                f"SSH connection unused for at least {self.CONNECTION_TIMEOUT}s, closing"
            )
            self.ssh_conn.close()
            await self.ssh_conn.wait_closed()
            self.ssh_conn = None

    @asynccontextmanager
    async def connection(self):
        self.conn_users += 1
        self.conn_last_usage = time.monotonic()

        await self._connect_if_needed()

        yield self.ssh_conn
        self.conn_users -= 1


class SlurmClient:
    def __init__(self, ssh_params: SSHConnectionParams):
        self.front_end = FrontEndConnection(ssh_params)

    async def submit_sbatch(self, sbatch_path, stdout_log_path, stderr_log_path):
        #
        # for some reason running 'sbatch' command using asyncssh connection
        # does not work correctly, the submitted batch file will be run in
        # weird environment, and will fail to load presto modules
        #
        # as a work-around, spawn the cli 'ssh' command and use that to issue
        # 'sbatch' command on the front end host
        #
        ssh_param = self.front_end.ssh_params
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-i",
            ssh_param.key_file,
            f"{ssh_param.username}@{ssh_param.host}",
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )
        cmd = (
            f"sbatch --output={stdout_log_path} --error={stderr_log_path} {sbatch_path}"
        )
        log.info(cmd)
        proc.stdin.write(cmd.encode())
        await proc.stdin.drain()

        proc.stdin.close()
        await proc.stdin.wait_closed()

        stdout, stderr = await proc.communicate()

        if stdout:
            log.info(f"[ssh stdout]\n{stdout.decode()}")
        if stderr:
            log.info(f"[ssh stderr]\n{stderr.decode()}")

        return parse_sbatch_reply(stdout.decode())

    async def cancel_sbatch(self, job_id):
        async with self.front_end.connection() as conn:
            await conn.run(f"scancel {job_id}", check=True)

    async def jobs_status(self, job_ids: Iterable[str]):
        """
        jobs status, as reported by 'sacct' command
        """

        def sacct_command():
            ids_list = ",".join(job_ids)
            return f"sacct --jobs={ids_list}"

        async with self.front_end.connection() as conn:
            # TODO: handle:
            # asyncssh.process.ProcessError: Process exited with non-zero exit status 1

            result = await conn.run(sacct_command(), check=True)

        # TODO: handle parse errors
        return parse_sacct_reply(result.stdout)


class JobWatcher:
    # job status polling interval, in seconds
    POLL_INTERVALL = 10

    def __init__(self, slurm_client: SlurmClient):
        self.client = slurm_client
        self.watched_jobs = {}
        self.poller_running = False

    def _start_watching(self):
        if self.poller_running:
            # already polling
            return

        self.poller_running = True
        asyncio.create_task(self._poll_jobs())

    def _job_done(self, job_id):
        self.watched_jobs[job_id].set()
        del self.watched_jobs[job_id]

    async def _poll_jobs(self):
        def job_ids():
            return self.watched_jobs.keys()

        def job_finished_status(status):
            return status in ["COMPLETED", "FAILED", "CANCELLED"]

        # poll jobs status,
        # until the 'watched_jobs' is empty
        log.info("polling slurm job status")
        while self.watched_jobs:
            job_status = await self.client.jobs_status(job_ids())

            for jid, status in job_status:
                if job_finished_status(status):
                    self._job_done(jid)

            await asyncio.sleep(self.POLL_INTERVALL)

        log.info("polling stopped, no more jobs to watch")
        self.poller_running = False

    async def wait_for_job(self, job_id):
        job_event = asyncio.Event()
        self.watched_jobs[job_id] = job_event

        self._start_watching()

        await job_event.wait()


class SlurmRunner:
    def __init__(self, host, user, key_file):
        self.client = SlurmClient(SSHConnectionParams(host, user, key_file))
        self.job_watcher = JobWatcher(self.client)

    async def run_job(self, program, stdout_log, stderr_log):
        log.info(f"submitting '{program}' command")
        job_id = None
        try:
            job_id = await self.client.submit_sbatch(program, stdout_log, stderr_log)
            await self.job_watcher.wait_for_job(job_id)
        except asyncio.CancelledError:
            if job_id is None:
                # job was canceled before we had time to
                # to submit it to slurm, we are done here
                return
            await self.client.cancel_sbatch(job_id)
            await self.job_watcher.wait_for_job(job_id)

        # TODO check if job have failed, and raise JobFailedException()

        log.info(f"'{program}' done")
