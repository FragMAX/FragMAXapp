from os import path
from django.shortcuts import redirect
from fragview.projects import current_project, project_static_url, project_results_dir
from worker.ccp4 import mtz_to_map


def map(request, dataset, process, refine, type):
    """
    generates CCP4 map from MTZ data
    """
    proj = current_project(request)

    mtz_path = path.join(project_results_dir(proj), dataset, process, refine)
    # start generation task and wait for it to complete
    mtz_to_map.delay(mtz_path).wait()

    # redirect to the generated CCP4 file
    ccp4_filename = "final_2mFo-DFc.ccp4" if type == "nat" else "final_mFo-DFc.ccp4"
    redirect_url = path.join(project_static_url(proj), "fragmax", "results", dataset, process, refine, ccp4_filename)

    return redirect(redirect_url)
