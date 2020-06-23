from glob import glob
import subprocess
from datetime import datetime
from time import sleep, time
from operator import itemgetter
from os import path, stat
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

    return render(request,
                  "fragview/jobhistory.html",
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
    # new logs are saved with a pattern based name
    # Dataset_software_epochTime_jobID_err.txt
    logHistory = list()

    software_names = {"xdsapp": "XDSAPP",
                      "xdsxscale": "xia2XDS",
                      "dials": "xia2DIALS",
                      "FSPipeline": "fspipeline",
                      "fspipeline": "fspipeline",
                      "DIMPLE": "DIMPLE",
                      "dimple": "DIMPLE",
                      "": "None"}

    log_dir = f"{proj.data_path()}/fragmax/logs"
    regular_logs = glob(f"{log_dir}/*out.txt")
    pandda_logs = glob(f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/*/pandda/logs/*log")

    for f in regular_logs:
        if "_" in f :
            status = "Unknown"
            refine_sw = f.split("/")[-1].split("_")[-4]
            if not refine_sw.isnumeric():
                refine_sw = software_names[refine_sw]
            epoch = int(stat(f).st_mtime)

            # jobID = f.split("_")[-2]
            datasetID = "_".join(f.split("_")[-3:-1])
            logName = f.split("/")[-1].split(f"_{datasetID}")[0]
            analysisStep = f.split("/")[-1].split("_")[0]
            process_sw = f.split("_")[1]
            errFile = f"{log_dir}/{logName}_{datasetID}_err.txt"
            outFile = f"{log_dir}/{logName}_{datasetID}_out.txt"
            if "Process_XDSAPP" in f:
                status = _get_xdsapp_status(f, epoch)
            if "Process_xia2" in f:
                status = _get_xia2_status(f, epoch)
            if "Refine_DIMPLE" in f:
                status = _get_dimple_status(f, epoch)
                process_sw, refine_sw = refine_sw, process_sw
                refine_sw = software_names[refine_sw]
            if "Refine_fspipeline" in f or "Refine_FSPipeline" in f:
                status = _get_fspipeline_status(f, epoch)
                process_sw, refine_sw = refine_sw, process_sw
                refine_sw = software_names[refine_sw]
            if "LigandFit_" in f:
                status = _get_ligandfit_status(f, epoch)
                if not refine_sw.isnumeric():
                    refine_sw = software_names[refine_sw]
                process_sw = software_names[process_sw]
            if "PanDDA_FREERFLAG" in f:
                status = _get_freerflag_status(f, epoch)
            if "PanDDA_CAD" in f:
                status = _get_cad_status(f, epoch)
            if "PanDDA_PhenixMaps" in f:
                status = _get_phenixmaps_status(f, epoch)
            selection = ""

            logHistory.append(
                [analysisStep, process_sw, refine_sw, datasetID, datetime.fromtimestamp(epoch),
                 errFile, outFile, status, selection])
    for f in pandda_logs:
        if "pandda-" in f:
            process_sw, refine_sw = f.split("/")[-4].split("_")
            analysisStep = "PanDDA"
            datasetID = f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/{process_sw}_{refine_sw}/selection.json"
            epoch = int(stat(f).st_mtime)
            errFile = ""
            outFile = f
            status = get_pandda_status(f)
            selection = "json"
            logHistory.append(
                [analysisStep, process_sw, refine_sw, datasetID, datetime.fromtimestamp(epoch),
                 errFile, outFile, status, selection])

    # sort jobs by date, newest first
    if "Running" in "".join([i[-1] for i in logHistory]):
        # logHistory.sort(key=lambda e: e[6],reverse=True)
        logHistory = sorted(logHistory, key=itemgetter(-1),  reverse=True)
    else:
        logHistory = sorted(logHistory, key=itemgetter(4),  reverse=True)

    return render(request,
                  "fragview/jobhistory.html",
                  {"logHistory": logHistory})


def _get_xdsapp_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "done" in log
    db_written = "writing results in db" in log
    if all([done, db_written]):
        status = _get_status_message(201)
    else:
        status = _get_status_message(200)
    return status


def _get_xia2_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "Status: normal termination" in log
    fail = "Error: " in log or "Indexing solution:" in log[-100:]
    if time() > epoch + 60*60 and not done:
        status = _get_status_message(417)
        return status
    else:
        if done:
            status = _get_status_message(201)
        elif fail:
            status = _get_status_message(417)
        else:
            status = _get_status_message(200)
        return status


def _get_dimple_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "To see it in Coot run" in log
    if time() > epoch + 60*10 and not done:
        status = _get_status_message(417)
        return status
    else:
        if done:
            status = _get_status_message(201)
        else:
            status = _get_status_message(200)
        return status


def _get_fspipeline_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "fspipeline finished since" in log

    if done:
        status = _get_status_message(201)
    elif fail:
        status = _get_status_message(417)
    else:
        status = _get_status_message(200)
    return status


def _get_ligandfit_status(logFile, epoch):
    with open(logFile, encoding="utf-8") as r:
        log = r.read()
    done = "Done cleaning up ..." in log
    fail = "0:00 Parsing Parsing Parsing Parsing" in log[-100:]

    if done:
        status = _get_status_message(201)
    elif fail:
        status = _get_status_message(417)
    else:
        status = _get_status_message(200)
    return status


def _get_phenixmaps_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "All done." in log
    fail = "Compute maps." in log[-50:]
    fail2 = "No map input specified - using default map types" in log[-50:]
    fail3 = "-------------" in log[-50:]
    if done:
        status = _get_status_message(201)
    elif any([fail, fail2, fail3]):
        status = _get_status_message(417)
    else:
        status = _get_status_message(200)
    return status


def _get_freerflag_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "Normal termination" in log
    fail = "(Error)" in log

    if done:
        status = _get_status_message(201)
    elif fail:
        status = _get_status_message(417)
    else:
        status = _get_status_message(200)
    return status


def _get_cad_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "Normal Termination of CAD" in log
    fail = "failed to open output file" in log
    if done:
        status = _get_status_message(201)
    elif fail:
        status = _get_status_message(417)
    else:
        status = _get_status_message(200)
    return status


def _get_panddaprep_status(logFile, epoch):
    with open(logFile) as r:
        log = r.read()
    done = "Status: normal termination" in log

    if done:
        status = _get_status_message(201)
    elif fail:
        status = _get_status_message(417)
    else:
        status = _get_status_message(200)
    return status


def get_pandda_status(f):
    pandda_out_path = f.split("logs/")[0]
    if path.exists(f"{pandda_out_path}/pandda.running"):
        status = _get_status_message(200)
    elif path.exists(f"{pandda_out_path}/pandda.finished"):
        status = _get_status_message(201)
    else:
        status = _get_status_message(417)
    return status


def _get_status_message(status_code):
    if status_code == 201:
        return "Finished"
    elif status_code == 200:
        return "Running"
    elif status_code == 417:
        return "Failed"
