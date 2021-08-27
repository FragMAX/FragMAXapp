from typing import List, Tuple
import re
import fabio
from re import Pattern
from pathlib import Path
from dateutil import parser as date_parser
from datetime import datetime
from fragview.sites.plugin import DatasetMetadata


class CbfHeaderParseError(Exception):
    pass


DETECTOR_RE = re.compile(r"^# Detector: ([^,]+), ")
DETECTOR_DISTANCE_RE = re.compile(r"^# Detector_distance (\d*\.\d+) m")
IMAGES_RE = re.compile(r"^# N_oscillations (\d+)")
WAVELENGTH_RE = re.compile(r"^# Wavelength (\d*\.\d+) A")
START_ANGLE_RE = re.compile(r"^# Start_angle (-?\d*\.\d+) deg")
ANGLE_INCREMENT_RE = re.compile(r"^# Angle_increment (\d*\.\d+) deg")
EXPOSURE_TIME_RE = re.compile(r"^# Exposure_time (\d*\.\d+) s")
TRANSMISSION_RE = re.compile(r"^# Transmission (\d*\.\d+)")
FLUX_RE = re.compile(r"^# Flux (\d*e\+\d+)")
BEAM_XY_RE = re.compile(r"^# Beam_xy \((\d*\.\d+), (\d*\.\d+)\) pixels")


def _get_array_data_header(cbf_file: Path) -> List[str]:
    with fabio.open(str(cbf_file)) as img:
        array_data = img.header["_array_data.header_contents"]
        return array_data.splitlines()


def _match(pattern: Pattern, line: str, line_name: str):
    match = pattern.match(line)
    if match is None:
        raise CbfHeaderParseError(f"error parsing {line_name} from '{line}'")

    return match.groups()[0]


def _parse_detector_distance(line: str) -> float:
    return float(_match(DETECTOR_DISTANCE_RE, line, "detector distance"))


def _parse_images(line: str) -> int:
    return int(_match(IMAGES_RE, line, "images"))


def _parse_datetime(line: str) -> datetime:
    _, line = line.split(" ", 1)  # shop of the '# ' prefix
    return date_parser.parse(line)


def _parse_wavelength(line: str) -> float:
    return float(_match(WAVELENGTH_RE, line, "wavelength"))


def _parse_start_angle(line: str) -> float:
    return float(_match(START_ANGLE_RE, line, "start_angle"))


def _parse_angle_increment(line: str) -> float:
    return float(_match(ANGLE_INCREMENT_RE, line, "angle_increment"))


def _parse_exposure_time(line: str) -> float:
    return float(_match(EXPOSURE_TIME_RE, line, "exposure time"))


def _parse_transmission(line: str) -> float:
    return float(_match(TRANSMISSION_RE, line, "transmission"))


def _parse_flux(line: str) -> float:
    return float(_match(FLUX_RE, line, "flux"))


def _parse_detector(line: str) -> str:
    return _match(DETECTOR_RE, line, "detector")


def _parse_beam_xy(line: str) -> Tuple[float, float]:
    match = BEAM_XY_RE.match(line)
    if match is None or len(match.groups()) != 2:
        raise CbfHeaderParseError(f"error parsing beam xy from '{line}'")

    x, y = match.groups()
    return float(x), float(y)


def parse_metadata(cbf_file: Path) -> DatasetMetadata:
    header = _get_array_data_header(cbf_file)

    val = _parse_detector_distance(header[16])
    detector_distance = val * 1000
    resolution = val * 8.178158027176648

    beam_size_at_sample_x, beam_size_at_sample_y = _parse_beam_xy(header[11])

    return DatasetMetadata(
        detector=_parse_detector(header[0]),
        resolution=resolution,
        images=_parse_images(header[10]),
        start_time=_parse_datetime(header[1]),
        end_time=None,
        wavelength=_parse_wavelength(header[30]),
        start_angle=_parse_start_angle(header[15]),
        angle_increment=_parse_angle_increment(header[7]),
        exposure_time=_parse_exposure_time(header[12]),
        detector_distance=detector_distance,
        xbeam=None,
        ybeam=None,
        beam_shape="ellipse",
        transmission=_parse_transmission(header[25]),
        slit_gap_horizontal=None,
        slit_gap_vertical=None,
        flux=_parse_flux(header[27]),
        beam_size_at_sample_x=beam_size_at_sample_x,
        beam_size_at_sample_y=beam_size_at_sample_y,
    )
