from django.urls import reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from fragview.models import UserProject, PendingProject
from fragview.forms import ProjectForm
from fragview.proposals import get_proposals
from fragview.projects import current_project
from fragview.views.utils import get_project_libraries
from fragview.views.wrap import Wrapper
from worker import setup_project


class ProjectEntry(Wrapper):
    """
    adds method to list project's fragment libraries
    """

    def get_libraries(self):
        return get_project_libraries(self.orig)


def _wrap_projects(request):
    for project in UserProject.user_projects(get_proposals(request)):
        yield ProjectEntry(project)


def show(request):
    """
    projects list page, aka 'manage projects' page
    """
    #
    # divide pending projects into failed and (still) pending lists
    #
    failed = []
    pending = []
    for proj in PendingProject.get_all():
        if proj.failed():
            failed.append(proj)
        else:
            pending.append(proj)

    return render(
        request,
        "fragview/projects.html",
        {
            "project_entries": _wrap_projects(request),
            "failed_projects": failed,
            "pending_projects": pending,
        },
    )


def new(request):
    """
    GET requests show the 'Create new Project' page
    POST requests will try to create a new project
    """

    if request.method == "GET":
        proposals = sorted(get_proposals(request), reverse=True)
        return render(
            request,
            "fragview/project_new.html",
            {"proposals": proposals},
        )

    form = ProjectForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.get_error_message())

    protein, proposal, crystals, import_autoproc, encrypt = form.get_values()
    proj = UserProject.create_new(protein, proposal)

    setup_project.delay(
        str(proj.id), protein, proposal, crystals.as_list(), import_autoproc, encrypt
    )

    return HttpResponse("ok")


def delete(_, id):
    try:
        proj = UserProject.get(id)
    except UserProject.DoesNotExist:
        return HttpResponseNotFound(f"project {id} not found")

    #
    # Do a 'cosmetic' delete,
    # only delete the project from the list of existing projects.
    # leave all data files will be left in-place.
    #
    # This way it's should be possible to 'recover' a project,
    # deleted by mistake.
    #
    proj.delete()

    return HttpResponse(f"ok")


def set_current(request, id):
    proj = UserProject.get_project(get_proposals(request), id)
    if proj is None:
        return HttpResponseNotFound()

    request.user.set_current_project(proj)

    # redirect to the 'landing page' page
    return redirect(reverse("project_summary"))


def project_summary(request):
    libraries = get_project_libraries(current_project(request))
    return render(request, "fragview/project_summary.html", {"libraries": libraries})
