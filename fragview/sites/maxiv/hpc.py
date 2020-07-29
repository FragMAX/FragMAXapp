import subprocess
from django.conf import settings
from fragview.sites import plugin


class HPC(plugin.HPC):
    def run_batch(self, sbatch_script, sbatch_options=None):
        cmd = "sbatch"

        # add options to sbatch command, if specified
        if sbatch_options is not None:
            cmd += f" {sbatch_options}"

        # add script for sbatch to run
        cmd += f" {sbatch_script}"

        # TODO: check exit code and bubble up error on exit code != 0
        _ssh_on_frontend(cmd)

    def new_batch_file(self, script_name):
        return BatchFile(script_name)


# TODO: this is copy and paste code from fragview.hpc model,
# get rid of one of the copies
def _ssh_on_frontend(command):
    """
    return a tuple of (stdout, stderr, exit_code)
    """
    print(f"running on HPC '{command}'")
    with subprocess.Popen(
        ["ssh", settings.HPC_FRONT_END], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    ) as proc:

        stdout, stderr = proc.communicate(command.encode("utf-8"))
        return stdout, stderr, proc.returncode


class BatchFile(plugin.BatchFile):
    def load_python_env(self):
        """
        no need to add any new commands here, as python3 is always available
        """
        self.add_command("module purge")
        self.add_command("module load GCC/7.3.0-2.30 OpenMPI/3.1.1 Python/3.7.0")