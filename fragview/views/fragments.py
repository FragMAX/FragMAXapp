from django.shortcuts import render
from fragview.projects import Project, current_project
from fragview.models import Fragment
from fragview.views.utils import get_crystals_fragment


def _get_fragments(project: Project) -> dict[Fragment, list]:
    fragments: dict = {}

    for crystal in project.get_crystals():
        if crystal.is_apo():
            continue

        frag = get_crystals_fragment(crystal)
        crystals = fragments.get(frag, [])
        crystals.append(crystal)
        fragments[frag] = crystals

    return fragments


def show(request):
    project = current_project(request)
    return render(request, "fragments.html", {"fragments": _get_fragments(project)})
