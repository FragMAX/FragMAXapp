from unittest import TestCase
from datetime import datetime
from fragview.sites.hzb.cbf import parse_metadata
from tests.utils import data_file_path


class TestParseMetadata(TestCase):
    """
    test parse_metadata()
    """

    def test_parse(self):
        # read metadata from an CBF file
        res = parse_metadata(data_file_path("ARwoDMSO-F2XEntry-A12a_1_0001.cbf"))

        # check parsed metadata
        self.assertEquals(res.detector, "PILATUS3 2M")
        self.assertAlmostEqual(res.resolution, 1.3)
        self.assertEquals(res.images, 3600)
        self.assertEquals(res.start_time, datetime(2019, 11, 29, 13, 14, 55))
        self.assertIsNone(res.end_time)
        self.assertAlmostEqual(res.wavelength, 0.9184)
        self.assertAlmostEqual(res.start_angle, 30.0)
        self.assertAlmostEqual(res.angle_increment, 0.1)
        self.assertAlmostEqual(res.exposure_time, 0.1)
        self.assertAlmostEqual(res.detector_distance, 158.96)
        self.assertIsNone(res.xbeam)
        self.assertIsNone(res.ybeam)
        self.assertEquals(res.beam_shape, "ellipse")
        self.assertAlmostEqual(res.transmission, 100.0)
        self.assertIsNone(res.slit_gap_horizontal)
        self.assertIsNone(res.slit_gap_vertical)
        self.assertAlmostEqual(res.flux, 100000000000.0)
        self.assertAlmostEqual(res.beam_size_at_sample_x, 747.0)
        self.assertAlmostEqual(res.beam_size_at_sample_y, 828.0)
        self.assertListEqual(res.snapshot_indices, [])
