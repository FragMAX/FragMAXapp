from django.http import HttpResponse
from fragview.projects import project_update_status_script, get_update_results_command, parse_dataset_name
from fragview.fileio import read_proj_file


def scrsplit(a, n):
    k, m = divmod(len(a), n)
    lst = (a[i * k + min(i, m): (i + 1) * k + min(i + 1, m)] for i in range(n))
    return [x for x in lst if x]


def binary_http_response(proj, file_path, content_type):
    return HttpResponse(read_proj_file(proj, file_path), content_type=content_type)


def jpeg_http_response(proj, file_path):
    return binary_http_response(proj, file_path, "image/jpeg")


def png_http_response(proj, file_path):
    return binary_http_response(proj, file_path, "image/png")


def download_http_response(proj, file_path):
    return binary_http_response(proj, file_path, "application/octet-stream")


def add_update_status_script_cmds(project, sample, batch, modules):
    dataset, run = parse_dataset_name(sample)

    batch.load_python_env()
    batch.add_command(
        f"python3 {project_update_status_script(project)} {project.data_path()} {dataset} {run}"
    )

    batch.purge_modules()
    batch.load_modules(modules)


def add_update_results_script_cmds(project, sample, batch, modules):
    dataset, run = parse_dataset_name(sample)

    batch.load_python_env()
    batch.add_command(get_update_results_command(project, dataset, run))

    batch.purge_modules()
    batch.load_modules(modules)
