import pandas
import csv
from typing import Dict, Union
from pathlib import Path
from django.http import HttpResponse
from django.shortcuts import render
from fragview.projects import current_project, project_results_file


NUMERICAL_COLUMNS = [
    "resolution",
    "ISa",
    "r_work",
    "r_free",
    "bonds",
    "angles",
    "a",
    "b",
    "c",
    "alpha",
    "beta",
    "gamma",
    "rhofitscore",
    "ligfitscore",
]


def _load_results(results_file: Path):
    def _as_float(row: Dict, name: str):
        """
        convert specified cell into float value,
        for cases when value is 'unknown' or not specified,
        return None
        """
        val = row[name]
        if val in {"unknown", ""}:
            return None

        return float(val)

    if results_file is None:
        return []

    results_data = []
    with results_file.open() as readFile:
        for row in csv.DictReader(readFile):
            # convert all numerical values to floats,
            # so that the template can render them with
            # desired number of decimals
            for col_name in NUMERICAL_COLUMNS:
                row[col_name] = _as_float(row, col_name)

            results_data.append(row)

    return results_data


def _get_results_file(request) -> Union[None, Path]:
    proj = current_project(request)
    results_file = Path(project_results_file(proj))

    if not results_file.is_file():
        return None

    return results_file


def _load_results_data(request):
    """
    load results CSV in pandas suitable format

    return None if results.csv does not exists or is empty
    """
    results_file = _get_results_file(request)
    if results_file is None:
        return None

    data = pandas.read_csv(results_file)
    if data.empty:
        return None

    return data


def show(request):
    return render(
        request,
        "fragview/results.html",
        {"results": _load_results(_get_results_file(request))},
    )


def isa(request):
    """
    return ISa statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    data = _load_results_data(request)
    if data is None:
        return HttpResponse("")

    # ignore data row when isa is unknown
    data = data[data["ISa"] != "unknown"]
    data["ISa"] = pandas.to_numeric(data["ISa"])

    # group data by dataset name and calculate mean and standard error
    isa_mean_by_dataset = (
        data.groupby("dataset")["ISa"].mean().to_frame(name="mean").reset_index()
    )
    isa_mean_by_dataset["mean"] = isa_mean_by_dataset["mean"].round(2)
    std_err_by_dataset = (
        data.groupby("dataset")["ISa"].std().round(2).to_frame(name="std").reset_index()
    )

    result = isa_mean_by_dataset.merge(std_err_by_dataset)

    return HttpResponse(result.to_json(), content_type="application/json")


def resolution(request):
    """
    return resolution statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    data = _load_results_data(request)
    if data is None:
        return HttpResponse("")

    data["resolution"] = pandas.to_numeric(data["resolution"])
    # group data by dataset name and calculate mean and standard error
    res_mean_by_dataset = (
        data.groupby("dataset")["resolution"].mean().to_frame(name="mean").reset_index()
    )
    res_mean_by_dataset["mean"] = res_mean_by_dataset["mean"].round(2)
    res_std_err_by_dataset = (
        data.groupby("dataset")["resolution"]
        .std()
        .round(2)
        .to_frame(name="std")
        .reset_index()
    )

    result = res_mean_by_dataset.merge(res_std_err_by_dataset)

    return HttpResponse(result.to_json(), content_type="application/json")


def rfactor(request):
    """
    return rfactors statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    data = _load_results_data(request)
    if data is None:
        return HttpResponse("")

    r_factors = ["r_work", "r_free"]
    r_factors_values = []
    for r_factor in r_factors:
        data[r_factor] = pandas.to_numeric(data[r_factor])
        mean_by_dataset = (
            data.groupby("dataset")[r_factor]
            .mean()
            .round(2)
            .to_frame(name=r_factor)
            .reset_index()
        )
        r_factors_values.append(mean_by_dataset)
        std_err_by_dataset = (
            data.groupby("dataset")[r_factor]
            .std()
            .round(2)
            .to_frame(name="std_" + r_factor)
            .reset_index()
        )
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
    data = _load_results_data(request)
    if data is None:
        return HttpResponse("")

    params = ["a", "b", "c", "alpha", "beta", "gamma"]
    params_mean_values = []
    for param in params:
        data[param] = pandas.to_numeric(data[param])
        mean_by_dataset = (
            data.groupby("dataset")[param]
            .mean()
            .round(3)
            .to_frame(name=param)
            .reset_index()
        )
        params_mean_values.append(mean_by_dataset)

    result = params_mean_values[0]
    for i in range(len(params_mean_values) - 1):
        result = result.merge(params_mean_values[i + 1])

    return HttpResponse(result.to_json(), content_type="application/json")
