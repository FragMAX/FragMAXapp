from pathlib import Path
from h5py import File, Dataset
from fragview.sites.plugin import DatasetMetadata


def _str(dset: Dataset) -> str:
    return dset[()].decode()


def _read_metadata(f: File) -> DatasetMetadata:
    entry = f["entry"]

    return DatasetMetadata(
        detector=_str(entry["instrument"]["detector"]["description"]),
        images=entry["instrument"]["detector"]["detectorSpecific"]["nimages"][()],
        xbeam=entry["instrument"]["detector"]["beam_center_x"][()],
        ybeam=entry["instrument"]["detector"]["beam_center_y"][()],
        wavelength=entry["instrument"]["beam"]["incident_wavelength"][()],
        beamline=_str(entry["instrument"]["name"]),
        start_angle=entry["sample"]["goniometer"]["omega"][0],
        angle_increment=entry["sample"]["goniometer"]["omega_range_average"][()],
        detector_distance=(
            entry["instrument"]["detector"]["detector_distance"][()] * 1000
        ),
    )


def read_metadata(master_file: Path) -> DatasetMetadata:
    with File(master_file, "r") as f:
        return _read_metadata(f)
