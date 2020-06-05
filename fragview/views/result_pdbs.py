from os import path
from fragview.fileio import read_proj_file
from django.http import HttpResponse
from fragview.projects import current_project, project_results_dir


def final(request, dataset, process, refine):
    proj = current_project(request)
    pdb_path = path.join(project_results_dir(proj), dataset, process, refine, "final.pdb")

    return HttpResponse(read_proj_file(proj, pdb_path),
                        content_type="application/octet-stream")
