from typing import List, Iterator
from django.shortcuts import render
from fragview.projects import current_project, Project
from fragview.views.wrap import (
    DatasetInfo,
    ProcessingInfo,
    wrap_pdbs,
    wrap_refine_results,
)
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


def _get_processed_datasets(project: Project) -> List[ProcessingInfo]:
    def _sort_key(proc_res):
        # sort by crystal id, run number, tool name and space group
        return (
            proc_res.crystal.id,
            proc_res.dataset.run,
            proc_res.tool_name(),
            proc_res.space_group.short_name(),
        )

    def _get_proc_datasets():
        for dataset in project.get_datasets():
            for proc_res in project.get_datasets_process_results(dataset):
                yield ProcessingInfo(proc_res)

    return sorted(_get_proc_datasets(), key=_sort_key)


def refine(request):
    project = current_project(request)

    return render(
        request,
        "analysis_refine.html",
        {
            "proc_results": _get_processed_datasets(project),
            "pipelines": get_supported_pipelines(),
            "pdbs": wrap_pdbs(project.get_pdbs()),
        },
    )


def ligfit(request):
    project = current_project(request)
    default_ligand_tool, ligand_tools = get_supported_ligand_tools()

    refine_results = list(wrap_refine_results(project.get_refine_results()))

    return render(
        request,
        "analysis_ligfit.html",
        {
            "refine_results": list(refine_results),
            "pipelines": get_supported_pipelines(),
            "default_ligand_tool": default_ligand_tool,
            "ligand_tools": ligand_tools,
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
