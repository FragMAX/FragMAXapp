from os import path
from threading import Thread
from django.http import HttpResponse, FileResponse
from fragview.fileio import read_proj_file


def start_thread(func, *func_args):
    Thread(target=func, args=func_args, daemon=True).start()


def scrsplit(a, n):
    k, m = divmod(len(a), n)
    lst = (a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n))
    return [x for x in lst if x]


def binary_http_response(proj, file_path, content_type):
    return HttpResponse(read_proj_file(proj, file_path), content_type=content_type)


def jpeg_http_response(proj, file_path):
    return binary_http_response(proj, file_path, "image/jpeg")


def png_http_response(proj, file_path):
    return binary_http_response(proj, file_path, "image/png")


def download_http_response(file_path):
    return FileResponse(
        open(file_path, "rb"), as_attachment=True, filename=path.basename(file_path)
    )
