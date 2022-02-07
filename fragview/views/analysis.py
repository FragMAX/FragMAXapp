from typing import Iterator
from django.shortcuts import render
from fragview.projects import current_project, Project
from fragview.views.wrap import DatasetInfo, ProcessingInfo, wrap_pdbs
from fragview.space_groups import by_system
from fragview.sites.current import get_supported_pipelines, get_supported_ligand_tools


def processing_form(request):
    project = current_project(request)
    default_ligand_tool, ligand_tools = get_supported_ligand_tools()

    datasets = sorted(project.get_datasets(), key=lambda d: d.name)

    return render(
        request,
        "data_analysis.html",
        {
            "pipelines": get_supported_pipelines(),
            "datasets": datasets,
            "default_ligand_tool": default_ligand_tool,
            "ligand_tools": ligand_tools,
            "space_group_systems": by_system(),
        },
    )


# TODO: this is a copy'n'paste from datasets.py !!!
def _get_dataset_info(project: Project) -> Iterator[DatasetInfo]:
    for dataset in sorted(project.get_datasets(), key=lambda d: d.name):
        yield DatasetInfo(dataset)


def process(request):
    project = current_project(request)

    return render(
        request,
        "analysis_process.html",
        {
            "datasets": list(_get_dataset_info(project)),
            "pipelines": get_supported_pipelines(),
            "space_group_systems": list(by_system()),
        },
    )


def _get_processed_datasets(project: Project) -> Iterator[ProcessingInfo]:
    for dataset in project.get_datasets():
        for proc_res in project.get_datasets_process_results(dataset):
            yield ProcessingInfo(proc_res)


def refine(request):
    project = current_project(request)
    default_ligand_tool, ligand_tools = get_supported_ligand_tools()

    return render(
        request,
        "analysis_refine.html",
        {
            "proc_results": list(_get_processed_datasets(project)),
            "pipelines": get_supported_pipelines(),
            "default_ligand_tool": default_ligand_tool,
            "ligand_tools": ligand_tools,
            "pdbs": wrap_pdbs(project.get_pdbs()),
        },
    )


def pandda(request):
    default_ligand_tool, ligand_tools = get_supported_ligand_tools()

    return render(
        request,
        "analysis_pandda.html",
        {
            "pipelines": get_supported_pipelines(),
            "default_ligand_tool": default_ligand_tool,
            "ligand_tools": ligand_tools,
        },
    )
