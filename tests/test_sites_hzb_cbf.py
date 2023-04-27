import numpy
from unittest import TestCase
from pathlib import Path
from datetime import datetime
from fabio.cbfimage import cbfimage
from fragview.sites.hzb import cbf
from fragview.sites.hzb.cbf import parse_metadata, CbfHeaderParseError
from tests.utils import data_file_path, TempDirMixin

HEAD_LINES = [
    "# Detector: PILATUS3 2M, S/N 24-0124",
    "# 2019/Nov/29 13:14:55",
    "# Pixel_size 172e-6 m x 172e-6 m",
    "# Silicon sensor, thickness 0.001 m",
    "# Oscillation_axis omega",
    "# Excluded_pixels:  badpix_mask.tif",
    "# Chi 0.0000 deg.",
    "# Angle_increment 0.1000 deg.",
    "# Polarization None",
    "# file_comments ",
    "# N_oscillations 3600",
    "# Beam_xy (747.00, 828.00) pixels",
    "# Exposure_time 0.100000 s",
    "# Phi -9999.0000 deg.",
    "# Energy_range (0, 0) eV",
    "# Start_angle 30.0000 deg.",
    "# Detector_distance 0.158960 m",
    "# Detector_Voffset 0.0000 m",
    "# Alpha 0.0000 deg.",
    "# Flat_field: (nil)",
    "# Threshold_setting 6750 eV",
    "# Exposure_period 0.103000 s",
    "# N_excluded_pixels: = 321",
    "# Kappa -9999.0000 deg.",
    "# Tau = 0 s",
    "# Transmission 100.0",
    "# Detector_2theta 0.0000 deg.",
    "# Flux 1e+11",
    "# Count_cutoff 1048500",
    "# Trim_directory: (nil)",
    "# Wavelength 0.918400 A",
]


def _get_header_lines(lineno, text):
    """
    get CBF header, with one line replaced with specified text
    """
    lines = HEAD_LINES.copy()
    lines[lineno] = text

    return "\n".join(lines)


class TestParseMetadata(TestCase):
    """
    test parse_metadata()
    """

    def test_parse(self):
        # read metadata from an CBF file
        res = parse_metadata(data_file_path("ARwoDMSO-F2XEntry-A12a_1_0001.cbf"))

        # check parsed metadata
        self.assertEquals(res.detector, "PILATUS3 2M")
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
        self.assertEquals(res.beamline, "14.2")


class TestParseErrors(TestCase, TempDirMixin):
    """
    test HZB CBF header parse errors
    """

    # make data part at least some kilobytes as a
    # workaround for: https://github.com/silx-kit/fabio/issues/528
    DUMMY_DATA = numpy.array([[1, 2, 3] * 1024])

    def setUp(self):
        self.setup_temp_dir()
        self.file_name = Path(self.temp_dir, "test.cbf")

    def tearDown(self):
        self.tear_down_temp_dir()
        # print(self.file_name)

    def _create_cbf(self, header_contents):
        header = {"_array_data.header_contents": header_contents}
        cbf = cbfimage(header=header, data=self.DUMMY_DATA)
        cbf.write(self.file_name)

    def test_images_parse_err(self):
        """
        error parsing 'images' line
        """
        header = _get_header_lines(cbf.IMAGES_LINE_NO, "# invalid")
        self._create_cbf(header)

        with self.assertRaisesRegex(CbfHeaderParseError, "error parsing images"):
            parse_metadata(self.file_name)

    def test_detector_parse_err(self):
        """
        error parsing 'detector' line
        """
        header = _get_header_lines(cbf.DETECTOR_LINE_NO, "# invalid")
        self._create_cbf(header)

        with self.assertRaisesRegex(CbfHeaderParseError, "error parsing detector"):
            parse_metadata(self.file_name)

    def test_unknown_detector_serial_no(self):
        """
        test the case when detector with unknown serial number is specified in the header
        """
        header = _get_header_lines(
            cbf.DETECTOR_LINE_NO, "# Detector: PILATUS3 2M, S/N 00-0000"
        )
        self._create_cbf(header)

        with self.assertRaisesRegex(
            CbfHeaderParseError, "unknown detector serial number '00-0000'"
        ):
            parse_metadata(self.file_name)

    def test_beam_xy_parse_err(self):
        """
        error parsing 'beam xy' line
        """
        header = _get_header_lines(cbf.BEAM_XY_LINE_NO, "# invalid")
        self._create_cbf(header)

        with self.assertRaisesRegex(CbfHeaderParseError, "error parsing beam xy"):
            parse_metadata(self.file_name)
