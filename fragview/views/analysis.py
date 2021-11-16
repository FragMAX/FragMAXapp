from django.shortcuts import render
from fragview.sites import SITE
from fragview.projects import current_project
from fragview.space_groups import by_system


def processing_form(request):
    project = current_project(request)
    default_ligand_tool, ligand_tools = SITE.get_supported_ligand_tools()

    datasets = sorted(project.get_datasets(), key=lambda d: d.name)

    return render(
        request,
        "fragview/data_analysis.html",
        {
            "pipelines": SITE.get_supported_pipelines(),
            "datasets": datasets,
            "default_ligand_tool": default_ligand_tool,
            "ligand_tools": ligand_tools,
            "space_group_systems": by_system(),
        },
    )
