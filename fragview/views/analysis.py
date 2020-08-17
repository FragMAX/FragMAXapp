from django.shortcuts import render
from fragview.models import PDB
from fragview.projects import current_project
from fragview.sites import SITE
from glob import glob
from fragview.projects import project_datasets


def processing_form(request):
    proj = current_project(request)

    datasets = sorted(project_datasets(proj), key=lambda x: ("Apo" in x, x))

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
            "methods": methods,
            "pipelines": SITE.get_supported_pipelines(),
        },
    )
