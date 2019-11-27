import glob
import subprocess
from time import sleep

from django.shortcuts import render

from fragview.projects import current_project, project_shift_dirs


def soaking_plan(request):
   

    return render(request,
                  "fragview/soaking_plan.html",
                  {"platename": "plateNumber1"})
