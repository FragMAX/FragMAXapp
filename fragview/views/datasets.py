from django.shortcuts import render

from fragview.projects import current_project
from fragview.status import run_update_status
from fragview.dsets import get_datasets
from fragview.sites import SITE


def show_all(request):
    proj = current_project(request)

    resyncStatus = str(request.GET.get("resyncstButton"))

    if "resyncStatus" in resyncStatus:
        run_update_status(proj)

    return render(
        request,
        "fragview/datasets.html",
        {"pipelines": SITE.get_supported_pipelines(), "datasets": get_datasets(proj)},
    )
