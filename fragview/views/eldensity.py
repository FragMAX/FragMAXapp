from pathlib import Path
from fragview.views.utils import download_http_response, get_refine_result_by_id
from fragview.projects import current_project


def _density_filename(name, type):
    if type == "nat":
        return f"{name}_2mFo-DFc.ccp4"
    elif type == "mtz":
        return f"{name}.mtz"
    assert type == "dif"
    return f"{name}_mFo-DFc.ccp4"


def refined_map(request, result_id, type):
    project = current_project(request)
    result = get_refine_result_by_id(project, result_id)
    mtz_path = Path(
        project.get_refine_result_dir(result), _density_filename("final", type)
    )

    return download_http_response(mtz_path, f"{result.name}{mtz_path.suffix}")


def pandda_consensus_zmap(request, dataset, method):
    project = current_project(request)

    zmap_path = Path(
        project.pandda_processed_dataset_dir(method, dataset),
        f"{dataset}-z_map.native.ccp4",
    )

    return download_http_response(zmap_path)


def pandda_bdc(request, dataset, method):
    project = current_project(request)

    dataset_dir = project.pandda_processed_dataset_dir(method, dataset)

    # pick one of the matching .ccp4 files,
    # TODO: this gives us random ccp4 file of any
    # TODO: potentional BDC files, is this a good way to roll?
    ccp4_path = next(dataset_dir.glob("*BDC*.ccp4"))

    return download_http_response(ccp4_path)


def pandda_average(request, dataset, method):
    project = current_project(request)

    zmap_path = Path(
        project.pandda_processed_dataset_dir(method, dataset),
        f"{dataset}-ground-state-average-map.native.ccp4",
    )

    return download_http_response(zmap_path)


def pandda_input(request, dataset, method):
    project = current_project(request)

    processed_dir = project.pandda_processed_dataset_dir(method, dataset)
    mtz_path = next(processed_dir.glob("*pandda-input.mtz"))

    return download_http_response(mtz_path)
