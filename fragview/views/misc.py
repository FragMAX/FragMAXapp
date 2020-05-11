from django.shortcuts import render


def project_details(request):
    return render(request, "fragview/project_details.html")


def download_options(request):
    return render(request, "fragview/download_options.html")


def testfunc(request):
    return render(request, "fragview/testpage.html", {"files": "results"})


def ugly(request):
    return render(request, "fragview/ugly.html")


def log_viewer(request):
    logFile = str(request.GET.get('logFile'))
    logFile = "biomax" + logFile.split("biomax")[-1]
    logFile = f"/data/visitors/{logFile}"
    downloadPath = f"/static/{logFile}"
    if path.exists(logFile):
        with open(logFile, "r") as r:
            log = "".join(r.readlines())
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
