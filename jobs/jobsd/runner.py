class JobFailedException(Exception):
    pass


class Runner:
    async def run_job(self, program, arguments, stdout_log, stderr_log):
        raise NotImplementedError()

    def command_received(self):
        raise NotImplementedError()
