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
    results_file = project_results_file(proj)

    data = pandas.read_csv(results_file)

    if data.empty:
        return HttpResponse('')
    else:
        # ignore data row when isa is unknown
        data = data[data["ISa"] != "unknown"]
        data["ISa"] = pandas.to_numeric(data["ISa"])

        # group data by dataset name and calculate mean and standard error
        isa_mean_by_dataset = data.groupby("dataset")["ISa"].mean()\
            .to_frame(name="mean").reset_index()
        isa_mean_by_dataset["mean"] = isa_mean_by_dataset["mean"].round(2)
        std_err_by_dataset = data.groupby("dataset")["ISa"].std().round(2)\
            .to_frame(name="std").reset_index()

        result = isa_mean_by_dataset.merge(std_err_by_dataset)

        return HttpResponse(result.to_json(), content_type="application/json")


def resolution(request):
    """
    return resolution statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    proj = current_project(request)
    results_file = project_results_file(proj)

    data = pandas.read_csv(results_file)

    if data.empty:
        return HttpResponse('')
    else:
        data["resolution"] = pandas.to_numeric(data["resolution"])
        # group data by dataset name and calculate mean and standard error
        res_mean_by_dataset = data.groupby("dataset")["resolution"].mean()\
            .to_frame(name="mean").reset_index()
        res_mean_by_dataset["mean"] = res_mean_by_dataset["mean"].round(2)
        res_std_err_by_dataset = data.groupby("dataset")["resolution"].std()\
            .round(2).to_frame(name="std").reset_index()

        result = res_mean_by_dataset.merge(res_std_err_by_dataset)

        return HttpResponse(result.to_json(), content_type="application/json")


def rfactor(request):
    """
    return rfactors statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    proj = current_project(request)
    results_file = project_results_file(proj)

    data = pandas.read_csv(results_file)

    if data.empty:
        return HttpResponse('')
    else:
        r_factors = ["r_work", "r_free"]
        r_factors_values = []
        for r_factor in r_factors:
            data[r_factor] = pandas.to_numeric(data[r_factor])
            mean_by_dataset = data.groupby('dataset')[r_factor].mean()\
                .round(2).to_frame(name=r_factor).reset_index()
            r_factors_values.append(mean_by_dataset)
            std_err_by_dataset = data.groupby('dataset')[r_factor].std()\
                .round(2).to_frame(name="std_" + r_factor).reset_index()
            r_factors_values.append(std_err_by_dataset)

        result = r_factors_values[0]
        for i in range(len(r_factors_values) - 1):
            result = result.merge(r_factors_values[i + 1])

        return HttpResponse(result.to_json(), content_type="application/json")


def cellparams(request):
    """
    return cell parameters statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    proj = current_project(request)
    results_file = project_results_file(proj)

    data = pandas.read_csv(results_file)

    if data.empty:
        return HttpResponse('')
    else:
        params = ["a", "b", "c", "alpha", "beta", "gamma"]
        params_mean_values = []
        for param in params:
            data[param] = pandas.to_numeric(data[param])
            mean_by_dataset = data.groupby('dataset')[param].mean()\
                .round(3).to_frame(name=param).reset_index()
            params_mean_values.append(mean_by_dataset)

        result = params_mean_values[0]
        for i in range(len(params_mean_values) - 1):
            result = result.merge(params_mean_values[i + 1])

        return HttpResponse(result.to_json(), content_type="application/json")
