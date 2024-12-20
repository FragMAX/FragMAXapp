from pathlib import Path
from django.urls import reverse
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from fragview.models import UserProject, PendingProject, Library
from fragview.forms import ProjectForm
from fragview.proposals import get_proposals
from fragview.projects import current_project
from fragview.views.utils import get_project_libraries
from fragview.views.wrap import Wrapper
from fragview.sites import current
from projects.database import get_project_db_file
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
        "projects.html",
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
            "project_new.html",
            {"proposals": proposals},
        )

    #
    # HZB-site hack, use 'username' as proposal
    #
    # As HZB is not using proposal to organize data, use the
    # user name as 'proposal' for now. Perhaps we should
    # restructure the code to no use 'proposal' concept in general.
    #
    post_args = request.POST
    if current.proposals_disabled():
        # make a mutable copy of POST arguments dict
        post_args = post_args.copy()
        # put down current user-name as 'proposal'
        post_args["proposal"] = request.user.username

    form = ProjectForm(post_args, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.get_error_message())

    protein, proposal, crystals, libraries, import_autoproc = form.get_values()

    proj = UserProject.create_new(protein, proposal)

    setup_project.delay(
        str(proj.id),
        protein,
        proposal,
        crystals.as_list(),
        libraries,
        import_autoproc,
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
    # All data files will be left in-place.
    #
    # This way it should be possible to 'recover' a project,
    # deleted by mistake.
    #

    # delete project's private fragment libraries
    for lib in Library.get_all_private(id):
        lib.delete()

    proj.delete()

    #
    # rename the project DB file, for easy ocular identification
    # of removed projects in the DB folder
    #
    proj_db = get_project_db_file(settings.PROJECTS_DB_DIR, id)
    proj_db_deleted = Path(proj_db.parent, f"{proj_db.name}-deleted")
    renamed = proj_db.rename(proj_db_deleted)
    print(f"{proj_db} -> {renamed}")

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
    return render(request, "project_summary.html", {"libraries": libraries})
