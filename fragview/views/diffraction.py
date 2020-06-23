from os import path
from django.shortcuts import redirect
from django.http import HttpResponseNotFound
from fragview.projects import current_project, project_shift_dirs, project_process_protein_dir, project_static_url
from worker.diffractions import get_diffraction


def _find_h5_file(proj, dataset, run, h5_data_num):
    for shift_dir in project_shift_dirs(proj):
        h5_file = path.join(shift_dir, "raw", proj.protein, dataset, f"{dataset}_{run}_data_{h5_data_num}.h5")
        if path.isfile(h5_file):
            return h5_file

    # H5 file not found
    return None


def _find_cbf_file(proj, dataset, run, cbf_data_num):

    cbf_file = path.join(proj.data_path(), "raw", proj.protein, dataset, f"{dataset}_{run}_{cbf_data_num}.cbf")
    if path.isfile(cbf_file):
        return cbf_file

    # H5 file not found
    return None


def image(request, dataset, run, image_num):
    """
    generated diffraction jpeg picture for given dataset run and specified 'angle'

    angle is specified by the H5 data file number 'image_num' parameter
    """
    proj = current_project(request)

    # h5_data_num = f"{image_num:06d}"
    cbf_data_num = f"{image_num:04d}"

    # h5_file = _find_h5_file(proj, dataset, run, h5_data_num)
    cbf_file = _find_cbf_file(proj, dataset, run, cbf_data_num)
    # if h5_file is None:
    #     return HttpResponseNotFound("H5 file found")
    if cbf_file is None:
        return HttpResponseNotFound("CBF file found")
    jpeg_name = f"diffraction_{run}_{cbf_data_num}.jpeg"
    jpeg_file = path.join(project_process_protein_dir(proj), dataset, jpeg_name)
    jpeg_url = path.join(project_static_url(proj), "fragmax", "process", proj.protein, dataset, jpeg_name)

    # request worker to generate diffraction jpeg and wait until it's completed
    get_diffraction.delay(cbf_file, jpeg_file).wait()

    # redirect client to the generated jpeg file
    return redirect(jpeg_url)
