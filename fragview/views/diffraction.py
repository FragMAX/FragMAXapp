from pathlib import Path
from fragview.projects import current_project
from fragview.sites import SITE
from fragview.projects import Project
from fragview.views.utils import jpeg_http_response, get_dataset_by_id
from worker.diffractions import make_diffraction_jpeg


def _jpeg_image_path(project: Project, dataset, angle: str) -> Path:
    return Path(project.get_dataset_process_dir(dataset), f"diffraction_{angle}.jpeg")


def image(request, dataset_id: str, angle: str):
    """
    generated diffraction jpeg picture for given dataset and specified angle

    Angle is relative to the first frame. First frame is defined to be at angle 0°,
    next frame at 0° + <oscillation range>, etc.

    That is, each frames angle is defined as:

       <angle> = <frame number> *  <oscillation range>.

    """
    project = current_project(request)
    dataset = get_dataset_by_id(project, dataset_id)

    jpeg_file = _jpeg_image_path(project, dataset, angle)
    if not jpeg_file.is_file():
        jpeg_file.parent.mkdir(parents=True, exist_ok=True)
        # request worker to run diffraction jpeg generation command
        # and wait until it's completed
        cmd = SITE.get_diffraction_picture_command(
            project, dataset, int(angle), jpeg_file
        )
        make_diffraction_jpeg.delay(cmd).wait()

    return jpeg_http_response(project, jpeg_file)
