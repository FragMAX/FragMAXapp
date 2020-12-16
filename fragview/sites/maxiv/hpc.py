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

    def new_batch_file(self, job_name, script_name, stdout, stderr):
        return BatchFile(job_name, script_name, stdout, stderr)


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
    def _add_option(self, option_string):
        self.add_line(f"#SBATCH {option_string}")

    def load_modules(self, modules):
        mods = " ".join(modules)
        self.add_command(f"module load {mods}")

    def purge_modules(self):
        self.add_command("module purge")

    def load_python_env(self):
        self.purge_modules()
        self.load_modules(["GCCcore/8.3.0", "Python/3.7.4"])

    def assign_variable(self, var_name, expression):
        self.add_command(f"{var_name}={expression}")

    def set_options(
        self,
        time=None,
        job_name=None,
        exclusive=None,
        nodes=None,
        cpus_per_task=None,
        mem_per_cpu=None,
        partition=None,
        memory=None,
        stdout=None,
        stderr=None,
    ):
        def _slurm_size(size):
            return f"{size.value}{size.unit}"

        if time:
            self._add_option(f"--time={time.as_hms_text()}")

        if job_name:
            raise NotImplementedError("port to new 'non-option' style")
            self._add_option(f"--job-name={job_name}")

        if exclusive:
            self._add_option("--exclusive")

        if nodes:
            self._add_option(f"--nodes={nodes}")

        if cpus_per_task:
            self._add_option(f"--cpus-per-task={cpus_per_task}")

        if mem_per_cpu:
            self._add_option(f"--mem-per-cpu={_slurm_size(mem_per_cpu)}")

        if partition:
            self._add_option(f"--partition={partition}")

        if memory:
            self._add_option(f"--mem={_slurm_size(memory)}")

        if stdout:
            raise NotImplementedError("port to new 'non-option' style")
            self._add_option(f"--output={stdout}")

        if stderr:
            raise NotImplementedError("port to new 'non-option' style")
            self._add_option(f"--error={stderr}")
