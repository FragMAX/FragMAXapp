import subprocess
from fragview.sites import plugin


class HPC(plugin.HPC):
    def run_batch(self, sbatch_script, sbatch_options=None):
        if sbatch_options is not None:
            # not sure how this should be handled, TODO investigate
            raise NotImplementedError("sbatch options support")

        cmd = f"sh {sbatch_script}"

        print(f"running on HKL8 '{cmd}'")
        subprocess.Popen(cmd, shell=True)

    def new_batch_file(self, script_name):
        return BatchFile(script_name)


class BatchFile(plugin.BatchFile):
    def load_python_env(self):
        """
        no need to add any new commands here, as python3 is always available
        """
        pass

    def set_options(self, **_):
        """
        for now, we ignore all options
        """

    def load_modules(self, *_):
        """
        """

    def purge_modules(self):
        """
        """
