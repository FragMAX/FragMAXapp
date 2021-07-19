from django.shortcuts import render
from fragview.sites import SITE


def processing_form(request):
    default_ligand_tool, ligand_tools = SITE.get_supported_ligand_tools()

    return render(
        request,
        "fragview/data_analysis.html",
        {
            "pipelines": SITE.get_supported_pipelines(),
            "default_ligand_tool": default_ligand_tool,
            "ligand_tools": ligand_tools,
        },
    )
