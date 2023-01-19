from gemmi import UnitCell
from projects.database import db_session
from fragview.space_groups import get_space_group
from fragview.tools import ProcessOptions
from fragview.tools.xdsapp import generate_batch
from tests.utils import ProjectTestCase
from tests.project_setup import Crystal, DataSet
from tests.project_setup import Project as ProjectDesc


class TestGenerateBatch(ProjectTestCase):
    """
    test xdsapp.generate_batch()
    i.e. test generating xdsapp batch processing files
    """

    PROJECTS = [
        ProjectDesc(
            proposal="20190242",
            protein="Prtk",
            crystals=[Crystal("X01", "VTL", "VT0")],
            datasets=[DataSet("X01", 1)],
            results=[],
        )
    ]

    @db_session
    def test_auto(self):
        """
        test generating batch file with space group and cell params set to 'auto'
        """
        options = ProcessOptions(None, None)
        batch = generate_batch(self.project, self.project.get_dataset(1), options)

        # check that the batch file ends with expected xdsapp command
        self.assertRegex(
            batch._body,
            ".*"
            "xdsapp3 --cmd --dir=/tmp/.*/fragmax/proj1/process/X01_1/xdsapp "
            "-j 1 -c 40 "
            "-i /data/visitors/biomax/20190242/20211125/raw/Prtk/X01/X01_1_master.h5   "
            r"--delphi=10 --fried=True --range=1\\ 1800\n",
        )

    @db_session
    def test_space_group(self):
        """
        test generating batch file where space group is specified
        """
        options = ProcessOptions(get_space_group("C2"), None)
        batch = generate_batch(self.project, self.project.get_dataset(1), options)

        self.assertRegex(
            batch._body,
            ".*"
            "xdsapp3 --cmd --dir=/tmp/.*/fragmax/proj1/process/X01_1/xdsapp "
            "-j 1 -c 40 "
            "-i /data/visitors/biomax/20190242/20211125/raw/Prtk/X01/X01_1_master.h5 "
            r"--spacegroup='5'  --delphi=10 --fried=True --range=1\\ 1800\n",
        )

    @db_session
    def test_space_group_cell_parameters(self):
        """
        test generating batch file where space group and cell params are specified
        """
        options = ProcessOptions(
            get_space_group("P21212"), UnitCell(61.5, 109.5, 43.5, 90.0, 90.0, 90.0)
        )
        batch = generate_batch(self.project, self.project.get_dataset(1), options)

        # check that the batch file ends with expected xdsapp command
        self.assertRegex(
            batch._body,
            ".*"
            "xdsapp3 --cmd --dir=/tmp/.*/fragmax/proj1/process/X01_1/xdsapp "
            "-j 1 -c 40 "
            "-i /data/visitors/biomax/20190242/20211125/raw/Prtk/X01/X01_1_master.h5 "
            r"--spacegroup='18 61.5 109.5 43.5 90.0 90.0 90.0'  --delphi=10 --fried=True --range=1\\ 1800\n",
        )

    @db_session
    def test_custom_parameters(self):
        """
        test generating batch file when custom parameters are specified
        """
        options = ProcessOptions(None, None, custom_args="--auto")
        batch = generate_batch(self.project, self.project.get_dataset(1), options)

        # check that the batch file ends with expected xdsapp command
        self.assertRegex(
            batch._body,
            ".*"
            "xdsapp3 --cmd --dir=/tmp/.*/fragmax/proj1/process/X01_1/xdsapp "
            "-j 1 -c 40 "
            "-i /data/visitors/biomax/20190242/20211125/raw/Prtk/X01/X01_1_master.h5  "
            r"--auto --delphi=10 --fried=True --range=1\\ 1800\n",
        )
