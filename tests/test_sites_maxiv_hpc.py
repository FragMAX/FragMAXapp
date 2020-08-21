from os import path
from unittest import TestCase
from tempfile import TemporaryDirectory
from fragview.sites.plugin import Duration, DataSize
from fragview.sites.maxiv import SitePlugin


EXPECTED_BATCH = b"""#!/bin/bash
#SBATCH --time=02:00:00
#SBATCH --job-name=test
#SBATCH --exclusive
#SBATCH --nodes=4
#SBATCH --cpus-per-task=2
#SBATCH --partition=sea
#SBATCH --mem=2G
#SBATCH --output=out
#SBATCH --error=err
single_command
command1
command2
module purge
module load mod1 mod2
module purge
module load GCCcore/8.3.0 Python/3.7.4
"""


class TestBatch(TestCase):
    """
    test writing MAXIV styled batch file
    """

    def setUp(self):
        self.hpc = SitePlugin().get_hpc_runner()

    def _assert_file(self, file_path, expected_contents):
        with open(file_path, "rb") as f:
            contents = f.read()
            self.assertEqual(contents, expected_contents)

    def test_batch(self):
        """
        test writing batch file using most of the features
        """
        with TemporaryDirectory() as temp_dir:
            script = path.join(temp_dir, "test.sh")

            batch = self.hpc.new_batch_file(script)

            # use all options
            batch.set_options(
                time=Duration(hours=2),
                job_name="test",
                exclusive=True,
                nodes=4,
                cpus_per_task=2,
                partition="sea",
                memory=DataSize(gigabyte=2),
                stdout="out",
                stderr="err",
            )

            # add available flavors of commands
            batch.add_command("single_command")
            batch.add_commands("command1", "command2")
            batch.purge_modules()
            batch.load_modules(["mod1", "mod2"])
            batch.load_python_env()

            batch.save()

            # check that written file on disk looks as expected
            self._assert_file(script, EXPECTED_BATCH)


class TestBatchTimeOption(TestCase):
    """
    test 'time' batch option
    """

    def setUp(self):
        self.batch = SitePlugin().get_hpc_runner().new_batch_file("dummy")

    def test_hms(self):
        """
        test specifying time using hours, minutes and seconds
        """
        self.batch.set_options(time=Duration(hours=128, minutes=23, seconds=7))

        self.assertEqual(self.batch._body, "#!/bin/bash\n" "#SBATCH --time=128:23:07\n")

    def test_hours(self):
        """
        test specifying time using only hours
        """
        self.batch.set_options(time=Duration(hours=6))

        self.assertEqual(self.batch._body, "#!/bin/bash\n" "#SBATCH --time=06:00:00\n")

    def test_minutes(self):
        """
        test specifying time using only minutes
        """
        self.batch.set_options(time=Duration(minutes=9))

        self.assertEqual(self.batch._body, "#!/bin/bash\n" "#SBATCH --time=00:09:00\n")

    def test_seconds(self):
        """
        test specifying time using only seconds
        """
        self.batch.set_options(time=Duration(seconds=5))

        self.assertEqual(self.batch._body, "#!/bin/bash\n" "#SBATCH --time=00:00:05\n")
