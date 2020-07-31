import os
import csv
from os import path
from glob import glob
import pyfastcopy  # noqa

from django.shortcuts import render

from fragview.projects import project_process_protein_dir
from fragview.projects import current_project, project_results_file
from fragview.xsdata import XSDataCollection
from fragview.views.misc import perc2float
from fragview.status import run_update_status
from fragview.sites import SITE
from fragview.dsets import get_datasets


def set_details(request):
    def _logs(logs_dir):
        log_paths = [x for x in glob(f"{logs_dir}/*") if "txt" in x or "LP" in x or "log" in x or "out" in x]
        return [(path.basename(p), p) for p in log_paths]

    proj = current_project(request)

    dataset = str(request.GET["proteinPrefix"])
    prefix = dataset.split(";")[0]
    images = dataset.split(";")[1]
    run = dataset.split(";")[2]
    images = str(int(images) / 2)

    dataset_dir = path.join(project_process_protein_dir(proj), prefix, f"{prefix}_{run}")

    curp = proj.data_path()
    xmlfile = os.path.join(proj.data_path(), "fragmax", "process", proj.protein, prefix, prefix + "_" + run + ".xml")
    xsdata = XSDataCollection(xmlfile)

    energy = format(12.4 / xsdata.wavelength, ".2f")
    totalExposure = format(xsdata.exposureTime * xsdata.numberOfImages, ".2f")
    edgeResolution = str(xsdata.resolution * 0.75625)

    ligpng = "/static/img/nolig.png"
    if "Apo" not in prefix.split("-"):
        ligpng = prefix.split("-")[-1]

    fragConc = "N/A"
    solventConc = "N/A"
    soakTime = "N/A"

    snapshots = [spath.replace("/mxn/groups/ispybstorage/", "/static/") for spath in xsdata.snapshots]

    half = int(float(images) / 200)

    # getreports
    scurp = curp.replace("/data/visitors/", "/static/")

    dialsreport = (
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "/dials/xia2.html"
    )

    xdsreport = (
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "/xdsxscale/xia2.html"
    )

    autoprocreport = (
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "/autoproc/summary.html"
    )

    xdsappOK = "no"
    dialsOK = "no"
    xdsOK = "no"
    autoprocOK = "no"
    ednaOK = "no"
    fastdpOK = "no"
    pipedreamOK = "no"
    fastdpLogs = ""
    ednaLogs = ""
    autoprocLogs = ""
    xdsappLogs = ""
    xdsLogs = ""
    dialsLogs = ""
    pipedreamLogs = ""
    _tables = {"autoproc": {}, "edna": {}, "fastdp": {}, "xdsapp": {}, "dials": {}, "xdsxscale": {}, "pipedream": {}}
    # XDSAPP logs
    xdsapp_dir = path.join(dataset_dir, "xdsapp")
    xdsappreport = path.join(xdsapp_dir, f"results_{prefix}_{run}_data.txt")
    if path.exists(xdsappreport):
        xdsappOK = "ready"
        xdsappLogs = _logs(xdsapp_dir)
    _tables["xdsapp"] = parse_aimless(path.join(dataset_dir, "xdsapp", f"results_{prefix}_{run}_data.txt"))
    # DIALS logs
    dials_dir = path.join(dataset_dir, "dials")
    if path.exists(path.join(dials_dir, "xia2.html")):
        dialsOK = "ready"
        dialsLogs = _logs(path.join(dials_dir, "LogFiles"))
    _tables["dials"] = parse_aimless(path.join(dataset_dir, "dials", "LogFiles", "AUTOMATIC_DEFAULT_aimless.log"))
    # XIA2/XDS logs
    xds_dir = path.join(dataset_dir, "xdsxscale")
    if path.exists(path.join(xds_dir, "xia2.html")):
        xdsOK = "ready"
        xdsLogs = _logs(path.join(xds_dir, "LogFiles"))
    _tables["xdsxscale"] = parse_aimless(
        path.join(dataset_dir, "xdsxscale", "LogFiles", "AUTOMATIC_DEFAULT_aimless.log")
    )
    # autoPROC logs
    autoproc_dir = path.join(dataset_dir, "autoproc")
    if path.exists(path.join(autoproc_dir, "summary.html")):
        autoprocOK = "ready"
        autoprocLogs = _logs(autoproc_dir)
    _tables["autoproc"] = parse_aimless(path.join(dataset_dir, "autoproc", "summary.html"))

    # Pipedream logs
    pipedream_dir = path.join(proj.data_path(), "fragmax", "results", f"{prefix}_{run}", "pipedream")
    if path.exists(path.join(pipedream_dir, "process", "summary.html")):
        pipedreamOK = "ready"
        pipedreamLogs = _logs(pipedream_dir)
    _tables["pipedream"] = parse_aimless(path.join(pipedream_dir, "process", "summary.html"))

    # EDNA logs
    edna_dir = path.join(dataset_dir, "edna")
    ednareport = path.join(edna_dir, f"ep_{prefix}_{run}_phenix_xtriage_noanom.log")
    if path.exists(ednareport):
        ednaOK = "ready"
        ednaLogs = _logs(edna_dir)
    _tables["edna"] = parse_aimless(path.join(dataset_dir, "edna", f"ep_{prefix}_{run}_aimless_anom.log"))
    # Fast DP reports
    fastdp_dir = path.join(dataset_dir, "fastdp")
    fastdpreport = path.join(fastdp_dir, f"ap_{prefix}_run{run}_noanom_fast_dp.log")
    if path.exists(fastdpreport):
        fastdpOK = "ready"
        fastdpLogs = _logs(fastdp_dir)
    _tables["fastdp"] = parse_aimless(path.join(dataset_dir, "fastdp", f"ap_{prefix}_run{run}_noanom_aimless.log"))

    # Logs for refinement methods
    # Dimple
    dimple_res_dirs = glob(f"{proj.data_path()}/fragmax/results/{prefix}_{run}/*/dimple")
    _dimple_logs = dict()
    for _file in dimple_res_dirs:
        proc_m = path.basename(path.dirname(_file))
        _dimple_logs[proc_m] = {path.basename(x): x for x in sorted(glob(f"{_file}/*log"))}
    # BUSTER
    buster_res_dirs = glob(f"{proj.data_path()}/fragmax/results/{prefix}_{run}/*/buster")
    _buster_logs = dict()
    for _file in buster_res_dirs:
        proc_m = path.basename(path.dirname(_file))
        _buster_logs[proc_m] = {path.basename(x): x for x in sorted(glob(f"{_file}/*log"))}
    # fspipeline
    fspipeline_res_dirs = glob(f"{proj.data_path()}/fragmax/results/{prefix}_{run}/*/fspipeline")
    _fspipeline_logs = dict()
    for _file in fspipeline_res_dirs:
        fsp_logs = sorted(glob(f"{_file}/*log") + glob(f"{_file}/*/*log"))
        proc_m = path.basename(path.dirname(_file))
        _fspipeline_logs[proc_m] = {"/".join(x.split(f"{prefix}_{run}/")[-1].split("/")[2:]): x for x in fsp_logs}
    # Pipedream
    pipedream_res_dirs = f"{proj.data_path()}/fragmax/results/{prefix}_{run}/pipedream"
    _pipedream_logs = dict()
    if path.exists(pipedream_res_dirs):
        _pipedream_logs["pipedream"] = {
            path.basename(x): x
            for x in sorted(glob(f"{pipedream_res_dirs}/*log") + glob(f"{pipedream_res_dirs}/*out"))
        }
        _pipedream_logs["autoproc"] = {
            "refine/" + path.basename(x): x
            for x in sorted(glob(f"{pipedream_res_dirs}/refine/*log") + glob(f"{pipedream_res_dirs}/refine/*out"))
        }
        _pipedream_logs["buster"] = {
            "process/" + path.basename(x): x
            for x in sorted(glob(f"{pipedream_res_dirs}/process/*log") + glob(f"{pipedream_res_dirs}/process/*out"))
        }
        _pipedream_logs["rhofit"] = {
            "rhofit/" + path.basename(x): x
            for x in sorted(glob(f"{pipedream_res_dirs}/rhofit/*log") + glob(f"{pipedream_res_dirs}/rhofit/*out"))
        }

    # Information for the data processing table
    spg_list = [_tables[key]["spg"] for key in _tables.keys()]
    unique_rflns_list = [_tables[key]["unique_rflns"] for key in _tables.keys()]
    total_observations_list = [_tables[key]["total_observations"] for key in _tables.keys()]

    overall_res_list = [_tables[key]["low_res_avg"] + " - " + _tables[key]["high_res_avg"] for key in _tables.keys()]
    outter_shell_res_list = [
        "(" + _tables[key]["low_res_out"] + " - " + _tables[key]["high_res_out"] + ")" for key in _tables.keys()
    ]
    resolution_list = zip(overall_res_list, outter_shell_res_list)
    for n, i in enumerate(overall_res_list):
        if i == " - ":
            overall_res_list[n] = ""
    for n, i in enumerate(outter_shell_res_list):
        if i == "( - )":
            outter_shell_res_list[n] = ""
    unit_cell_list_d = [", ".join(_tables[key]["unit_cell"].split(",")[:3]) for key in _tables.keys()]
    unit_cell_list_a = [", ".join(_tables[key]["unit_cell"].split(",")[3:]) for key in _tables.keys()]
    unit_cell_list = zip(unit_cell_list_d, unit_cell_list_a)

    multiplicity_list = [_tables[key]["multiplicity"] for key in _tables.keys()]

    isig_avg_list = [_tables[key]["isig_avg"] for key in _tables.keys()]
    isig_out_list = ["(" + _tables[key]["isig_out"] + ")" for key in _tables.keys()]
    for n, i in enumerate(isig_out_list):
        if i == "()":
            isig_out_list[n] = ""
    isgi_list = zip(isig_avg_list, isig_out_list)
    rmeas_avg_list = [_tables[key]["rmeas_avg"] for key in _tables.keys()]
    rmeas_out_list = ["(" + _tables[key]["rmeas_out"] + ")" for key in _tables.keys()]
    for n, i in enumerate(rmeas_out_list):
        if i == "()":
            rmeas_out_list[n] = ""
    rmeas_list = zip(rmeas_avg_list, rmeas_out_list)

    completeness_avg_list = [_tables[key]["completeness_avg"] for key in _tables.keys()]
    completeness_out_list = ["(" + _tables[key]["completeness_out"] + ")" for key in _tables.keys()]
    for n, i in enumerate(completeness_out_list):
        if i == "()":
            completeness_out_list[n] = ""
    completeness_list = zip(completeness_avg_list, completeness_out_list)

    mosaicity_list = [_tables[key]["mosaicity"] for key in _tables.keys()]
    ISa_list = [_tables[key]["ISa"] for key in _tables.keys()]
    WilsonB_list = [_tables[key]["WilsonB"] for key in _tables.keys()]
    cc12_avg_list = [_tables[key]["cc12_avg"] for key in _tables.keys()]
    cc12_out_list = ["(" + _tables[key]["cc12_out"] + ")" for key in _tables.keys()]
    cc12_list = zip(cc12_avg_list, cc12_out_list)

    if "Apo" in prefix:
        soakTime = "Soaking not performed"
        fragConc = "-"
        solventConc = "-"

    results_file = project_results_file(proj)
    if os.path.exists(results_file):
        with open(results_file) as readFile:
            reader = csv.reader(readFile)
            lines = [line for line in list(reader)[1:] if prefix + "_" + run in line[0]]
    else:
        lines = []

    for n, line in enumerate(lines):
        if len(line) == 23:
            lines[n].append("")
    return render(
        request,
        "fragview/dataset_info.html",
        {
            "csvfile": lines,
            "shift": curp.split("/")[-1],
            "run": run,
            "imgprf": prefix,
            "imgs": images,
            "ligand": ligpng,
            "fragConc": fragConc,
            "solventConc": solventConc,
            "soakTime": soakTime,
            "xsdata": xsdata,
            "snapshots": snapshots,
            "diffraction_half": half,
            "energy": energy,
            "totalExposure": totalExposure,
            "edgeResolution": edgeResolution,
            "xdsappreport": xdsappreport,
            "dialsreport": dialsreport,
            "xdsreport": xdsreport,
            "autoprocreport": autoprocreport,
            "ednareport": ednareport,
            "fastdpreport": fastdpreport,
            "xdsappOK": xdsappOK,
            "dialsOK": dialsOK,
            "xdsOK": xdsOK,
            "autoprocOK": autoprocOK,
            "pipedreamOK": pipedreamOK,
            "ednaOK": ednaOK,
            "fastdpOK": fastdpOK,
            "fastdpLogs": fastdpLogs,
            "ednaLogs": ednaLogs,
            "autoprocLogs": autoprocLogs,
            "pipedreamLogs": pipedreamLogs,
            "xdsappLogs": xdsappLogs,
            "xdsLogs": xdsLogs,
            "dialsLogs": dialsLogs,
            "site": SITE,
            "beamline": SITE.get_beamline_info(),
            "spg_list": spg_list,
            "unique_rflns_list": unique_rflns_list,
            "total_observations_list": total_observations_list,
            "unit_cell_list": unit_cell_list,
            "multiplicity_list": multiplicity_list,
            "isgi_list": isgi_list,
            "rmeas_list": rmeas_list,
            "completeness_list": completeness_list,
            "mosaicity_list": mosaicity_list,
            "ISa_list": ISa_list,
            "WilsonB_list": WilsonB_list,
            "cc12_list": cc12_list,
            "resolution_list": resolution_list,
            "dimple_logs": _dimple_logs,
            "fspipeline_logs": _fspipeline_logs,
            "pipedream_logs": _pipedream_logs,
        },
    )


