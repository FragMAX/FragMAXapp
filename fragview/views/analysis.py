from django.shortcuts import render
from fragview.models import PDB
from fragview.projects import current_project, project_raw_master_h5_files
from glob import glob


def processing_form(request):
    proj = current_project(request)

    datasets = sorted(
        [
            x.split("/")[-1].replace("_master.h5", "")
            for x in project_raw_master_h5_files(proj)
            if "ref-" not in x
        ],
        key=lambda x: ("Apo" in x, x),
    )
    methods = [
        x.split("/")[10]
        for x in glob(
            f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/*/pandda/analyses/*inspect_events*"
        )
    ]
    return render(
        request,
        "fragview/data_analysis.html",
        {
            "datasets": datasets,
            "pdbs": PDB.project_pdbs(proj),
            "methods": methods
        })
