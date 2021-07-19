from typing import Iterator
from django.shortcuts import render
from fragview.projects import current_project
from fragview.projects import Project
from fragview.views.wrap import DatasetInfo


def _get_dataset_info(project: Project) -> Iterator[DatasetInfo]:
    for dataset in project.get_datasets():
        yield DatasetInfo(dataset)


def show_all(request):
    project = current_project(request)

    return render(
        request, "fragview/datasets.html", {"datasets": _get_dataset_info(project),},
    )
