import xmltodict
from dateutil import parser as date_parser
from datetime import datetime, timezone


class XSDataCollection:
    def __init__(self, xmlfile):
        with open(xmlfile, "rb") as f:
            doc = xmltodict.parse(f)

        self.node = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]

    def _float_tag(self, tag_name):
        return float(self.node[tag_name])

    def _int_tag(self, tag_name):
        return int(self.node[tag_name])

    def _datetime_tag(self, tag_name):
        dt = date_parser.parse(self.node[tag_name])

        # convert to UTC time zone
        utc_dt = dt.astimezone(timezone.utc)

        #
        # remove time zone info, as pony ORM does not support time zones
        # see this issue: https://github.com/ponyorm/pony/issues/434
        #
        # we store datetime in database without explicit time zone, and
        # always assume UTC time zone as a work-around
        #
        return utc_dt.replace(tzinfo=None)

    @property
    def snapshot_indexes(self):
        for i in range(1, 5):
            snap = self.node.get(f"xtalSnapshotFullPath{i}")
            if snap is None or snap == "None":
                # no snapshot for this index available
                continue

            yield i

    @property
    def imagePrefix(self):
        return self.node["imagePrefix"]

    @property
    def imageDirectory(self):
        return self.node["imageDirectory"]

    @property
    def fileTemplate(self):
        return self.node["fileTemplate"]

    @property
    def axisStart(self):
        return self._float_tag("axisStart")

    @property
    def axisEnd(self):
        return self._float_tag("axisEnd")

    @property
    def flux(self):
        return self._float_tag("flux")

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
    def num_images(self):
        return self._int_tag("numberOfImages")

    @property
    def dataCollectionNumber(self):
        return self._int_tag("dataCollectionNumber")

    @property
    def beamShape(self):
        return self.node["beamShape"]

    @property
    def start_time(self) -> datetime:
        return self._datetime_tag("startTime")

    @property
    def end_time(self) -> datetime:
        return self._datetime_tag("endTime")

    @property
    def synchrotronMode(self):
        return self.node["synchrotronMode"]
