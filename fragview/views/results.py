import pandas
from typing import Iterator, Dict, List
from django.http import HttpResponse
from django.shortcuts import render
from fragview.projects import current_project, Project
from fragview.views.wrap import RefineInfo, wrap_refine_results


def _get_refine_info(project: Project) -> Iterator[RefineInfo]:
    for res in project.get_refine_results():
        yield RefineInfo(res)


def show(request):
    project = current_project(request)
    return render(
        request,
        "fragview/results.html",
        {"refine_results": wrap_refine_results(project.get_refine_results())},
    )


def _get_results_data(project, columns: List[str]) -> pandas.DataFrame:
    """
    put refine result statistics data into a pandas data frame

    'columns' specifies the RefineResult attribute names to include into the data frame

    The dataframe will also include refine result's symbolic name column 'dset_tools'
    and dataset's symbolic name column 'dataset'.

    For example, if 'r_work' and 'r_free' attributes are requested, the data frame will look like:

        r_work   r_free               dset_tools  dataset
    0  0.14723  0.16015      Apo01_1_edna_dimple  Apo01_1
    1  0.15019  0.16336  Apo01_1_autoproc_dimple  Apo01_1
    2  0.15636  0.17151      Apo27_1_edna_dimple  Apo27_1
    3  0.17733  0.19371  Apo27_1_autoproc_dimple  Apo27_1
    4  0.15231  0.16726      B08a2_1_edna_dimple  B08a2_1
    5  0.15676  0.17284  B08a2_1_autoproc_dimple  B08a2_1
    """
    names = []
    datasets = []
    vals: Dict[str, List] = {col_name: [] for col_name in columns}

    for ref_res in project.get_refine_results():
        names.append(ref_res.name)
        datasets.append(ref_res.dataset.name)
        for col_name in columns:
            vals[col_name].append(getattr(ref_res, col_name))

    data = {col_name: vals[col_name] for col_name in columns}
    data["dset_tools"] = names
    data["dataset"] = datasets

    return pandas.DataFrame(data)


def isa(request):
    """
    return ISa statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    data = _get_results_data(current_project(request), ["isa"])

    # group data by dataset name and calculate mean and standard error
    isa_mean_by_dataset = (
        data.groupby("dataset")["isa"].mean().to_frame(name="mean").reset_index()
    )
    isa_mean_by_dataset["mean"] = isa_mean_by_dataset["mean"].round(2)
    std_err_by_dataset = (
        data.groupby("dataset")["isa"].std().round(2).to_frame(name="std").reset_index()
    )

    result = isa_mean_by_dataset.merge(std_err_by_dataset)

    return HttpResponse(result.to_json(), content_type="application/json")


def resolution(request):
    """
    return resolution statistics for datasets in the results,
    in Json format, suitable for drawing interactive plots
    """
    data = _get_results_data(current_project(request), ["resolution"])

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
    r_factors = ["r_work", "r_free"]
    data = _get_results_data(current_project(request), r_factors)

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

    # rename the database column names to shorter unit cell value names,
    # for a nice UIs sake
    columns_map = {
        "unit_cell_a": "a",
        "unit_cell_b": "b",
        "unit_cell_c": "c",
        "unit_cell_alpha": "alpha",
        "unit_cell_beta": "beta",
        "unit_cell_gamma": "gamma",
    }

    data = _get_results_data(current_project(request), list(columns_map.keys()))
    data.rename(columns=columns_map, inplace=True)

    params_mean_values = []
    for param in columns_map.values():
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
