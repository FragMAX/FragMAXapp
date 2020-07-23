from os import path
from glob import glob
from django.shortcuts import render
from django.conf import settings
from fragview.projects import current_project
from ast import literal_eval


def project_details(request):
    return render(request, "fragview/project_details.html")


def library_view(request):
    proj = current_project(request)

    fragments = sorted(
        [x.split("/")[-1].replace(".cif", "") for x in glob(f"{proj.data_path()}/fragmax/fragments/*cif")]
    )
    lib = proj.library
    project_fragments = {x: lib.get_fragment(x).smiles for x in fragments if lib.get_fragment(x) is not None}
    data_path = proj.data_path().replace("/data/visitors/", "/static/")

    return render(
        request, "fragview/library_view.html", {"project_fragments": project_fragments, "data_path": data_path}
    )


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
        if path.splitext(logFile)[-1] == ".json":
            filetype = "json"
            with open(logFile, "r", encoding="utf-8") as r:
                init_log = literal_eval(r.read())
            log = "<table>\n"
            for k, v in sorted(init_log.items()):
                log += f"<tr><td>{k}</td><td> {v}</td></tr>\n"
            log += "</table>"
        else:
            filetype = "txt"
            with open(logFile, "r", encoding="utf-8") as r:
                log = r.read()
    else:
        log = ""
        downloadPath = ""
        filetype = ""

    return render(
        request,
        "fragview/log_viewer.html",
        {"log": log, "dataset": logFile, "downloadPath": downloadPath, "filetype": filetype},
    )


def perc2float(v):
    return str("{:.3f}".format(float(v.replace("%", "")) / 100.0))
