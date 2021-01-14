from os import path
from fragview.fileio import read_proj_file
from django.http import HttpResponse, HttpResponseNotFound
from fragview.projects import current_project, project_results_dir


def _binary_http_response(proj, pdb_path):
    return HttpResponse(
        read_proj_file(proj, pdb_path), content_type="application/octet-stream"
    )


def _refine_dir(proj, dataset, process, refine):
    return path.join(project_results_dir(proj), dataset, process, refine)


def final(request, dataset, process, refine):
    proj = current_project(request)
    pdb_path = path.join(_refine_dir(proj, dataset, process, refine), "final.pdb")

    return _binary_http_response(proj, pdb_path)


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

    return _binary_http_response(proj, pdb_path)
