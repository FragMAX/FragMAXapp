from django.shortcuts import render
from fragview.models import Library
from django.http import JsonResponse, HttpResponseNotFound, HttpResponse


def show(request):
    return render(request, "libraries.html", {"libraries": Library.get_all()})


def _get_library(library_id: str):
    try:
        return Library.get_by_id(library_id), None
    except Library.DoesNotExist:
        return (
            None,
            HttpResponseNotFound(f"fragment library with id '{library_id}' not found"),
        )


def as_json(_, library_id: str) -> HttpResponse:
    library, err_resp = _get_library(library_id)
    if err_resp:
        return err_resp

    fragments = []
    for frag in library.get_fragments():
        fragments.append(dict(code=frag.code, smiles=frag.smiles, id=frag.id))

    return JsonResponse(dict(fragments=fragments))


def as_csv(_, library_id: str) -> HttpResponse:
    library, err_resp = _get_library(library_id)
    if err_resp:
        return err_resp

    csv_text = f"# Fragments Library '{library.name}'\n" "FragmentCode,SMILES\n"

    for frag in library.get_fragments():
        csv_text += f"{frag.code},{frag.smiles}\n"

    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={library.name}.csv"

    return response
