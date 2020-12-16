from glob import glob
from datetime import datetime
from os import path
from pathlib import Path
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponseBadRequest
from fragview.projects import current_project, project_logs_dir
from fragview.forms import KillJobForm
from fragview import hpc


def status(request):
    return render(request, "fragview/hpcstatus.html", {"jobs": hpc.get_jobs()})


def kill(request):
    form = KillJobForm(request.POST)

    if not form.is_valid():
        return HttpResponseBadRequest(f"{form.errors}")

    hpc.cancel_jobs(form.get_job_ids())

    return redirect(reverse("hpcstatus"))


def jobhistory(request):
    proj = current_project(request)
    # new logs are saved with a pattern based name
    # Dataset_software_epochTime_jobID_err.txt
    logHistory = list()

    log_dir = project_logs_dir(proj)
    relative_log_dir = Path(log_dir).relative_to(proj.data_path())

    for f in glob(f"{log_dir}/*out.txt"):
        if "_" in f:
            try:
                epoch = int(f.split("/")[-1].split("_")[-3])
            except (IndexError, ValueError):
                # handle old-style log files,
                # where epoch was not included into the filename
                epoch = path.getmtime(f)

            jobID = f.split("_")[-2]
            logName = f.split("/")[-1].split(f"_{jobID}")[0]
            errFile = Path(relative_log_dir, f"{logName}_{jobID}_err.txt")
            outFile = Path(relative_log_dir, f"{logName}_{jobID}_out.txt")

            logHistory.append(
                [logName, jobID, datetime.fromtimestamp(epoch), errFile, outFile]
            )

    # sort jobs by date, newest first
    logHistory.sort(key=lambda e: e[2], reverse=True)

    return render(request, "fragview/jobhistory.html", {"logHistory": logHistory})
