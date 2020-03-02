import re
from os import path
from django.shortcuts import redirect
from fragview.projects import current_project, project_static_url, project_results_dir, project_process_protein_dir
from worker.ccp4 import mtz_to_map


def _ccp4_filename(name, type):
    if type == "nat":
        return f"{name}_2mFo-DFc.ccp4"

    assert type == "dif"
    return f"{name}_mFo-DFc.ccp4"


def map(request, dataset, process, refine, type):
    """
    generates CCP4 map from MTZ data
    """
    proj = current_project(request)

    mtz_path = path.join(project_results_dir(proj), dataset, process, refine)
    # start generation task and wait for it to complete
    mtz_to_map.delay(mtz_path, "final.mtz").wait()

    # redirect to the generated CCP4 file
    redirect_url = path.join(project_static_url(proj), "fragmax", "results", dataset,
                             process, refine, _ccp4_filename("final", type))

    return redirect(redirect_url)


def pipedream_map(request, sample, process, type):
    """
    generates CCP4 map from MTZ data using pipedream file layouts
    """
    proj = current_project(request)

    re_pattern = f"{proj.protein}-{proj.library}-([a-zA-Z0-9]*)_([0-9]*)"
    ligand, run = re.match(re_pattern, sample).groups()

    mtz_dir = path.join(f"{proj.protein}-{proj.library}-{ligand}", sample, "pipedream", f"{process}-{ligand}")

    mtz_path = path.join(project_process_protein_dir(proj), mtz_dir)

    # start generation task and wait for it to complete
    mtz_to_map.delay(mtz_path, "refine.mtz").wait()

    redirect_url = path.join(project_static_url(proj), "fragmax", "process", proj.protein, mtz_dir,
                             _ccp4_filename("refine", type))

    return redirect(redirect_url)
