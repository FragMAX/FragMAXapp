from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponse
from fragview.projects import current_project
from fragview.fileio import read_proj_text_file, read_proj_file


def _get_file_path(proj, file_path):
    """
    convert the path relative to the project's data directory,
    to absolute path on the file system
    """
    return Path(proj.data_path(), file_path)


def _is_html(log_path):
    suffix = log_path.suffix.lower()
    return ".html" == suffix


def _log_not_found_resp(log_file):
    """
    standard response when requested log is not found
    """
    return HttpResponseNotFound(f"log file '{log_file}' not found")


def htmldata(request, data_file):
    proj = current_project(request)

    log_path = _get_file_path(proj, data_file)

    if not log_path.is_file():
        return HttpResponseNotFound()

    return HttpResponse(read_proj_file(proj, log_path))


def _show_html_log(request, html_file_url):
    """
    render a HTML log
    """
    proj = current_project(request)

    rel_path = html_file_url.relative_to(proj.data_path())
    html_file_url = f"/logs/htmldata/{rel_path}"

    return render(request, "fragview/html_log.html", {"html_url": html_file_url})


def _show_text_log(request, proj, download_url, log_path):
    """
    render a text log
    """
    return render(
        request,
        "fragview/text_log.html",
        {
            "log_text": read_proj_text_file(proj, log_path),
            "log_path": log_path,
            "download_url": f"/logs/download/{download_url}",
        },
    )


def show(request, log_file):
    proj = current_project(request)
    log_path = _get_file_path(proj, log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    if _is_html(log_path):
        return _show_html_log(request, log_path)

    return _show_text_log(request, proj, log_file, log_path)


def download(request, log_file):
    proj = current_project(request)
    log_path = _get_file_path(proj, log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    return HttpResponse(
        read_proj_file(proj, log_path), content_type="application/octet-stream",
    )
