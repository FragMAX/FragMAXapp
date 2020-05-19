import unittest
from os import path
from fragview.xsdata import XSDataCollection

XML_FILENAME = "xs_data_result.xml"
EXPECTED_SNAPSHOTS = ["/some/dir/Prtk-Vt-G2_1_1.snapshot.jpeg",
                      "/some/dir/Prtk-Vt-G2_1_2.snapshot.jpeg"]


def _xml_path():
    return path.join(path.dirname(__file__), "data", XML_FILENAME)


class TestXSDataCollection(unittest.TestCase):
    def test_parser(self):
        # parse the XML file
        xsdata = XSDataCollection(_xml_path())

        # check that we get expected data
        self.assertListEqual(xsdata.snapshots, EXPECTED_SNAPSHOTS)
        self.assertAlmostEqual(xsdata.axisStart, 2.70001e+02)
        self.assertAlmostEqual(xsdata.axisEnd, 6.300010e+02)
        self.assertAlmostEqual(xsdata.flux, 2.7e+12)
        self.assertAlmostEqual(xsdata.wavelength, 9.762530e-01)
        self.assertAlmostEqual(xsdata.exposureTime, 1.100000e-02)
        self.assertAlmostEqual(xsdata.resolution, 1.600000e+00)
        self.assertAlmostEqual(xsdata.beamSizeSampleX, 5.000000e+01)
        self.assertAlmostEqual(xsdata.beamSizeSampleY, 5.000000e+01)
        self.assertAlmostEqual(xsdata.axisRange, 1.000000e-01)
        self.assertAlmostEqual(xsdata.detectorDistance, 2.152600e+02)
        self.assertAlmostEqual(xsdata.overlap, 0)
        self.assertAlmostEqual(xsdata.xbeam, 2.100770e+03)
        self.assertAlmostEqual(xsdata.ybeam, 2.120790e+03)
        self.assertAlmostEqual(xsdata.transmission, 1.000000e+02)
        self.assertAlmostEqual(xsdata.slitGapVertical, 5.000000e+01)
        self.assertAlmostEqual(xsdata.slitGapHorizontal, 5.000000e+01)
        self.assertEqual(xsdata.numberOfImages, 3600)
        self.assertEqual(xsdata.imageDirectory, "/img/dir/")
        self.assertEqual(xsdata.beamShape, "ellipse")
        self.assertEqual(xsdata.startTime, "2020-04-01 09:55:25+02:00")
        self.assertEqual(xsdata.endTime, "2020-04-01 09:56:44+02:00")
        self.assertEqual(xsdata.synchrotronMode, "Variable TopUp/Decay")

        # fetch snapshots list second time, to test 'cached snapshots' code path
        self.assertListEqual(xsdata.snapshots, EXPECTED_SNAPSHOTS)
