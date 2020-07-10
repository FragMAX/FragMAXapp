import csv
from os import path
from django.http import HttpResponse
from django.shortcuts import render
from fragview.projects import current_project, project_results_file
from worker import resync_results
from worker import results


def show(request):
    proj = current_project(request)
    results_file = project_results_file(proj)

    resync_active = results.resync_active(proj)
    if not resync_active and not path.exists(results_file):
        # results file have not been created yet,
        # start the job to generate it
        _start_resync_job(proj)
        resync_active = True

    if resync_active:
        # re-synchronization is progress, show 'wait for it' page
        return render(request,
                      "fragview/results_notready.html")

    with open(results_file, "r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]

    for n, line in enumerate(lines):
        if len(line) == 23:
            lines[n].append("")
    return render(request, "fragview/results.html", {"csvfile": lines})


def _start_resync_job(proj):
    resync_results.delay(proj.id)


def resync(request):
    _start_resync_job(current_project(request))

    return HttpResponse("ok")
