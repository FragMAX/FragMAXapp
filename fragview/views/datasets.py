from django.shortcuts import render

from fragview.projects import current_project
from fragview.status import run_update_status
from fragview.dsets import get_datasets


def show_all(request):
    proj = current_project(request)

    resyncStatus = str(request.GET.get("resyncstButton"))

    if "resyncStatus" in resyncStatus:
        run_update_status(proj)

    return render(request, "fragview/datasets.html", {"datasets": get_datasets(proj)})


def proc_report(request):

    report = str(request.GET.get("logFile"))

    if "/data/visitors" in report:
        report = report.replace("/data/visitors/", "/static/")

    return render(request, "fragview/procReport.html", {"reportHTML": report})
