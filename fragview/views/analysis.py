from glob import glob

from django.shortcuts import render
from fragview.projects import current_project, project_raw_master_h5_files


def processing_form(request):
    proj = current_project(request)

    models = [
        x.split("/")[-1].split(".pdb")[0]
        for x in glob(proj.data_path() + "/fragmax/models/*.pdb")
    ]

    datasets = sorted(
        [
            x.split("/")[-1].replace("_master.h5", "")
            for x in project_raw_master_h5_files(proj)
            if "ref-" not in x
        ],
        key=lambda x: ("Apo" in x, x))

    return render(
        request,
        "fragview/data_analysis.html",
        {"models": models, "datasets": datasets})
