from os import path
from worker.dials import get_rlp
from django.shortcuts import render, redirect
from fragview.projects import current_project, project_process_protein_dir, project_static_url


def show(request, sample, run):
    return render(request, "fragview/reciprocal_lattice.html", {"sample": sample, "run": run})


def rlp(request, sample, run):
    proj = current_project(request)

    idx_path = path.join(f"{sample}", f"{sample}_{run}", "dials", "DEFAULT", "NATIVE", "SWEEP1", "index")
    dials_dir = path.join(project_process_protein_dir(proj), idx_path)
    if not path.exists(dials_dir):
        idx_path = path.join(f"{sample}", f"{sample}_{run}", "dials", "DEFAULT", "SAD", "SWEEP1", "index")
        dials_dir = path.join(project_process_protein_dir(proj), idx_path)

    # create rlp.json, if needed
    get_rlp.delay(dials_dir).wait()

    # redirect to the generated json file
    redirect_url = path.join(project_static_url(proj), "fragmax", "process", proj.protein, idx_path, "rlp.json")

    return redirect(redirect_url)
