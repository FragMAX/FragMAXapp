from glob import glob
from os import path
from pathlib import Path
from django.shortcuts import render
from fragview.projects import (
    current_project,
    project_process_protein_dir,
    project_results_dir,
    project_results_file,
)
from fragview.scraper import autoproc, edna
from fragview.xsdata import XSDataCollection
from fragview.sites import SITE
from fragview.fileio import read_csv_lines


def show(request, images, prefix, run):
    def _logs(logs_dir):
        log_paths = [
            Path(x) for x in glob(f"{logs_dir}/*") if "txt" in x or "LP" in x or "log" in x or "out" in x or "html" in x
        ]
        return [(p.name, p.relative_to(curp)) for p in log_paths]

    def _pipedream_logs():
        pipedream_dir = path.join(project_results_dir(proj), f"{prefix}_{run}", "pipedream")

        if not path.exists(path.join(pipedream_dir, "process", "summary.html")):
            return [], None

        vals = parse_log_process(path.join(pipedream_dir, "process", "summary.html"))
        vals["tool"] = "pipedream"
        vals["report"] = Path(pipedream_dir, "summary.out").relative_to(curp)

        return _logs(pipedream_dir), vals

    def _autoproc_logs():
        autoproc_summary_report = autoproc.get_summary_report(proj, f"{prefix}_{run}")

        if autoproc_summary_report is None:
            return [], None

        vals = autoproc.parse_statistics(autoproc_summary_report)
        return autoproc.get_log_files(autoproc_summary_report), vals

    def _edna_logs():
        edna_report = edna.get_report(proj, prefix, run)

        if edna_report is None:
            return [], None

        vals = edna.parse_statistics(proj, prefix, run)
        vals.report = edna_report

        return edna.get_log_files(edna_report), vals

    def _xdsapp_logs():
        def _report_file():
            #
            # handle different versions of XDSAPP,
            # older versions name the report file: 'results_<dataset>_data.txt'
            # newer versions                       'results_<dataset>.txt'
            #
            report_file = next(xdsapp_dir.glob(f"results_{prefix}_{run}*.txt"), None)
            if report_file is None or not report_file.is_file():
                return None

            return report_file

        xdsapp_dir = Path(dataset_dir, "xdsapp")
        xdsappreport = _report_file()

        if xdsappreport is None:
            return [], None

        vals = parse_log_process(str(xdsappreport))
        vals["tool"] = "xdsapp"
        vals["report"] = xdsappreport.relative_to(curp)
        return _logs(xdsapp_dir), vals

    def _dials_logs():
        dials_dir = path.join(dataset_dir, "dials")

        if not path.exists(path.join(dials_dir, "xia2.html")):
            return [], None

        vals = parse_log_process(path.join(dials_dir, "xia2.html"))
        vals["tool"] = "xia2/dials"
        vals["report"] = Path(dials_dir, "xia2.html").relative_to(curp)

        return _logs(path.join(dials_dir, "LogFiles")), vals

    def _xds_logs():
        xds_dir = path.join(dataset_dir, "xdsxscale")

        if not path.exists(path.join(xds_dir, "xia2.html")):
            return [], None

        vals = parse_log_process(path.join(xds_dir, "xia2.html"))
        vals["tool"] = "xia2/xds"
        vals["report"] = Path(xds_dir, "xia2.html").relative_to(curp)

        return _logs(path.join(xds_dir, "LogFiles")), vals

    proj = current_project(request)

    images = str(images / 2)

    dataset_dir = path.join(project_process_protein_dir(proj), prefix, f"{prefix}_{run}")

    curp = proj.data_path()

    xmlfile = path.join(proj.data_path(), "fragmax", "process", proj.protein, prefix, prefix + "_" + run + ".xml",)
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

    #
    # Logs for data processing tools
    #

    data_proc_stats = []

    pipedreamLogs, proc_stats = _pipedream_logs()
    if proc_stats is not None:
        data_proc_stats.append(proc_stats)

    dialsreport = None
    dialsLogs, proc_stats = _dials_logs()
    if proc_stats is not None:
        dialsreport = proc_stats["report"]
        data_proc_stats.append(proc_stats)

    xdsLogs, proc_stats = _xds_logs()
    if proc_stats is not None:
        data_proc_stats.append(proc_stats)

    xdsappLogs, proc_stats = _xdsapp_logs()
    if proc_stats is not None:
        data_proc_stats.append(proc_stats)

    autoprocLogs, proc_stats = _autoproc_logs()
    if proc_stats is not None:
        data_proc_stats.append(proc_stats)

    ednaLogs, proc_stats = _edna_logs()
    if proc_stats is not None:
        data_proc_stats.append(proc_stats)

    #
    # Logs for refinement methods
    #

    # DIMPLE
    dimple_res_dirs = glob(f"{proj.data_path()}/fragmax/results/{prefix}_{run}/*/dimple")
    _dimple_logs = dict()
    for _file in dimple_res_dirs:
        proc_m = path.basename(path.dirname(_file))
        _dimple_logs[proc_m] = {path.basename(x): x for x in sorted(glob(f"{_file}/*log"))}

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
        _pipedream_logs["rhofit"] = {
            "rhofit/" + path.basename(x): x
            for x in sorted(glob(f"{pipedream_res_dirs}/rhofit/*log") + glob(f"{pipedream_res_dirs}/rhofit/*out"))
        }

    if "Apo" in prefix:
        soakTime = "Soaking not performed"
        fragConc = "-"
        solventConc = "-"

    lines = _load_results(proj, prefix, run)
    for n, line in enumerate(lines):
        if len(line) == 23:
            lines[n].append("")

    return render(
        request,
        "fragview/dataset_info.html",
        {
            "data_processing": data_proc_stats,
            "csvfile": lines,
            "shift": curp.split("/")[-1],
            "pipelines": SITE.get_supported_pipelines(),
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
            "dialsreport": dialsreport,
            "ednaLogs": ednaLogs,
            "autoprocLogs": autoprocLogs,
            "pipedreamLogs": pipedreamLogs,
            "xdsappLogs": xdsappLogs,
            "xdsLogs": xdsLogs,
            "dialsLogs": dialsLogs,
            "site": SITE,
            "beamline": SITE.get_beamline_info(),
            "dimple_logs": _dimple_logs,
            "fspipeline_logs": _fspipeline_logs,
            "pipedream_logs": _pipedream_logs,
        },
    )


