from django.shortcuts import render
from django.conf import settings
from os import path
from fragview.projects import current_project
from glob import glob


def project_details(request):
    return render(request, "fragview/project_details.html")


def library_view(request):
    proj = current_project(request)

    fragments = sorted([x.split("/")[-1].replace(".cif", "") for x
                        in glob(f"{proj.data_path()}/fragmax/fragments/*cif")])
    lib = proj.library
    project_fragments = {x: lib.get_fragment(x).smiles for x in fragments}
    data_path = proj.data_path().replace("/data/visitors/", "/static/")

    return render(request, "fragview/library_view.html", {
        "project_fragments": project_fragments,
        "data_path": data_path
    })


def download_options(request):
    return render(request, "fragview/download_options.html")


def testfunc(request):
    return render(request, "fragview/testpage.html", {"files": "results"})


def ugly(request):
    return render(request, "fragview/ugly.html")


def log_viewer(request):
    logFile = request.GET["logFile"]
    downloadPath = f"/static/biomax{logFile[len(settings.PROPOSALS_DIR):]}"

    if path.exists(logFile):
        with open(logFile, "r") as r:
            log = r.read()
    else:
        log = ""

    return render(
        request,
        "fragview/log_viewer.html",
        {
            "log": log,
            "dataset": logFile,
            "downloadPath": downloadPath
        })
