from typing import Optional
from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponse, Http404
from fragview.projects import current_project, Project
from fragview.fileio import read_proj_text_file, read_proj_file


def _is_html(log_path: Path) -> bool:
    suffix = log_path.suffix.lower()
    return ".html" == suffix


def _log_not_found_resp(log_file):
    """
    standard response when requested log is not found
    """
    return HttpResponseNotFound(f"log file '{log_file}' not found")


def _show_text_log(request, proj, download_url: str, log_path):
    """
    render a text log
    """
    return render(
        request,
        "text_log.html",
        {
            "log_text": read_proj_text_file(proj, log_path),
            "log_path": log_path,
            "download_url": download_url,
        },
    )


def _get_absolute_path(
    project: Project, dataset_id, rel_log_path: Path
) -> Optional[Path]:
    dataset = project.get_dataset(dataset_id)
    if dataset is None:
        raise Http404(f"unknown dataset {dataset_id}")

    # try with dataset's results directory
    log_path = Path(project.get_dataset_results_dir(dataset), rel_log_path)
    if log_path.is_file():
        return log_path

    # try with dataset's process directory
    log_path = Path(project.get_dataset_process_dir(dataset), rel_log_path)
    if log_path.is_file():
        return log_path

    # try with dataset's data root directory
    log_path = Path(project.get_dataset_root_dir(dataset), rel_log_path)
    if log_path.is_file():
        return log_path

    # can't reconstruct path
    raise Http404(f"log file '{rel_log_path}' not found")


def show_dset(request, dataset_id, log_file):
    project = current_project(request)
    log_path = _get_absolute_path(project, dataset_id, Path(log_file))

    if log_path is None:
        return _log_not_found_resp(log_file)

    if _is_html(log_path):
        return HttpResponse(read_proj_file(log_path))

    download_url = f"/logs/dset/download/{dataset_id}/{log_file}"
    return _show_text_log(request, project, download_url, log_path)


def download_dset(request, dataset_id, log_file):
    project = current_project(request)
    log_path = _get_absolute_path(project, dataset_id, Path(log_file))

    return HttpResponse(
        read_proj_file(log_path),
        content_type="application/octet-stream",
    )


def htmldata_dset(request, dataset_id, data_file):
    project = current_project(request)
    log_path = _get_absolute_path(project, dataset_id, Path(data_file))

    return HttpResponse(read_proj_file(log_path))


def show_job(request, log_file):
    project = current_project(request)
    log_path = Path(project.logs_dir, log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    download_url = f"/logs/job/download/{log_file}"
    return _show_text_log(request, project, download_url, log_path)


def download_job(request, log_file):
    project = current_project(request)
    log_path = Path(project.logs_dir, log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    return HttpResponse(
        read_proj_file(log_path),
        content_type="application/octet-stream",
    )