def _load_results(proj, prefix, run):
    results_file = project_results_file(proj)
    if not path.exists(results_file):
        return []

    # load the whole results files
    lines = read_csv_lines(results_file)[1:]

    # return results for our dataset of interest
    return [line for line in lines if prefix + "_" + run in line[0]]


def parse_log_process(pplog):
    def split_unit_cell_vals(unit_cell):
        """
        split unit cell values into 'dim' and 'ang' parts
        """
        vals = unit_cell.split(",")
        return dict(dim=vals[:3], ang=vals[3:])

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

    if path.exists(pplog):
        with open(pplog, "r", encoding="utf-8") as r:
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
                if "Mosaicity [deg]" in line:
                    mosaicity = line.split()[-1]
                if "ISa" in line:
                    ISa = line.split()[-1]
        if "dials" in pplog or "xdsxscale" in pplog:
            for line in log:
                if "High resolution limit  " in line:
                    high_res_avg = line.split()[-3]
                    high_res_out = line.split()[-1]
                if "Low resolution limit  " in line:
                    low_res_avg = line.split()[-3]
                    low_res_out = line.split()[-1]
                if "Completeness  " in line:
                    completeness_avg = line.split()[-3]
                    completeness_out = line.split()[-1]
                if "Multiplicity  " in line:
                    multiplicity = line.split()[-3]
                if "Rmeas(I+/-) " in line:
                    rmeas_avg = line.split()[-3]
                    rmeas_out = line.split()[-1]
                if "Total unique" in line:
                    unique_rflns = line.split()[-3]
                if "Total observations" in line:
                    total_observations = line.split()[-3]
                if "Mosaic spread" in line:
                    mosaicity = line.split()[-1]
                if "I/sigma  " in line:
                    isig_avg = line.split()[-3]
                    isig_out = line.split()[-1]
                if "Space group:  " in line:
                    spg = "".join(line.split()[2:])
                if "Unit cell: " in line:
                    unit_cell = "".join(line.split()[2:])
                ISa = ""

        stats = {
            "spg": spg,
            "unique_rflns": unique_rflns,
            "total_observations": total_observations,
            "low_res_avg": low_res_avg,
            "low_res_out": low_res_out,
            "high_res_avg": high_res_avg,
            "high_res_out": high_res_out,
            "unit_cell": split_unit_cell_vals(unit_cell),
            "multiplicity": multiplicity,
            "isig_avg": isig_avg,
            "isig_out": isig_out,
            "rmeas_avg": rmeas_avg,
            "rmeas_out": rmeas_out,
            "completeness_avg": completeness_avg,
            "completeness_out": completeness_out,
            "mosaicity": mosaicity,
            "ISa": ISa,
        }
    else:
        stats = None

    return stats
