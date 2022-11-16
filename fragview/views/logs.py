from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponse
from fragview.projects import current_project
from fragview.fileio import read_proj_text_file, read_proj_file
from fragview.scraper import autoproc
from fragview.sites import SITE


def _is_html(log_path: Path) -> bool:
    suffix = log_path.suffix.lower()
    return ".html" == suffix


def _log_not_found_resp(log_file):
    """
    standard response when requested log is not found
    """
    return HttpResponseNotFound(f"log file '{log_file}' not found")


def htmldata(request, data_file):
    project = current_project(request)

    log_path = Path(project.project_dir, data_file)

    if not log_path.is_file():
        return HttpResponseNotFound()

    return HttpResponse(read_proj_file(project, log_path))


def _show_html_log(request, html_file_url):
    """
    render a HTML log
    """
    project = current_project(request)
    rel_path = html_file_url.relative_to(project.logs_dir)
    html_file_url = f"/logs/htmldata/{rel_path}"

    return render(request, "html_log.html", {"html_url": html_file_url})


def _show_text_log(request, proj, download_url, log_path):
    """
    render a text log
    """
    return render(
        request,
        "text_log.html",
        {
            "log_text": read_proj_text_file(proj, log_path),
            "log_path": log_path,
            "download_url": f"/logs/download/{download_url}",
        },
    )


def show(request, log_file):
    project = current_project(request)
    log_path = Path(project.logs_dir, log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    if _is_html(log_path):
        return _show_html_log(request, log_path)

    return _show_text_log(request, project, log_file, log_path)


def download(request, log_file):
    project = current_project(request)
    log_path = Path(project.logs_dir, log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    return HttpResponse(
        read_proj_file(project, log_path),
        content_type="application/octet-stream",
    )


def imported_htmldata(request, data_file):
    proj = current_project(request)

    log_path = Path(SITE.RAW_DATA_DIR, proj.proposal, data_file)

    if not log_path.is_file():
        return HttpResponseNotFound()

    return HttpResponse(read_proj_file(proj, log_path))


def _show_imported_html_log(request, log_file):
    """
    render a HTML log that is outside the fragmax folder,
    that is, in one of the shift folders

    this is used to display logs for auto-processing tools,
    which are imported into fragmax projects
    """
    proj = current_project(request)

    rel_path = log_file.relative_to(Path(SITE.RAW_DATA_DIR, proj.proposal))

    html_file_url = f"/logs/imported/htmldata/{rel_path}"

    return render(request, "html_log.html", {"html_url": html_file_url})


def show_autoproc(request, dataset, log_file):
    proj = current_project(request)
    log_path = Path(autoproc.get_logs_dir(proj, dataset), log_file)

    if not log_path.is_file():
        return _log_not_found_resp(log_file)

    if _is_html(log_path):
        return _show_imported_html_log(request, log_path)

    return _show_text_log(request, proj, log_file, log_path)
