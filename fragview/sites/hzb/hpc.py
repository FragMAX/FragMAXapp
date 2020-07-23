import subprocess
from fragview.sites import plugin


class HPC(plugin.HPC):
    def run_sbatch(self, sbatch_script, sbatch_options=None):
        if sbatch_options is not None:
            # not sure how this should be handled, TODO investigate
            raise NotImplementedError("sbatch options support")

        cmd = f"sh {sbatch_script}"

        print(f"running on HKL8 '{cmd}'")
        subprocess.Popen(cmd, shell=True)
