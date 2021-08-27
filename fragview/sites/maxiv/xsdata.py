import xmltodict
from pathlib import Path
from dateutil import parser as date_parser
from datetime import datetime, timezone
from fragview.sites.plugin import DatasetMetadata


def parse_xsdata_file(xmlfile: Path) -> DatasetMetadata:
    def _float(tag_name: str) -> float:
        return float(node[tag_name])

    def _int(tag_name: str) -> int:
        return int(node[tag_name])

    def _datetime(tag_name) -> datetime:
        dt = date_parser.parse(node[tag_name])

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

    def _snapshot_indices():
        for i in range(1, 5):
            snap = node.get(f"xtalSnapshotFullPath{i}")
            if snap is None or snap == "None":
                # no snapshot for this index available
                continue

            yield i

    with xmlfile.open("rb") as f:
        doc = xmltodict.parse(f)

    node = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]

    return DatasetMetadata(
        # hard-code detector for now as there is only
        # one MX detector in operation at MAXIV
        detector="EIGER 16M",
        resolution=_float("resolution"),
        images=_int("numberOfImages"),
        start_time=_datetime("startTime"),
        end_time=_datetime("endTime"),
        wavelength=_float("wavelength"),
        start_angle=_float("axisStart"),
        angle_increment=_float("axisRange"),
        exposure_time=_float("exposureTime"),
        detector_distance=_float("detectorDistance"),
        xbeam=_float("xbeam"),
        ybeam=_float("ybeam"),
        beam_shape=node["beamShape"],
        transmission=_float("transmission"),
        slit_gap_horizontal=_float("slitGapHorizontal") * 1000,
        slit_gap_vertical=_float("slitGapVertical") * 1000,
        flux=_float("flux"),
        beam_size_at_sample_x=_float("beamSizeAtSampleX") * 1000,
        beam_size_at_sample_y=_float("beamSizeAtSampleY") * 1000,
        snapshot_indices=list(_snapshot_indices()),
    )
