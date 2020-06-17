import os
from os import path
import zipstream
from pathlib import Path
from django.http import StreamingHttpResponse
from django.shortcuts import render
from fragview.projects import current_project, project_pandda_results_dir
from fragview.fileio import read_proj_file


def _get_pandda_dirs(proj):
    """
    list available pandda analysis results directories
    """
    pandda_res_dir = project_pandda_results_dir(proj)
    if not path.isdir(pandda_res_dir):
        return None

    return os.listdir(pandda_res_dir)


def page(request):
    """
    render download form page
    """
    proj = current_project(request)

    return render(request,
                  "fragview/download.html",
                  {"pandda_dirs": _get_pandda_dirs(proj)})


def _dir_archive_entries(proj, root_dir):
    def _file_data(proj, file_path):
        yield read_proj_file(proj, file_path)

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            abs_path = Path(dirpath, filename)
            arch_path = abs_path.relative_to(root_dir)

            yield arch_path, _file_data(proj, abs_path)


def _zipstream_pandda_dirs(proj, pandda_dirs):
    pandda_root = project_pandda_results_dir(proj)

    z = zipstream.ZipFile(mode="w",
                          compression=zipstream.ZIP_DEFLATED,
                          allowZip64=True)

    for dir in pandda_dirs:
        abs_path = path.join(pandda_root, dir)

        for n, data in _dir_archive_entries(proj, abs_path):
            z.write_iter(path.join(dir, n), data)

    return z


def pandda(request):
    proj = current_project(request)

    # figure out which result dirs where selected (checked)
    selected_dirs = [
        d for d in _get_pandda_dirs(proj)
        if d in request.POST
    ]

    zip_name = f"{proj.protein}{proj.library.name}_PanDDa.zip"

    resp = StreamingHttpResponse(_zipstream_pandda_dirs(proj, selected_dirs),
                                 content_type="application/zip")
    resp["Content-Disposition"] = f"attachment; filename={zip_name}"

    return resp
