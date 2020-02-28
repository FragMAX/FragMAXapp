from django.http import HttpResponse, HttpResponseNotFound
from fragview.projects import current_project
from fragview import smiles


def svg(request, fragment):
    proj = current_project(request)

    frag = proj.library.get_fragment(fragment)
    if frag is None:
        return HttpResponseNotFound(f"no '{fragment}' fragment in {proj.library.name} library")

    return HttpResponse(
        smiles.to_svg(frag.smiles),
        content_type="image/svg+xml")
