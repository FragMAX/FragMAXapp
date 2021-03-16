from os import path
from pathlib import Path
from django.http import HttpResponseNotFound
from fragview.projects import (
    current_project,
    project_results_dir,
    project_pandda_processed_dataset_dir,
)
from fragview.views.utils import download_http_response


def _refine_dir(proj, dataset, process, refine):
    return path.join(project_results_dir(proj), dataset, process, refine)


def final(request, dataset, process, refine):
    proj = current_project(request)
    pdb_path = path.join(_refine_dir(proj, dataset, process, refine), "final.pdb")

    return download_http_response(proj, pdb_path)


def ligand(request, dataset, process, refine, fitting):
    """
    view for fetching ligand PDBs generated by the ligand fitting tools

    'fitting' is either 'ligfit' or 'rhofit', for the respective tool
    """
    proj = current_project(request)

    refine_dir = _refine_dir(proj, dataset, process, refine)

    if fitting == "ligfit":
        pdb_path = path.join(
            refine_dir, "ligfit", "LigandFit_run_1_", "ligand_fit_1_1.pdb"
        )
    elif fitting == "rhofit":
        pdb_path = path.join(refine_dir, "rhofit", "best.pdb")
    else:
        return HttpResponseNotFound(f"unknown ligand fitting tool '{fitting}'")

    if not path.isfile(pdb_path):
        return HttpResponseNotFound(f"no '{fitting}' PDB file found")

    return download_http_response(proj, pdb_path)


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

    return download_http_response(proj, pdb_path)
