import pandas
from os import path
from django.http import HttpResponse
from django.shortcuts import render
from fragview.projects import current_project, project_results_file
from fragview.fileio import read_csv_lines
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

    lines = read_csv_lines(results_file)[1:]

    for n, line in enumerate(lines):
        if len(line) == 23:
            lines[n].append("")
    return render(request, "fragview/results.html", {"csvfile": lines})


def _start_resync_job(proj):
    resync_results.delay(proj.id)


def resync(request):
    _start_resync_job(current_project(request))

    return HttpResponse("ok")


def isa(request):
    """
    return ISa statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    proj = current_project(request)

    data = pandas.read_csv(project_results_file(proj))

    data["dataset"] = data["dataset"].map(lambda name: name[-9:])
    isa_mean_by_dataset = data.groupby("dataset")["ISa"].mean().round(2).to_frame(name="mean").reset_index()
    isa_std_by_dataset = data.groupby("dataset")["ISa"].std().round(2).to_frame(name="std").reset_index()

    result = isa_mean_by_dataset.merge(isa_std_by_dataset)

    return HttpResponse(result.to_json(), content_type="application/json")
