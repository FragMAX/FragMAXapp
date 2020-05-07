from glob import glob
import subprocess
from time import sleep, ctime

from os import path

from django.shortcuts import render

from fragview.projects import current_project, project_shift_dirs
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
                    item for it in
                    [
                        glob(f"{shift_dir}/fragmax/logs/*{jobid}*")
                        for shift_dir in project_shift_dirs(proj)
                    ]
                    for item in it
                ]

                stdErr, stdOut = sorted(log_pairs)
                stdErr = stdErr.replace("/data/visitors/", "/static/")
                stdOut = stdOut.replace("/data/visitors/", "/static/")
            except Exception:
                stdErr, stdOut = ["-", "-"]

            hpcList.append([jobid, partition, name, user, ST, TIME, NODE, NODEn, stdErr, stdOut])

    return render(request,
                  "fragview/hpcstatus.html",
                  {"hpcList": hpcList, "proposal": proj.proposal})


def kill_job(request):
    jobid_k = str(request.GET.get("jobid_kill"))

    subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'scancel', jobid_k], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    sleep(5)

    out = hpc.jobs_list(request.user)
    output = ""

    for i in out.decode("UTF-8").split("\n")[1:-1]:
        proc_info = subprocess.Popen(
            ["ssh", "-t", "clu0-fe-1", "scontrol", "show", "jobid", "-dd", i.split()[0]],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        out_info, err_info = proc_info.communicate()
        stdout_file = [
            x for x in out_info.decode("UTF-8").splitlines() if "StdOut=" in x][0].split("/data/visitors")[-1]
        stderr_file = [
            x for x in out_info.decode("UTF-8").splitlines() if "StdErr=" in x][0].split("/data/visitors")[-1]
        try:
            prosw = [x for x in out_info.decode("UTF-8").splitlines() if "#SW=" in x][0].split("#SW=")[-1]
        except Exception:
            prosw = "Unknown"
        output += "<tr><td>" + "</td><td>".join(i.split())+"</td><td>" + prosw + \
                  "</td><td><a href='/static" + stdout_file + "'> job_" + i.split()[0] + \
                  "_out.txt</a></td><td><a href='/static" + stderr_file+"'>job_"+i.split()[0]+"""_err.txt</a></td><td>

        <form action="/hpcstatus_jobkilled/" method="get" id="kill_job_{0}" >
            <button class="btn-small" type="submit" value={0} name="jobid_kill" size="1">Kill</button>
        </form>

        </tr>""".format(i.split()[0])

    return render(
        request,
        "fragview/hpcstatus_jobkilled.html",
        {"command": output, "history": ""})


def jobhistory(request):
    proj = current_project(request)

    logHistory = list()

    log_dir = f"{proj.data_path()}/fragmax/logs"

    for f in glob(f"{log_dir}/*"):
        if "_" in f:
            cdate = ctime(path.getmtime(f))
            jobID = f.split("_")[-2]
            logName = f.split("/")[-1].split(f"_{jobID}")[0]
            errFile = f"{log_dir}/{logName}_{jobID}_err.txt"
            outFile = f"{log_dir}/{logName}_{jobID}_out.txt"
            logHistory.append([logName, jobID, cdate, errFile, outFile])

    return render(request,
                  "fragview/jobhistory.html",
                  {"logHistory": logHistory})
