import pandas
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
        reader = csv.DictReader(readFile)
        results_data = [row for row in reader]

    return render(request, "fragview/results.html", {"results": results_data})


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

    # ignore data row when isa is unknown
    data = data[data["ISa"]!="unknown"]
    data["ISa"] = pandas.to_numeric(data["ISa"])

    # for each dataset name: group the data and calculate mean and standard error
    isa_mean_by_dataset = data.groupby("dataset")["ISa"].mean().to_frame(name="mean").reset_index()
    isa_mean_by_dataset["mean"] = isa_mean_by_dataset["mean"].round(2)
    std_err_by_dataset = data.groupby("dataset")["ISa"].std().round(2).to_frame(name="std").reset_index()

    result = isa_mean_by_dataset.merge(std_err_by_dataset)

    return HttpResponse(result.to_json(), content_type="application/json")


def rfactor(request):
    """
    return rfactors statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    proj = current_project(request)
    print(project_results_file(proj))
    data = pandas.read_csv(project_results_file(proj))

    data["r_work"] = pandas.to_numeric(data["r_work"])
    data["r_free"] = pandas.to_numeric(data["r_free"])

    rwork_mean_by_dataset = data.groupby('dataset')['r_work'].mean().round(2).to_frame(name='rwork').reset_index()
    rfree_mean_by_dataset = data.groupby('dataset')['r_free'].mean().round(2).to_frame(name='rfree').reset_index()
    std_rwork_by_dataset = data.groupby('dataset')['r_work'].std().round(2).to_frame(name='std_rw').reset_index()
    std_rfree_by_dataset = data.groupby('dataset')['r_free'].std().round(2).to_frame(name='std_rf').reset_index()

    result_rw = rwork_mean_by_dataset.merge(std_rwork_by_dataset)
    result_rf = rfree_mean_by_dataset.merge(std_rfree_by_dataset)
    final_result = result_rw.merge(result_rf)

    return HttpResponse(final_result.to_json(), content_type="application/json")
