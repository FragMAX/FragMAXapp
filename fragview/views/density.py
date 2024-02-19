from os import path
from glob import glob
from pathlib import Path
from django.shortcuts import render
from fragview.projects import current_project
from fragview.views.utils import get_refine_result_by_id, get_crystals_fragment


def show(request, result_id):
    project = current_project(request)
    result = get_refine_result_by_id(project, result_id)

    return render(
        request,
        "density.html",
        {
            "result": result,
            "rhofit_result": result.get_ligfit_result("rhofit"),
            "ligandfit_result": result.get_ligfit_result("ligandfit"),
            "fragment": get_crystals_fragment(result.dataset.crystal),
            "previous_result": result.previous(),
            "next_result": result.next(),
        },
    )


def compare_poses(request, result_id):
    project = current_project(request)
    result = get_refine_result_by_id(project, result_id)

    return render(
        request,
        "dual_density.html",
        {
            "result": result,
            "rhofit_result": result.get_ligfit_result("rhofit"),
            "ligandfit_result": result.get_ligfit_result("ligandfit"),
            "fragment": get_crystals_fragment(result.dataset.crystal),
        },
    )


def find_refinement_log(proj_dir, res_dir):
    logFile = "refinelog"
    pipelineLog = "pipelinelong"

    if "dimple" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/*refmac*log"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = "/".join(logFile.split("/")[:-1]) + "/dimple.log"

    if "fspipeline" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/*/*-*log"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = path.join(
                path.dirname(path.dirname(logFile)), "fspipeline.log"
            )

    if "buster" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/*BUSTER/Cycle*/*html"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = logSearch[-1]

    return Path(logFile).relative_to(proj_dir), Path(pipelineLog).relative_to(proj_dir)


def find_ligandfitting_log(proj_dir, res_dir):
    rhofitSearch = glob(f"{res_dir}/rhofit/results.txt")
    if rhofitSearch:
        rhofitlog = Path(rhofitSearch[0]).relative_to(proj_dir)
    else:
        rhofitlog = ""

    ligandfitSearch = glob(f"{res_dir}/ligfit/LigandFit_run*/ligand_*.log")
    if ligandfitSearch:
        ligandfitlog = Path(ligandfitSearch[0]).relative_to(proj_dir)
    else:
        ligandfitlog = ""

    return rhofitlog, ligandfitlog
