from fragview.sites import SITE


def _local_runner():
    from jobs.jobsd.local import run_job

    return run_job


def _slurm_runner():
    from jobs.jobsd.slurm import SlurmRunner
    from conf import SLURM_FRONT_END

    slurm_runner = SlurmRunner(
        SLURM_FRONT_END["host"], SLURM_FRONT_END["user"], SLURM_FRONT_END["key_file"]
    )
    return slurm_runner.run_job


def _get_hpc_runner():  # TODO: type annotate 'returns callable'
    runner_name = SITE.HPC_JOBS_RUNNER

    if runner_name == "local":
        return _local_runner()

    if runner_name == "slurm":
        return _slurm_runner()


def get_runners():  # TBD type annotate return value 'dict of str: callable ?'
    return dict(local=_local_runner(), hpc=_get_hpc_runner())
