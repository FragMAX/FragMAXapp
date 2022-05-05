from django.shortcuts import render
from fragview import models
from fragview.forms import LibraryImportForm
from fragview.fraglibs import create_db_library, LibraryAlreadyExist
from fragview.projects import current_project, Project
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseBadRequest,
)


def show(request):
    project = current_project(request)
    return render(
        request, "libraries.html", {"libraries": models.Library.get_all(project)}
    )


def new(request):
    return render(request, "libraries_new.html")


def import_new(request):
    if request.method != "POST":
        return HttpResponseBadRequest("expected POST request")

    form = LibraryImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.get_error_message())

    name, frags = form.get_library()

    try:
        create_db_library(current_project(request), name, frags)
    except LibraryAlreadyExist as e:
        return HttpResponseBadRequest(f"{e}")

    return HttpResponse("ok")


def _get_library(project: Project, library_id: str):
    try:
        return models.Library.get_by_id(project, library_id), None
    except models.Library.DoesNotExist:
        return (
            None,
            HttpResponseNotFound(f"fragment library with id '{library_id}' not found"),
        )


def as_json(request, library_id: str) -> HttpResponse:
    library, err_resp = _get_library(current_project(request), library_id)
    if err_resp:
        return err_resp

    fragments = []
    for frag in library.get_fragments():
        fragments.append(dict(code=frag.code, smiles=frag.smiles, id=frag.id))

    return JsonResponse(dict(fragments=fragments))


def as_csv(request, library_id: str) -> HttpResponse:
    library, err_resp = _get_library(current_project(request), library_id)
    if err_resp:
        return err_resp

    csv_text = f"# Fragments Library '{library.name}'\n" "FragmentCode,SMILES\n"

    for frag in library.get_fragments():
        csv_text += f"{frag.code},{frag.smiles}\n"

    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={library.name}.csv"

    return response
