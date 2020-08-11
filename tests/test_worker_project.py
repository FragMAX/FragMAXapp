import shutil
import tempfile
from unittest import TestCase
from unittest.mock import Mock
from tests.utils import xs_data_path
from fragview.fileio import makedirs, read_csv_lines
from fragview.projects import project_process_protein_dir, project_data_collections_file
from worker.project import _write_data_collections_file


class TestWriteDataCollectionsFile(TestCase):
    EXPECTED_CSV_LINES = [
        [
            "imagePrefix",
            "SampleName",
            "dataCollectionPath",
            "Acronym",
            "dataCollectionNumber",
            "numberOfImages",
            "resolution",
            "snapshot",
        ],
        [
            "100037-SiBiL-x556",
            "x556",
            "/img/dir/",
            "AR",
            "1",
            "3600",
            "1.60",
            "/some/dir/Prtk-Vt-G2_1_1.snapshot.jpeg,/some/dir/Prtk-Vt-G2_1_2.snapshot.jpeg",
        ],
        [
            "100037-SiBiL-x656",
            "x656",
            "/img/dir/",
            "AR",
            "1",
            "1800",
            "1.60",
            "/some/dir/Prtk-Vt-F0_1_1.snapshot.jpeg",
        ],
        [
            "100037-SiBiL-x756",
            "x756",
            "/img/dir/",
            "AR",
            "2",
            "3600",
            "1.24",
            "noSnapshots",
        ],
    ]

    def setUp(self):
        #
        # set-up mocked project with it's
        # directory inside temp directory
        #
        self.temp_dir = tempfile.mkdtemp()

        proj = Mock()
        proj.protein = "AR"
        proj.data_path.return_value = self.temp_dir

        # create subdirectories where we'll write datacollection file
        makedirs(project_process_protein_dir(proj))

        self.proj = proj

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_func(self):
        # write datacollection file
        xmls = [xs_data_path(n) for n in range(3)]
        _write_data_collections_file(self.proj, xmls)

        # load created CSV file, and check it matches our expectations
        self.assertListEqual(
            read_csv_lines(project_data_collections_file(self.proj)),
            self.EXPECTED_CSV_LINES,
        )
