from typing import Iterator
from django.shortcuts import render
from django.http import HttpResponse
from fragview.projects import current_project
from fragview.projects import Project
from fragview.forms import ProcessForm, RefineForm, LigfitForm
from fragview.tools import (
    ProcessOptions,
    RefineOptions,
    LigfitOptions,
    generate_process_batch,
    generate_refine_batch,
    generate_ligfit_batch,
)
from fragview.scraper import get_result_mtz
from fragview.views.wrap import DatasetInfo
from fragview.sites.current import get_hpc_runner
from fragview.views.utils import get_crystals_fragment
from fragview.views.update_jobs import add_update_job
from jobs.client import JobsSet


def _get_dataset_info(project: Project) -> Iterator[DatasetInfo]:
    for dataset in project.get_datasets():
        yield DatasetInfo(dataset)


def show_all(request):
    project = current_project(request)

    return render(
        request,
        "datasets.html",
        {
            "datasets": _get_dataset_info(project),
        },
    )


def process(request):
    project = current_project(request)

    form = ProcessForm(project, request.body)
    options = ProcessOptions(form.space_group, form.cell_params)

    jobs = JobsSet(project, "process datasets")
    hpc = get_hpc_runner()

    for tool, custom_params in form.tools:
        for dataset in form.datasets:
            options.custom_args = custom_params
            batch = generate_process_batch(tool, project, dataset, options)
            batch.save()
            jobs.add_job(batch)

            add_update_job(jobs, hpc, project, tool.get_name(), dataset, batch)

    jobs.submit()

    return HttpResponse("ok")


def refine(request):
    project = current_project(request)

    form = RefineForm(project, request.body)
    options = RefineOptions(form.pdb_file)

    jobs = JobsSet(project, "refine structures")
    hpc = get_hpc_runner()

    for proc_result in form.datasets:
        dataset = proc_result.result.dataset
        mtz = get_result_mtz(project, proc_result)
        proc_tool = proc_result.result.tool

        for tool, custom_params in form.tools:
            options.custom_args = custom_params
            batch = generate_refine_batch(
                tool, project, dataset, proc_tool, mtz, options
            )
            batch.save()

            jobs.add_job(batch)
            add_update_job(jobs, hpc, project, tool.get_name(), dataset, batch)

    jobs.submit()

    return HttpResponse("ok")


def ligfit(request):
    project = current_project(request)

    form = LigfitForm(project, request.body)
    options = LigfitOptions(form.restrains_tool)
    jobs = JobsSet(project, "fit ligands")
    hpc = get_hpc_runner()

    for ref_res in form.datasets:
        result_dir = project.get_refine_result_dir(ref_res)
        dataset = ref_res.dataset
        fragment = get_crystals_fragment(dataset.crystal)

        for pipeline, _ in form.tools:
            batch = generate_ligfit_batch(
                project,
                pipeline,
                dataset,
                fragment,
                ref_res.process_tool,
                ref_res.refine_tool,
                result_dir,
                options,
            )
            batch.save()

            jobs.add_job(batch)
            add_update_job(jobs, hpc, project, pipeline.get_name(), dataset, batch)

    jobs.submit()

    return HttpResponse("ok")