def show_all(request):
    proj = current_project(request)

    resyncStatus = str(request.GET.get("resyncstButton"))

    if "resyncStatus" in resyncStatus:
        run_update_status(proj)

    return render(request, "fragview/datasets.html", {"datasets": get_datasets(proj)})


def proc_report(request):
    method = ""
    report = str(request.GET.get("dataHeader"))
    if "fastdp" in report or "EDNA" in report:
        method = "log"
        with open(report.replace("/static/", "/data/visitors/"), "r") as readFile:
            report = readFile.readlines()
        report = "<br>".join(report)

    return render(request, "fragview/procReport.html", {"reportHTML": report, "method": method})


def parse_aimless(pplog):
    if path.exists(pplog):
        with open(pplog) as r:
            log = r.readlines()
        if "xdsapp" in pplog:
            for line in log:
                if "Space group   " in line:
                    spg = line.split()[2]
                if "Unit cell parameters [A]" in line:
                    unit_cell = ",".join(line.split()[4:])
                if "Resolution limit" in line:
                    low_res_avg, high_res_avg = line.split()[3].split("-")
                    low_res_out, high_res_out = line.split()[4][1:-1].split("-")
                if "No. of reflections" in line:
                    total_observations = line.split()[-1]
                if "No. of uniques" in line:
                    unique_rflns = line.split()[-1]
                if "Multiplicity" in line:
                    multiplicity = line.split()[-1]
                if "I/sigI" in line:
                    isig_avg = line.split()[-2]
                    isig_out = line.split()[-1][1:-1]
                if "R_meas [%]" in line:
                    rmeas_avg = line.split()[-2]
                    rmeas_out = line.split()[-1][1:-1]
                if "Completeness [%]" in line:
                    completeness_avg = line.split()[-2]
                    completeness_out = line.split()[-1][1:-1]
                if "B(Wilson) [A^2]" in line:
                    WilsonB = line.split()[-1]
                if "Mosaicity [deg]" in line:
                    mosaicity = line.split()[-1]
                if "CC(1/2)" in line:
                    cc12_avg = line.split()[-2]
                    cc12_out = line.split()[-1][1:-1]
                if "ISa" in line:
                    ISa = line.split()[-1]
        if "autoproc" in pplog or "pipedream" in pplog:
            spg = "None"
            for n, line in enumerate(log):
                if "Unit cell and space group:" in line:
                    spg = "".join(line.split()[11:]).replace("'", "")
                    unit_cell = ",".join(line.split()[5:11])
                if "Low resolution limit  " in line:
                    low_res_avg, low_res_out = line.split()[3], line.split()[5]
                if "High resolution limit  " in line:
                    high_res_out, high_res_avg = line.split()[3], line.split()[5]
                if "total   " in line:
                    total_observations, unique_rflns = line.split()[1:3]
                    multiplicity = str("{:.1f}".format(int(total_observations) / int(unique_rflns)))
                    isig_avg = line.split()[8]
                    isig_out = log[n - 1].split()[8]
                    rmeas_avg = perc2float(line.split()[9])
                    rmeas_out = perc2float(log[n - 1].split()[9])
                    completeness_avg = line.split()[4].replace("%", "")
                    completeness_out = log[n - 1].split()[4].replace("%", "")
                    cc12_avg = line.split()[10]
                    cc12_out = log[n - 1].split()[10]
                    WilsonB = ""
                if "CRYSTAL MOSAICITY (DEGREES)" in line:
                    mosaicity = line.split()[-1]
                if "ISa (" in line:
                    ISa = log[n + 1].split()[-1]
            if spg == "None":
                spg = ""
                unique_rflns = ""
                total_observations = ""
                low_res_avg = ""
                low_res_out = ""
                high_res_avg = ""
                high_res_out = ""
                unit_cell = ""
                multiplicity = ""
                isig_avg = ""
                isig_out = ""
                rmeas_avg = ""
                rmeas_out = ""
                completeness_avg = ""
                completeness_out = ""
                mosaicity = ""
                ISa = ""
                WilsonB = ""
                cc12_avg = ""
                cc12_out = ""

        else:
            for line in log:
                if "Space group:" in line:
                    spg = "".join(line.split()[2:])
                if "Number of unique reflections" in line:
                    unique_rflns = line.split()[-1]
                if "Total number of observations" in line:
                    total_observations = line.split()[-3]
                if "Low resolution limit" in line:
                    low_res_avg = line.split()[3]
                    low_res_out = line.split()[-1]
                if "High resolution limit" in line:
                    high_res_avg = line.split()[3]
                    high_res_out = line.split()[-1]
                if "Average unit cell:" in line:
                    unit_cell = ",".join(line.split()[3:])
                if "Multiplicity" in line:
                    multiplicity = line.split()[1]
                if "Mean((I)/sd(I))" in line:
                    isig_avg = line.split()[1]
                    isig_out = line.split()[-1]
                if "Rmeas (all I+ & I-)" in line:
                    rmeas_avg = line.split()[5]
                    rmeas_out = line.split()[-1]
                if "completeness" in line:
                    completeness_avg = line.split()[-3]
                    completeness_out = line.split()[-1]
                if "mosaicity" in line:
                    mosaicity = line.split()[-1]
                if "Mn(I) half-set correlation CC(1/2)" in line:
                    cc12_avg = line.split()[-3]
                    cc12_out = line.split()[-1]
                ISa = ""
                WilsonB = ""

        stats = {
            "spg": spg,
            "unique_rflns": unique_rflns,
            "total_observations": total_observations,
            "low_res_avg": low_res_avg,
            "low_res_out": low_res_out,
            "high_res_avg": high_res_avg,
            "high_res_out": high_res_out,
            "unit_cell": unit_cell,
            "multiplicity": multiplicity,
            "isig_avg": isig_avg,
            "isig_out": isig_out,
            "rmeas_avg": rmeas_avg,
            "rmeas_out": rmeas_out,
            "completeness_avg": completeness_avg,
            "completeness_out": completeness_out,
            "mosaicity": mosaicity,
            "ISa": ISa,
            "WilsonB": WilsonB,
            "cc12_avg": cc12_avg,
            "cc12_out": cc12_out,
        }
    else:
        stats = {
            "spg": "",
            "unique_rflns": "",
            "total_observations": "",
            "low_res_avg": "",
            "low_res_out": "",
            "high_res_avg": "",
            "high_res_out": "",
            "unit_cell": "",
            "multiplicity": "",
            "isig_avg": "",
            "isig_out": "",
            "rmeas_avg": "",
            "rmeas_out": "",
            "completeness_avg": "",
            "completeness_out": "",
            "mosaicity": "",
            "ISa": "",
            "WilsonB": "",
            "cc12_avg": "",
            "cc12_out": "",
        }
    return stats
