import unittest
from datetime import datetime
from fragview.sites.maxiv.xsdata import parse_xsdata_file
from tests.utils import xs_data_path, data_file_path


class TestParseXsdataFile(unittest.TestCase):
    """
    test parse_xsdata_file() function
    """

    def test_parser(self):
        # parse the XML file
        metadata = parse_xsdata_file(xs_data_path(0))

        # check that we get expected data
        self.assertListEqual(metadata.snapshot_indices, [1, 2])
        self.assertAlmostEqual(metadata.start_angle, 2.70001e02)
        self.assertAlmostEqual(metadata.flux, 2.7e12)
        self.assertAlmostEqual(metadata.wavelength, 9.762530e-01)
        self.assertAlmostEqual(metadata.exposure_time, 1.100000e-02)
        self.assertAlmostEqual(metadata.resolution, 1.600000e00)
        self.assertAlmostEqual(metadata.beam_size_at_sample_x, 5.000000e01)
        self.assertAlmostEqual(metadata.beam_size_at_sample_y, 5.000000e01)
        self.assertAlmostEqual(metadata.angle_increment, 1.000000e-01)
        self.assertAlmostEqual(metadata.detector_distance, 2.152600e02)
        self.assertAlmostEqual(metadata.xbeam, 2.100770e03)
        self.assertAlmostEqual(metadata.ybeam, 2.120790e03)
        self.assertAlmostEqual(metadata.transmission, 1.000000e02)
        self.assertAlmostEqual(metadata.slit_gap_vertical, 5.000000e01)
        self.assertAlmostEqual(metadata.slit_gap_horizontal, 5.000000e01)
        self.assertEqual(metadata.images, 3600)
        self.assertEqual(metadata.beam_shape, "ellipse")
        self.assertEqual(metadata.start_time, datetime(2020, 4, 1, 7, 55, 25))
        self.assertEqual(metadata.end_time, datetime(2020, 4, 1, 7, 56, 44))

    def test_no_snaps(self):
        """
        test case when XML file does not contain any 'xtalSnapshotFullPathN' tags,
        which is the case for projects at HZB
        """
        metadata = parse_xsdata_file(data_file_path(f"xs_data_no_snaps.xml"))

        # snapshots indices should be an empty list
        self.assertListEqual(metadata.snapshot_indices, [])
