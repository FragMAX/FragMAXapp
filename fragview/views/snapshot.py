from django.http import HttpResponseNotFound
from fragview.projects import current_project
from fragview.views.utils import jpeg_http_response


def show(request, dataset_id, snapshot_index):
    project = current_project(request)

    snapshot = project.get_dataset_snapshot(dataset_id, snapshot_index)
    if snapshot is None:
        return HttpResponseNotFound(
            f"no snapshot '{snapshot_index}' for dataset '{dataset_id}' found"
        )

    snapshot_path = project.get_dataset_snapshot_path(snapshot)
    return jpeg_http_response(project, snapshot_path)
