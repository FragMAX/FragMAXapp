from datetime import datetime
from os import path
from pathlib import Path
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponseBadRequest
from fragview.projects import current_project
from fragview.forms import KillJobForm
from fragview import hpc


def status(request):
    return render(
        request, "hpcstatus.html", {"jobs": hpc.get_jobs(current_project(request))}
    )


def kill(request):
    form = KillJobForm(request.POST)

    if not form.is_valid():
        return HttpResponseBadRequest(f"{form.errors}")

    hpc.cancel_jobs(form.get_job_ids())

    return redirect(reverse("hpcstatus"))


def jobhistory(request):
    project = current_project(request)
    # new logs are saved with a pattern based name
    # Dataset_software_epochTime_jobID_err.txt
    logHistory = list()

    logs_dir = project.logs_dir
    relative_log_dir = Path(logs_dir).relative_to(project.project_dir)

    for file in logs_dir.glob("*out.txt"):
        fpath = str(file)

        if "_" in fpath:
            try:
                epoch = int(fpath.split("/")[-1].split("_")[-3])
            except (IndexError, ValueError):
                # handle old-style log files,
                # where epoch was not included into the filename
                epoch = path.getmtime(fpath)

            jobID = fpath.split("_")[-2]
            logName = fpath.split("/")[-1].split(f"_{jobID}")[0]
            errFile = Path(relative_log_dir, f"{logName}_{jobID}_err.txt")
            outFile = Path(relative_log_dir, f"{logName}_{jobID}_out.txt")

            logHistory.append(
                [logName, jobID, datetime.fromtimestamp(epoch), errFile, outFile]
            )

    # sort jobs by date, newest first
    logHistory.sort(key=lambda e: e[2], reverse=True)

    return render(request, "jobhistory.html", {"logHistory": logHistory})
