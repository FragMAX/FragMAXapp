from pathlib import Path
from typing import List


# TODO: investigate if we can read this number from HDF5 files somehow
FRAMES_PER_FILE = 100


def get_diffraction_pic_command(
    project, dataset, angle: int, dest_pic_file: Path
) -> List[str]:
    first_frame = int(angle / dataset.oscillation_range)
    file_num = (first_frame // FRAMES_PER_FILE) + 1
    slab_num = (first_frame % FRAMES_PER_FILE) + 1

    h5_file = Path(
        project.get_dataset_raw_dir(dataset),
        f"{project.protein}-{dataset.name}_data_{file_num:06d}.h5",
    )

    return [
        "adxv",
        "-sa",
        "-slab",
        str(slab_num),
        "-slabs",
        "10",
        "-weak_data",
        str(h5_file),
        str(dest_pic_file),
    ]
