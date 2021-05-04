from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotFound, HttpResponseBadRequest
from fragview.sites import SITE
from fragview.models import UserProject, PendingProject
from fragview.forms import ProjectForm, NewLibraryForm
from fragview.proposals import get_proposals
from fragview.projects import current_project
from fragview.views.utils import get_project_libraries
from fragview.views.wrap import Wrapper
from worker import setup_project_files, add_new_shifts


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

    return render(
        request,
        "fragview/projects.html",
        {
            "project_entries": _wrap_projects(request),
            "pending_projects": PendingProject.get_projects(),
        },
    )


def _update_project(form):
    old_shifts = set(form.model.shifts())

    form.update()
    new_shifts = set(form.model.shifts())

    added = new_shifts - old_shifts

    if len(added) > 0:  # new shift added
        # put the project into 'pending' state
        form.model.set_pending()
        # start importing datasets from the new shift(s)
        add_new_shifts.delay(form.model.id, list(added))


def edit(request, id):
    """
    GET requests show the 'Edit Project' page
    POST requests will update or delete the project
    """
    proj = get_object_or_404(Project, pk=id)
    form = ProjectForm(request.POST or None, request.FILES or None, model=proj)

    if request.method == "POST":
        action = request.POST["action"]
        if action == "modify":
            if form.is_valid():
                _update_project(form)
                return redirect("/projects/")
        elif action == "delete":
            proj.delete()
            return redirect("/projects/")
        else:
            return HttpResponseBadRequest(f"unexpected action '{action}'")

    return render(
        request,
        "fragview/project.html",
        {"form": form, "project_id": proj.id, "proj_layout": SITE.get_project_layout()},
    )


def new(request):
    """
    GET requests show the 'Create new Project' page
    POST requests will try to create a new project
    """
    if request.method == "GET":
        return render(
            request, "fragview/project.html", {"proj_layout": SITE.get_project_layout()}
        )

    form = ProjectForm(request.POST, request.FILES)

    if not form.is_valid():
        return render(
            request,
            "fragview/project.html",
            {"form": form, "proj_layout": SITE.get_project_layout()},
        )

    proj = form.save()
    proj.set_pending()
    setup_project_files.delay(proj.id)

    return redirect("/projects/")


def update_library(request):
    """
    GET requests show the 'Create new Project' page
    POST requests will try to create a new project
    """
    # proj = current_project(request)

    if request.method == "GET":
        return render(request, "fragview/library_view.html")

    form = NewLibraryForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "fragview/library_view.html", {"form": "form"})

    return render(request, "fragview/library_view.html", {"form": "form"})


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
