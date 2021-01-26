from os import path
from django.http import HttpResponseNotFound
from fragview.projects import (
    current_project,
    project_process_protein_dir,
)
from fragview.sites import SITE
from fragview.sites.plugin import DiffractionImageMaker
from fragview.views.utils import jpeg_http_response
from worker.diffractions import get_diffraction


def image(request, dataset, run, image_num):
    """
    generated diffraction jpeg picture for given dataset run and specified 'angle'

    angle is specified by the H5 data file number 'image_num' parameter
    """
    proj = current_project(request)

    diffraction_maker = SITE.get_diffraction_img_maker()
    try:
        src_file, jpeg_name = diffraction_maker.get_file_names(
            proj, dataset, run, image_num
        )
    except DiffractionImageMaker.SourceImageNotFound:
        return HttpResponseNotFound("diffraction source file not found")

    jpeg_file = path.join(project_process_protein_dir(proj), dataset, jpeg_name)

    # request worker to generate diffraction jpeg and wait until it's completed
    get_diffraction.delay(src_file, jpeg_file).wait()

    return jpeg_http_response(proj, jpeg_file)
