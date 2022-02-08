from typing import Iterator
from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from fragview.projects import current_project
from fragview.projects import Project
from fragview.forms import ProcessForm, RefineForm
from fragview.tools import (
    ProcessOptions,
    RefineOptions,
    generate_process_batch,
    generate_refine_batch,
)
from fragview.scraper import get_result_mtz
from fragview.views.wrap import DatasetInfo
from fragview.sites.current import get_hpc_runner
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
    form = ProcessForm(project, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    options = ProcessOptions(form.get_space_group(), form.get_cell_parameters())

    jobs = JobsSet("process datasets")
    hpc = get_hpc_runner()

    for pipeline in form.get_pipelines():
        for dataset in form.get_datasets():
            batch = generate_process_batch(pipeline, project, dataset, options)
            batch.save()
            jobs.add_job(batch)

            add_update_job(jobs, hpc, project, pipeline.get_name(), dataset, batch)

    jobs.submit()

    return HttpResponse("ok")


def refine(request):
    project = current_project(request)
    form = RefineForm(project, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    options = RefineOptions(form.pdb_file)

    jobs = JobsSet("process datasets")
    hpc = get_hpc_runner()

    for proc_result in form.get_process_results():
        dataset = proc_result.result.dataset
        mtz = get_result_mtz(project, proc_result)
        proc_tool = proc_result.result.tool

        for pipeline in form.get_pipelines():
            batch = generate_refine_batch(
                pipeline, project, dataset, proc_tool, mtz, options
            )
            batch.save()

            jobs.add_job(batch)
            add_update_job(jobs, hpc, project, pipeline.get_name(), dataset, batch)

    jobs.submit()

    return HttpResponse("ok")
