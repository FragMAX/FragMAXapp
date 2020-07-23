from os import path
from fragview.sites import plugin


class DiffractionImageMaker(plugin.DiffractionImageMaker):
    def get_file_names(self, project, dataset, run, image_num):
        h5_data_num = f"{image_num:06d}"
        h5_file = _find_h5_file(project, dataset, run, h5_data_num)
        jpeg_name = f"diffraction_{run}_{h5_data_num}.jpeg"

        return h5_file, jpeg_name

    def get_command(self, source_file, dest_pic_file):
        return ["adxv", "-sa", "-slabs", "10", "-weak_data", source_file, dest_pic_file]


def _find_h5_file(proj, dataset, run, h5_data_num):
    from fragview.projects import project_shift_dirs

    for shift_dir in project_shift_dirs(proj):
        h5_file = path.join(
            shift_dir,
            "raw",
            proj.protein,
            dataset,
            f"{dataset}_{run}_data_{h5_data_num}.h5",
        )
        if path.isfile(h5_file):
            return h5_file

    # H5 file not found
    raise DiffractionImageMaker.SourceImageNotFound()
