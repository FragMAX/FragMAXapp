from glob import glob

from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotFound, HttpResponseBadRequest

from fragview.sites import SITE
from fragview.models import Project, PendingProject
from fragview.forms import ProjectForm, NewLibraryForm
from fragview.proposals import get_proposals
from fragview.projects import current_project, project_shift_dirs
from worker import setup_project_files, add_new_shifts


def show(request):
    """
    projects list page, aka 'manage projects' page
    """
    return render(request, "fragview/projects.html", {"pending_projects": PendingProject.get_projects()})


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
        return render(request, "fragview/project.html", {"proj_layout": SITE.get_project_layout()})

    form = ProjectForm(request.POST, request.FILES)

    if not form.is_valid():
        return render(request, "fragview/project.html", {"form": form, "proj_layout": SITE.get_project_layout()})

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

    # _prepare_fragments(proj)

    return render(request, "fragview/library_view.html", {"form": "form"})


def set_current(request, id):
    proj = Project.get_project(get_proposals(request), id)
    if proj is None:
        return HttpResponseNotFound()

    request.user.set_current_project(proj)

    # redirect to the 'landing page' page
    return redirect(reverse("project_summary"))


def project_summary(request):
    proj = current_project(request)

    number_known_apo = len(glob(proj.data_path() + "/raw/" + proj.protein + "/*Apo*"))
    number_datasets = len(glob(proj.data_path() + "/raw/" + proj.protein + "/*"))

    totalapo = 0
    totaldata = 0

    for shift_dir in project_shift_dirs(proj):
        totalapo += len(glob(shift_dir + "/raw/" + proj.protein + "/*Apo*"))
        totaldata += len(glob(shift_dir + "/raw/" + proj.protein + "/*"))

    return render(
        request,
        "fragview/project_summary.html",
        {
            "known_apo": number_known_apo,
            "num_dataset": number_datasets,
            "totalapo": totalapo,
            "totaldata": totaldata,
            "fraglib": proj.library.name,
            "experiment_date": SITE.get_project_experiment_date(proj),
        },
    )
