import unittest
from datetime import datetime
from fragview.xsdata import XSDataCollection
from tests.utils import xs_data_path, data_file_path


class TestXSDataCollection(unittest.TestCase):
    def test_parser(self):
        # parse the XML file
        xsdata = XSDataCollection(xs_data_path(0))

        # check that we get expected data
        self.assertListEqual(list(xsdata.snapshot_indexes), [1, 2])
        self.assertAlmostEqual(xsdata.axisStart, 2.70001e02)
        self.assertAlmostEqual(xsdata.axisEnd, 6.300010e02)
        self.assertAlmostEqual(xsdata.flux, 2.7e12)
        self.assertAlmostEqual(xsdata.wavelength, 9.762530e-01)
        self.assertAlmostEqual(xsdata.exposureTime, 1.100000e-02)
        self.assertAlmostEqual(xsdata.resolution, 1.600000e00)
        self.assertAlmostEqual(xsdata.beamSizeSampleX, 5.000000e01)
        self.assertAlmostEqual(xsdata.beamSizeSampleY, 5.000000e01)
        self.assertAlmostEqual(xsdata.axisRange, 1.000000e-01)
        self.assertAlmostEqual(xsdata.detectorDistance, 2.152600e02)
        self.assertAlmostEqual(xsdata.overlap, 0)
        self.assertAlmostEqual(xsdata.xbeam, 2.100770e03)
        self.assertAlmostEqual(xsdata.ybeam, 2.120790e03)
        self.assertAlmostEqual(xsdata.transmission, 1.000000e02)
        self.assertAlmostEqual(xsdata.slitGapVertical, 5.000000e01)
        self.assertAlmostEqual(xsdata.slitGapHorizontal, 5.000000e01)
        self.assertEqual(xsdata.num_images, 3600)
        self.assertEqual(xsdata.dataCollectionNumber, 1)
        self.assertEqual(xsdata.imagePrefix, "100037-SiBiL-x556")
        self.assertEqual(xsdata.imageDirectory, "/img/dir/")
        self.assertEqual(xsdata.fileTemplate, "Prtk-Vt-G2_%06d.h5")
        self.assertEqual(xsdata.beamShape, "ellipse")
        self.assertEqual(xsdata.start_time, datetime(2020, 4, 1, 7, 55, 25))
        self.assertEqual(xsdata.end_time, datetime(2020, 4, 1, 7, 56, 44))
        self.assertEqual(xsdata.synchrotronMode, "Variable TopUp/Decay")

    def test_no_snaps(self):
        """
        test case when XML file does not contain any 'xtalSnapshotFullPathN' tags,
        which is the case for projects at HZB
        """
        xsdata = XSDataCollection(data_file_path(f"xs_data_no_snaps.xml"))

        # snapshots indices should be an empty list
        self.assertListEqual(list(xsdata.snapshot_indexes), [])
