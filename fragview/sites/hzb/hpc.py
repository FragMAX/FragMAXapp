from fragview.sites import plugin


class HPC(plugin.HPC):
    def new_batch_file(self, job_name, script_name, stdout, stderr, cpus=None):
        return BatchFile(job_name, script_name, stdout, stderr, cpus)


class BatchFile(plugin.BatchFile):
    # HZB uses tcsh shell
    HEADER = "#!/bin/tcsh"

    def load_python_env(self):
        """
        no need to add any new commands here, as python3 is always available
        """
        pass

    def assign_variable(self, var_name, expression):
        self.add_command(f"set {var_name}={expression}")

    def set_options(self, **_):
        """
        for now, we ignore all options
        """

    def load_modules(self, *_):
        """
        no modules on HZB
        """

    def purge_modules(self):
        """
        no modules on HZB
        """
