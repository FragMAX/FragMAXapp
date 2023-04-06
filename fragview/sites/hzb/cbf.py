from typing import Optional
import re
import fabio
from re import Pattern
from pathlib import Path
from dateutil import parser as date_parser
from datetime import datetime
from fragview.sites.plugin import DatasetMetadata


START_TIME_LINE_NO = 1

DETECTOR_LINE_NO = 0
DETECTOR_RE = re.compile(r"^# Detector: ([^,]+), S/N ([\d-]*)")

DETECTOR_DISTANCE_LINE_NO = 16
DETECTOR_DISTANCE_RE = re.compile(r"^# Detector_distance (\d*\.\d+) m")

IMAGES_LINE_NO = 10
IMAGES_RE = re.compile(r"^# N_oscillations (\d+)")

WAVELENGTH_LINE_NO = 30
WAVELENGTH_RE = re.compile(r"^# Wavelength (\d*\.\d+) A")

START_ANGLE_LINE_NO = 15
START_ANGLE_RE = re.compile(r"^# Start_angle (-?\d*\.\d+) deg")

ANGLE_INCREMENT_LINE_NO = 7
ANGLE_INCREMENT_RE = re.compile(r"^# Angle_increment (\d*\.\d+) deg")

EXPOSURE_TIME_LINE_NO = 12
EXPOSURE_TIME_RE = re.compile(r"^# Exposure_time (\d*\.\d+) s")

TRANSMISSION_LINE_NO = 25
TRANSMISSION_RE = re.compile(r"^# Transmission (\d*\.\d+)")

FLUX_LINE_NO = 27
FLUX_RE = re.compile(r"^# Flux (\d*e\+\d+)")

BEAM_XY_LINE_NO = 11
BEAM_XY_RE = re.compile(r"^# Beam_xy \((\d*\.\d+), (\d*\.\d+)\) pixels")


class CbfHeaderParseError(Exception):
    pass


# Detector serial number for each MX beamline at HZB
BEAMLINE_DETECTORS = {
    "60-0138": "14.1",
    "24-0124": "14.2",
    "60-0118": "14.3",
}


def _get_array_data_header(cbf_file: Path) -> list[str]:
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


def _get_beamline(detector_serial: str) -> str:
    beamline = BEAMLINE_DETECTORS.get(detector_serial)
    if beamline is None:
        raise CbfHeaderParseError(f"unknown detector serial number '{detector_serial}'")

    return beamline


def _parse_detector(line: str) -> tuple[str, str]:
    match = DETECTOR_RE.match(line)
    if match is None:
        raise CbfHeaderParseError(f"error parsing detector info from '{line}'")

    detector_model, detector_serial = match.groups()

    return detector_model, _get_beamline(detector_serial)


def _parse_beam_xy(line: str) -> tuple[float, float]:
    match = BEAM_XY_RE.match(line)
    if match is None or len(match.groups()) != 2:
        raise CbfHeaderParseError(f"error parsing beam xy from '{line}'")

    x, y = match.groups()
    return float(x), float(y)


def parse_metadata(cbf_file: Path) -> Optional[DatasetMetadata]:
    header = _get_array_data_header(cbf_file)

    detector, beamline = _parse_detector(header[DETECTOR_LINE_NO])

    val = _parse_detector_distance(header[DETECTOR_DISTANCE_LINE_NO])
    detector_distance = val * 1000
    resolution = val * 8.178158027176648

    beam_size_at_sample_x, beam_size_at_sample_y = _parse_beam_xy(
        header[BEAM_XY_LINE_NO]
    )

    return DatasetMetadata(
        beamline=beamline,
        detector=detector,
        resolution=resolution,
        images=_parse_images(header[IMAGES_LINE_NO]),
        start_time=_parse_datetime(header[START_TIME_LINE_NO]),
        end_time=None,
        wavelength=_parse_wavelength(header[WAVELENGTH_LINE_NO]),
        start_angle=_parse_start_angle(header[START_ANGLE_LINE_NO]),
        angle_increment=_parse_angle_increment(header[ANGLE_INCREMENT_LINE_NO]),
        exposure_time=_parse_exposure_time(header[EXPOSURE_TIME_LINE_NO]),
        detector_distance=detector_distance,
        xbeam=None,
        ybeam=None,
        beam_shape="ellipse",
        transmission=_parse_transmission(header[TRANSMISSION_LINE_NO]),
        slit_gap_horizontal=None,
        slit_gap_vertical=None,
        flux=_parse_flux(header[FLUX_LINE_NO]),
        beam_size_at_sample_x=beam_size_at_sample_x,
        beam_size_at_sample_y=beam_size_at_sample_y,
    )
