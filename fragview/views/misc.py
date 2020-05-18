from django.shortcuts import render
from django.conf import settings
from os import path


def project_details(request):
    return render(request, "fragview/project_details.html")


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
