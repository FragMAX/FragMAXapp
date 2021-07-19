from typing import List
from pathlib import Path


def get_diffraction_pic_command(
    project, dataset, angle: int, dest_pic_file: Path
) -> List[str]:
    # TODO: implement this
    raise NotImplementedError()


# from os import path
# from fragview.sites import plugin
#
#
# class DiffractionImageMaker(plugin.DiffractionImageMaker):
#     def get_file_names(self, project, dataset, run, image_num):
#         cbf_data_num = f"{image_num:04d}"
#         cbf_file = _find_cbf_file(project, dataset, run, cbf_data_num)
#         jpeg_name = f"diffraction_{run}_{cbf_data_num}.jpeg"
#
#         return cbf_file, jpeg_name
#
#     def get_command(self, source_file, dest_pic_file):
#         return ["/soft/pxsoft/64/adxv/adxv", "-sa", source_file, dest_pic_file]
#
#
# def _find_cbf_file(proj, dataset, run, cbf_data_num):
#
#     cbf_file = path.join(
#         proj.data_path(),
#         "raw",
#         proj.protein,
#         dataset,
#         f"{dataset}_{run}_{cbf_data_num}.cbf",
#     )
#     if path.isfile(cbf_file):
#         return cbf_file
#
#     # CBF file not found
#     raise DiffractionImageMaker.SourceImageNotFound()
