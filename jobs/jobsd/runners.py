from fragview.sites import SITE
from jobs.jobsd.runner import Runner


def _local_runner() -> Runner:
    from jobs.jobsd.local import LocalRunner

    return LocalRunner()


def _slurm_runner() -> Runner:
    from jobs.jobsd.slurm import SlurmRunner
    from conf import SLURM_FRONT_END

    return SlurmRunner(
        SLURM_FRONT_END["host"], SLURM_FRONT_END["user"], SLURM_FRONT_END["key_file"]
    )


def _get_hpc_runner() -> Runner:
    runner_name = SITE.HPC_JOBS_RUNNER

    if runner_name == "local":
        return _local_runner()

    if runner_name == "slurm":
        return _slurm_runner()

    assert False, f"unexpected runner type {runner_name}"


def get_runners() -> dict[str, Runner]:
    return dict(local=_local_runner(), hpc=_get_hpc_runner())
