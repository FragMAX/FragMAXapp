import xmltodict


class XSDataCollection:
    def __init__(self, xmlfile):
        with open(xmlfile, "rb") as f:
            doc = xmltodict.parse(f)

        self.node = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        self._snapshots = None

    def _float_tag(self, tag_name):
        return float(self.node[tag_name])

    def _int_tag(self, tag_name):
        return int(self.node[tag_name])

    def _get_snapshots(self):
        for i in range(1, 5):
            snap = self.node[f"xtalSnapshotFullPath{i}"]
            if snap != "None":
                yield snap

    @property
    def snapshots(self):
        if self._snapshots is None:
            self._snapshots = list(self._get_snapshots())

        return self._snapshots

    @property
    def axisStart(self):
        return self._float_tag("axisStart")

    @property
    def axisEnd(self):
        return self._float_tag("axisEnd")

    @property
    def wavelength(self):
        return self._float_tag("wavelength")

    @property
    def exposureTime(self):
        return self._float_tag("exposureTime")

    @property
    def resolution(self):
        return self._float_tag("resolution")

    @property
    def beamSizeSampleX(self):
        return self._float_tag("beamSizeAtSampleX") * 1000

    @property
    def beamSizeSampleY(self):
        return self._float_tag("beamSizeAtSampleY") * 1000

    @property
    def axisRange(self):
        return self._float_tag("axisRange")

    @property
    def detectorDistance(self):
        return self._float_tag("detectorDistance")

    @property
    def overlap(self):
        return self._float_tag("overlap")

    @property
    def xbeam(self):
        return self._float_tag("xbeam")

    @property
    def ybeam(self):
        return self._float_tag("ybeam")

    @property
    def transmission(self):
        return self._float_tag("transmission")

    @property
    def slitGapVertical(self):
        return self._float_tag("slitGapVertical") * 1000

    @property
    def slitGapHorizontal(self):
        return self._float_tag("slitGapHorizontal") * 1000

    @property
    def numberOfImages(self):
        return self._int_tag("numberOfImages")

    @property
    def beamShape(self):
        return self.node["beamShape"]

    @property
    def startTime(self):
        return self.node["startTime"]

    @property
    def endTime(self):
        return self.node["endTime"]

    @property
    def synchrotronMode(self):
        return self.node["synchrotronMode"]
