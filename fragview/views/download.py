from typing import Iterable
import os
from os import path
import zipstream
from pathlib import Path
from django.http import StreamingHttpResponse
from django.shortcuts import render
from fragview.projects import current_project, Project
from fragview.fileio import read_proj_file


def _get_method_dirs(project: Project) -> Iterable[str]:
    """
    list available pandda analysis results directories
    """
    if not project.pandda_dir.is_dir():
        return

    for child in project.pandda_dir.iterdir():
        if not child.is_dir():
            continue

        yield child.name


def page(request):
    """
    render download form page
    """
    project = current_project(request)

    return render(request,
                  "fragview/download.html",
                  {"pandda_dirs": _get_method_dirs(project)})


def _dir_archive_entries(proj, root_dir):
    def _file_data(proj, file_path):
        yield read_proj_file(proj, file_path)

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            abs_path = Path(dirpath, filename)
            arch_path = abs_path.relative_to(root_dir)

            if not abs_path.is_file():
                #
                # ignore broken symlinks
                #
                # pandda creates symlinks in some directories,
                # which in some situations come out broken
                # for now, just skip including the into archive
                #
                continue

            yield arch_path, _file_data(proj, abs_path)


def _zipstream_pandda_dirs(project, pandda_dirs):
    z = zipstream.ZipFile(mode="w",
                          compression=zipstream.ZIP_DEFLATED,
                          allowZip64=True)

    for dir in pandda_dirs:
        abs_path = path.join(project.pandda_dir, dir)

        for n, data in _dir_archive_entries(project, abs_path):
            z.write_iter(path.join(dir, n), data)

    return z


def pandda(request):
    project = current_project(request)

    # figure out which result dirs where selected (checked)
    selected_dirs = [
        d for d in _get_method_dirs(project)
        if d in request.POST
    ]

    zip_name = f"{project.name}_PanDDa.zip"
    # cut out any spaces from zip file name
    zip_name = zip_name.replace(" ", "")

    resp = StreamingHttpResponse(_zipstream_pandda_dirs(project, selected_dirs),
                                 content_type="application/zip")
    resp["Content-Disposition"] = f"attachment; filename={zip_name}"

    return resp
