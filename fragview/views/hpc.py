from glob import glob
import subprocess
from datetime import datetime
from time import sleep
from os import path
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponseBadRequest
from fragview.projects import current_project, project_shift_dirs
from fragview.forms import KillJobForm
from fragview import hpc


def status(request):
    proj = current_project(request)

    out = hpc.jobs_list(request.user)

    hpcList = list()
    for j in out.decode("UTF-8").split("\n")[1:-1]:
        if j.split() != []:
            try:
                jobid, partition, name, user, ST, TIME, NODE, NODEn = j.split()[:8]
            except ValueError:
                jobid, partition, name, user, ST, TIME, NODE, NODEn1, NODEn2 = j.split()[:9]
                NODEn = NODEn1 + NODEn2
            try:
                log_pairs = [
                    item
                    for it in [glob(f"{shift_dir}/fragmax/logs/*{jobid}*") for shift_dir in project_shift_dirs(proj)]
                    for item in it
                ]

                stdErr, stdOut = sorted(log_pairs)
                if path.exists(stdErr):
                    stdErr = stdErr.replace("/data/visitors/", "/static/")
                else:
                    stdErr = "None"
                if path.exists(stdOut):
                    stdOut = stdOut.replace("/data/visitors/", "/static/")
                else:
                    stdOut = "None"
            except Exception:
                stdErr, stdOut = ["None", "None"]

            hpcList.append([jobid, partition, name, user, ST, TIME, NODE, NODEn, stdErr, stdOut])

    return render(request, "fragview/hpcstatus.html", {"hpcList": hpcList, "proposal": proj.proposal})


def kill(request):
    form = KillJobForm(request.POST)

    if not form.is_valid():
        return HttpResponseBadRequest(f"{form.errors}")

    _kill_hpc_jobs(form.get_job_ids())

    return redirect(reverse("hpcstatus"))


def _kill_hpc_jobs(job_ids):
    cmd = ["ssh", "-t", "clu0-fe-1", "scancel"] + job_ids
    subprocess.run(cmd)
    sleep(2.4)


def jobhistory(request):
    proj = current_project(request)
    # new logs are saved with a pattern based name
    # Dataset_software_epochTime_jobID_err.txt
    logHistory = list()

    log_dir = f"{proj.data_path()}/fragmax/logs"

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
            errFile = f"{log_dir}/{logName}_{jobID}_err.txt"
            outFile = f"{log_dir}/{logName}_{jobID}_out.txt"

            logHistory.append([logName, jobID, datetime.fromtimestamp(epoch), errFile, outFile])

    # sort jobs by date, newest first
    logHistory.sort(key=lambda e: e[2], reverse=True)

    return render(request, "fragview/jobhistory.html", {"logHistory": logHistory})
