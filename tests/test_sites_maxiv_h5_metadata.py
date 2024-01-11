from unittest import TestCase
from pathlib import Path
from h5py import File, Group
import numpy as np
from tests.utils import TempDirMixin
from fragview.sites.maxiv.h5_metadata import read_metadata


BEAMLINE = "MircoMAX"
DETECTOR = "Kebnekaise Fe 42M"
NIMAGES = 480
BEAM_CENTER_X = 2101.8
BEAM_CENTER_Y = 2121.1
WAVELENGTH = 0.986
OMEGA = [0.4, 0.5, 0.6]
ANGLE_INC = 0.1
DETECTOR_DIST = 0.453


def _write_master_file(
    master_file: Path,
    beamline: str,
    detector_desc: str,
    nimages: int,
    beam_center_x: float,
    beam_center_y: float,
    wavelength: float,
    omega: list[float],
    angle_inc: float,
    detector_dist: float,
):
    def add_dset(entry: Group, path: str, value, dtype):
        entry.create_dataset(path, data=value, dtype=dtype)

    def add_str(entry: Group, path: str, value: str):
        add_dset(entry, path, value, np.dtype(f"S{len(value)}"))

    def add_int(entry: Group, path: str, value: int):
        add_dset(entry, path, value, np.dtype("u8"))

    def add_float(entry: Group, path: str, value: float):
        add_dset(entry, path, value, np.dtype("f8"))

    def create_entry(h5file: File):
        entry = h5file.create_group("entry")

        add_str(entry, "instrument/detector/description", detector_desc)
        add_int(entry, "instrument/detector/detectorSpecific/nimages", nimages)
        add_float(entry, "instrument/detector/beam_center_x", beam_center_x)
        add_float(entry, "instrument/detector/beam_center_y", beam_center_y)
        add_float(entry, "instrument/beam/incident_wavelength", wavelength)
        add_str(entry, "instrument/name", beamline)
        entry["sample/goniometer/omega"] = np.array(omega, dtype=np.dtype("f8"))
        add_float(entry, "sample/goniometer/omega_range_average", angle_inc)
        add_float(entry, "instrument/detector/detector_distance", detector_dist)

    with File(master_file, "w") as h5file:
        create_entry(h5file)


class TestH5(TestCase, TempDirMixin):
    def setUp(self):
        self.setup_temp_dir()

    def tearDown(self):
        self.tear_down_temp_dir()

    def test_reading(self):
        """
        test reading data-set meta-data from an HDF5 master file
        """

        # create a test master file
        h5_file = Path(self.temp_dir, "master.h5")
        _write_master_file(
            h5_file,
            BEAMLINE,
            DETECTOR,
            NIMAGES,
            BEAM_CENTER_X,
            BEAM_CENTER_Y,
            WAVELENGTH,
            OMEGA,
            ANGLE_INC,
            DETECTOR_DIST,
        )

        # read the master file
        metadata = read_metadata(h5_file)

        # check that we get expected meta-data
        self.assertEqual(metadata.beamline, BEAMLINE)
        self.assertEqual(metadata.detector, DETECTOR)
        self.assertEqual(metadata.images, NIMAGES)
        self.assertAlmostEqual(metadata.wavelength, WAVELENGTH)
        self.assertAlmostEqual(metadata.start_angle, OMEGA[0])
        self.assertAlmostEqual(metadata.angle_increment, ANGLE_INC)
        self.assertAlmostEqual(metadata.detector_distance, DETECTOR_DIST * 1000)
        self.assertAlmostEqual(metadata.xbeam, BEAM_CENTER_X)
        self.assertAlmostEqual(metadata.ybeam, BEAM_CENTER_Y)
        self.assertIsNone(metadata.start_time)
        self.assertIsNone(metadata.end_time)
        self.assertIsNone(metadata.exposure_time)
        self.assertIsNone(metadata.beam_shape)
        self.assertIsNone(metadata.transmission)
        self.assertIsNone(metadata.slit_gap_horizontal)
        self.assertIsNone(metadata.slit_gap_vertical)
        self.assertIsNone(metadata.flux)
        self.assertIsNone(metadata.beam_size_at_sample_x)
        self.assertIsNone(metadata.beam_size_at_sample_y)
