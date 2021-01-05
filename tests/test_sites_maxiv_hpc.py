from os import path
from unittest import TestCase
from tempfile import TemporaryDirectory
from fragview.sites.plugin import Duration, DataSize
from fragview.sites.maxiv import SitePlugin


EXPECTED_BATCH = b"""#!/bin/bash
#SBATCH --job-name=test
#SBATCH --time=02:00:00
#SBATCH --exclusive
#SBATCH --nodes=4
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=1G
#SBATCH --partition=sea
#SBATCH --mem=2G
FOO=BAR
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

            batch = self.hpc.new_batch_file("test", script, "out", "err")

            # use all options
            batch.set_options(
                time=Duration(hours=2),
                exclusive=True,
                nodes=4,
                cpus_per_task=2,
                mem_per_cpu=DataSize(gigabyte=1),
                partition="sea",
                memory=DataSize(gigabyte=2),
            )

            # add available flavors of commands
            batch.assign_variable("FOO", "BAR")
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

    SBATCH_HEADER = "#!/bin/bash\n#SBATCH --job-name=test\n"

    def setUp(self):
        self.batch = (
            SitePlugin().get_hpc_runner().new_batch_file("test", "dummy", "out", "err")
        )

    def test_hms(self):
        """
        test specifying time using hours, minutes and seconds
        """
        self.batch.set_options(time=Duration(hours=128, minutes=23, seconds=7))

        self.assertEqual(
            self.batch._body, f"{self.SBATCH_HEADER}#SBATCH --time=128:23:07\n",
        )

    def test_hours(self):
        """
        test specifying time using only hours
        """
        self.batch.set_options(time=Duration(hours=6))

        self.assertEqual(
            self.batch._body, f"{self.SBATCH_HEADER}#SBATCH --time=06:00:00\n",
        )

    def test_minutes(self):
        """
        test specifying time using only minutes
        """
        self.batch.set_options(time=Duration(minutes=9))

        self.assertEqual(
            self.batch._body, f"{self.SBATCH_HEADER}#SBATCH --time=00:09:00\n",
        )

    def test_seconds(self):
        """
        test specifying time using only seconds
        """
        self.batch.set_options(time=Duration(seconds=5))

        self.assertEqual(
            self.batch._body, f"{self.SBATCH_HEADER}#SBATCH --time=00:00:05\n",
        )
