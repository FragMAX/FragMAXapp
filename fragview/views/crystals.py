from typing import Optional, Iterable
from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from dataclasses import dataclass
from fragview.forms import CrystalsImportForm
from fragview.models import UserProject, Fragment
from fragview.views.utils import get_crystals_fragment
from fragview.projects import Project, current_project
from fragview.crystals import Crystals, Crystal
from worker import import_crystals


@dataclass
class _CrystalInfo:
    id: str
    datasets_num: int
    fragment_library: Optional[str]
    fragment_code: Optional[str]


def _get_crystals(project: Project) -> Iterable[_CrystalInfo]:
    def _get_frag_info(crystal):
        if crystal.is_apo():
            return None, None

        frag = get_crystals_fragment(crystal)
        return frag.library.name, frag.code

    for crystal in project.get_crystals().order_by(lambda c: c.id):
        library, fragment = _get_frag_info(crystal)

        yield _CrystalInfo(crystal.id, crystal.datasets.count(), library, fragment)


def show(request):
    project = current_project(request)

    return render(request, "crystals.html", {"crystals": list(_get_crystals(project))})


def new(request):
    """
    the 'Import New Crystals' page
    """
    return render(request, "crystals_new.html")


class _InvalidCrystal(Exception):
    def __init__(self, crystal: Crystal, message: str):
        super().__init__(f"{crystal.SampleID}: {message}")


def _validate_crystals_csv(project: Project, crystals: Crystals):
    def _validate_apo(crystal: Crystal):
        if crystal.FragmentCode is None and crystal.FragmentLibrary is None:
            # still APO, all good
            return

        raise _InvalidCrystal(crystal, "Apo crystal have a fragment defined.")

    def _validate_fragment(new_crystal: Crystal, old_fragment: Fragment):
        """
        validate that new crystal defines same fragment as previously
        """
        # check that fragment is specified
        if new_crystal.FragmentLibrary is None or new_crystal.FragmentCode is None:
            raise _InvalidCrystal(new_crystal, "no fragment specified")

        # check that still same fragment library
        if new_crystal.FragmentLibrary != old_fragment.library.name:
            raise _InvalidCrystal(
                new_crystal, f"unexpected library {new_crystal.FragmentLibrary}"
            )

        # check that still same fragment code
        if new_crystal.FragmentCode != old_fragment.code:
            raise _InvalidCrystal(
                new_crystal, f"unexpected fragment code {new_crystal.FragmentCode}"
            )

    for crystal in crystals:
        existing_crystal = project.get_crystal(crystal.SampleID)
        if existing_crystal is None:
            # this is new crystal, no need to validate it
            continue

        fragment = get_crystals_fragment(existing_crystal)
        if fragment is None:
            # Apo crystal
            _validate_apo(crystal)
        else:
            _validate_fragment(crystal, fragment)


def import_csv(request):
    if request.method != "POST":
        return HttpResponseBadRequest("expected POST request")

    project = current_project(request)
    form = CrystalsImportForm(project, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.get_error_message())

    crystals = form.get_crystals()

    try:
        _validate_crystals_csv(project, crystals)
    except _InvalidCrystal as ex:
        return HttpResponseBadRequest(str(ex))

    # put project into 'pending' state while we import new crystals
    UserProject.get(project.id).set_pending(project.protein)

    # start the 'import crystals' task
    import_crystals.delay(str(project.id), crystals.as_list())

    return HttpResponse("ok")
