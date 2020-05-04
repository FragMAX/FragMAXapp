from django.shortcuts import render
from fragview.projects import current_project


def soaking_plan(request):
    proj = current_project(request)
    return render(request,
                  "fragview/soaking_plan.html",
                  {"platename": "plateNumber1", 
                  "library": proj.library.name})
