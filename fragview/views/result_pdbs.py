from os import path
from pathlib import Path
from fragview.projects import (
    current_project,
    project_results_dir,
    project_pandda_processed_dataset_dir,
)
from fragview.views.utils import (
    download_http_response,
    get_refine_result_by_id,
    get_ligfit_result_by_id,
)


def _refine_dir(proj, dataset, process, refine):
    return path.join(project_results_dir(proj), dataset, process, refine)


def refined(request, result_id):
    project = current_project(request)
    result = get_refine_result_by_id(project, result_id)
    pdb_path = Path(project.get_refine_result_dir(result), "final.pdb")

    return download_http_response(pdb_path, f"{result.name}.pdb")


def final(request, dataset, process, refine):
    proj = current_project(request)
    pdb_path = path.join(_refine_dir(proj, dataset, process, refine), "final.pdb")

    return download_http_response(pdb_path)


def ligand(request, result_id):
    """
    view for fetching ligand PDBs generated by the ligand fitting tools

    'fitting' is either 'ligfit' or 'rhofit', for the respective tool
    """
    project = current_project(request)

    result = get_ligfit_result_by_id(project, result_id)
    tool = result.result.tool
    refine_dir = project.get_refine_result_dir(result.result.input.refine_result)

    if tool == "ligandfit":
        pdb_path = Path(refine_dir, "ligfit", "LigandFit_run_1_", "ligand_fit_1_1.pdb")
    elif tool == "rhofit":
        pdb_path = Path(refine_dir, "rhofit", "best.pdb")
    else:
        assert False, f"unexpected ligand fitting tool {tool}"

    return download_http_response(pdb_path)


def pandda_fitted(request, dataset, method):
    proj = current_project(request)

    modelled_structures_dir = Path(
        project_pandda_processed_dataset_dir(proj, method, dataset),
        "modelled_structures",
    )

    #
    # pick 'fitted-vNNNN.pdb' file, with highest NNNN number
    #
    pdb_path = max(modelled_structures_dir.glob("*fitted*.pdb"))

    return download_http_response(pdb_path)


def pandda_input(request, dataset, method):
    project = current_project(request)

    processed_dir = project.pandda_processed_dataset_dir(method, dataset)
    pdb_path = next(processed_dir.glob("*pandda-input.pdb"))

    return download_http_response(pdb_path)
