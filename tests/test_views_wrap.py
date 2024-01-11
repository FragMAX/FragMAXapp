from projects.database import db_session
from fragview.views.wrap import DatasetInfo
from tests.utils import ProjectTestCase
from tests.project_setup import Project, DataSet, Crystal


class TestDatasetInfo(ProjectTestCase):
    PROJECTS = [
        Project(
            protein="MID2",
            proposal="20180453",
            crystals=[
                Crystal("X01", "TstLib", "VT0"),
            ],
            datasets=[
                DataSet("X01", 1),
            ],
            results=[],
        ),
    ]

    def setUp(self):
        super().setUp()

    @db_session
    def test_fields(self):
        """
        test using the data-set wrapper object DatasetInfo

        check that we can access the wrapped fields
        """
        dset = self.project.get_crystal("X01").get_dataset(1)
        dinfo = DatasetInfo(dset)

        self.assertEqual(dinfo.beamline, "BioMAX")
        self.assertEqual(dinfo.detector, "EIGER 16M")
        self.assertAlmostEqual(dinfo.wavelength, 0.92)
        self.assertAlmostEqual(dinfo.start_angle, 43.0)
        self.assertAlmostEqual(dinfo.angle_increment, 0.1)
        self.assertAlmostEqual(dinfo.exposure_time, 39.2)
        self.assertEqual(dinfo.images, 1800)
        # check that the 'synthetic' field total_exposure works
        self.assertAlmostEqual(dinfo.total_exposure(), 1800 * 39.2)
        self.assertAlmostEqual(dinfo.detector_distance, 152.44)
        self.assertAlmostEqual(dinfo.xbeam, 2100.77)
        self.assertAlmostEqual(dinfo.ybeam, 2120.31)
        self.assertAlmostEqual(dinfo.transmission, 0.12)
        self.assertEqual(dinfo.beam_shape, "ellipse")
