from django.shortcuts import render
from fragview.models import PDB
from fragview.projects import current_project, project_raw_master_h5_files, project_raw_master_cbf_files
from glob import glob
from os import path


def processing_form(request):
    proj = current_project(request)

    datasets = sorted(
        [
            path.basename(x).split("_")[0]
            for x in project_raw_master_cbf_files(proj)
        ],
        key=lambda x: ("Apo" in x, x))
    methods = [
        x.split("/")[10]
        for x in glob(f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/*/pandda/analyses/*inspect_events*")
    ]
    return render(
        request,
        "fragview/data_analysis.html",
        {
            "datasets": datasets,
            "pdbs": PDB.project_pdbs(proj),
            "methods": methods
        })
