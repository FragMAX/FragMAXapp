from pathlib import Path
from fragview.sites.hzb.utils import get_dataset_frame_image


def get_diffraction_pic_command(
    project, dataset, angle: int, dest_pic_file: Path
) -> list[str]:
    frame_num = int(angle / dataset.angle_increment) + 1
    cbf_file = get_dataset_frame_image(project, dataset, frame_num)

    return ["/soft/pxsoft/64/adxv/adxv", "-sa", str(cbf_file), str(dest_pic_file)]
