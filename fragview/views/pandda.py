import os
import csv
import natsort
import pyfastcopy  # noqa
import shutil
import threading
import json
import time
import tempfile
import subprocess
from os import path
from glob import glob
from random import randint
from datetime import datetime
from collections import Counter
from django.shortcuts import render
from fragview import hpc
from fragview.views import utils, crypt_shell
from fragview.fileio import open_proj_file, read_text_lines, read_proj_file
from fragview.projects import current_project, project_results_dir, project_script, project_process_protein_dir
from fragview.projects import project_process_dir, project_log_path, PANDDA_WORKER, project_fragments_dir
from worker.scripts import read_mtz_flags_path


def str2bool(v):
    if not type(v) == bool:
        if v.lower() in ("yes", "true", "t", "1"):
            return True
        else:
            return False
    else:
        return v


def processing_form(request):
    proj = current_project(request)

    methods = [
        x.split("/")[10]
        for x in glob(f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/*/pandda/analyses/*inspect_events*")
    ]

    return render(request, "fragview/pandda.html", {"methods": methods})


def inspect(request):
    proj = current_project(request)

    res_dir = os.path.join(project_results_dir(proj), "pandda", proj.protein)

    glob_pattern = f"{res_dir}/*/pandda/analyses/html_summaries/*inspect.html"
    proc_methods = [x.split("/")[-5] for x in glob(glob_pattern)]

    if not proc_methods:
        localcmd = f"cd {proj.data_path()}/fragmax/results/pandda/xdsapp_fspipeline/pandda/; pandda.inspect"
        return render(request, "fragview/pandda_notready.html", {"cmd": localcmd})

    filters = []

    glob_pattern = f"{res_dir}/*/pandda/analyses/pandda_inspect_events.csv"
    eventscsv = [x for x in glob(glob_pattern)]

    filterform = request.GET.get("filterForm")
    if filterform is not None:
        if ";" in filterform:
            AP, DI, FD, ED, XD, XA, BU, DP, FS = filterform.split(";")
            xdsapp = 1 if "true" in XA else 0
            autoproc = 1 if "true" in AP else 0
            dials = 1 if "true" in DI else 0
            edna = 1 if "true" in ED else 0
            fastdp = 1 if "true" in FD else 0
            xdsxscale = 1 if "true" in XD else 0
            dimple = 1 if "true" in DP else 0
            fspipeline = 1 if "true" in FS else 0
            buster = 1 if "true" in BU else 0
            filters = list()
            filters.append("autoproc") if AP == "true" else ""
            filters.append("dials") if DI == "true" else ""
            filters.append("fastdp") if FD == "true" else ""
            filters.append("EDNA_proc") if ED == "true" else ""
            filters.append("xdsapp") if XA == "true" else ""
            filters.append("xdsxscale") if XD == "true" else ""
            filters.append("dimple") if DP == "true" else ""
            filters.append("fspipeline") if FS == "true" else ""
            filters.append("buster") if BU == "true" else ""
        else:
            flat_filters = set([j for sub in [x.split("/")[10].split("_") for x in eventscsv] for j in sub])
            xdsapp = 1 if "xdsapp" in flat_filters else 0
            autoproc = 1 if "autoproc" in flat_filters else 0
            dials = 1 if "dials" in flat_filters else 0
            edna = 1 if "edna" in flat_filters else 0
            fastdp = 1 if "fastdp" in flat_filters else 0
            xdsxscale = 1 if "xdsxscale" in flat_filters else 0
            dimple = 1 if "dimple" in flat_filters else 0
            fspipeline = 1 if "fspipeline" in flat_filters else 0
            buster = 1 if "buster" in flat_filters else 0

    else:
        flat_filters = set([j for sub in [x.split("/")[10].split("_") for x in eventscsv] for j in sub])
        xdsapp = 1 if "xdsapp" in flat_filters else 0
        autoproc = 1 if "autoproc" in flat_filters else 0
        dials = 1 if "dials" in flat_filters else 0
        edna = 1 if "edna" in flat_filters else 0
        fastdp = 1 if "fastdp" in flat_filters else 0
        xdsxscale = 1 if "xdsxscale" in flat_filters else 0
        dimple = 1 if "dimple" in flat_filters else 0
        fspipeline = 1 if "fspipeline" in flat_filters else 0
        buster = 1 if "buster" in flat_filters else 0

    method = request.GET.get("methods")
    if method is None or "panddaSelect" in method or ";" in method:

        if len(eventscsv) != 0:
            if method is not None and ";" in method:
                filters = list()
                AP, DI, FD, ED, XD, XA, BU, DP, FS = method.split(";")
                filters.append("autoproc") if AP == "true" else ""
                filters.append("dials") if DI == "true" else ""
                filters.append("fastdp") if FD == "true" else ""
                filters.append("EDNA_proc") if ED == "true" else ""
                filters.append("xdsapp") if XA == "true" else ""
                filters.append("xdsxscale") if XD == "true" else ""
                filters.append("dimple") if DP == "true" else ""
                filters.append("fspipeline") if FS == "true" else ""
                filters.append("buster") if BU == "true" else ""
            allEventDict, eventDict, low_conf, medium_conf, high_conf = pandda_events(proj, filters)

            sitesL = list()
            for k, v in eventDict.items():
                sitesL += [k1 for k1, v1 in v.items()]

            siteN = Counter(sitesL)
            ligEvents = sum(siteN.values())
            siteP = dict()
            for k, v in natsort.natsorted(siteN.items()):
                siteP[k] = 100 * v / ligEvents

            totalEvents = high_conf + medium_conf + low_conf
            uniqueEvents = str(len(allEventDict.items()))

            with open(os.path.join(project_process_protein_dir(proj), "panddainspects.csv"), "w") as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(["dataset", "site_idx", "event_idx", "proc_method", "ddtag", "run", "bdc"])
                for k, v in natsort.natsorted(eventDict.items()):
                    for k1, v1 in v.items():
                        dataset = k
                        site_idx = k1.split("_")[0]
                        event_idx = k1.split("_")[1]
                        proc_method = "_".join(v1[0].split("_")[0:2])
                        ddtag = v1[0].split("_")[2]
                        run = v1[0].split("_")[-1]
                        bdc = v1[1]
                        writer.writerow([dataset, site_idx, event_idx, proc_method, ddtag, run, bdc])

            html = ""
            # HTML Head
            html += "    <!DOCTYPE html>\n"
            html += '    <html lang="en">\n'
            html += "      <head>\n"
            html += '        <meta charset="utf-8">\n'
            html += '        <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            html += (
                '        <link rel="stylesheet" '
                'href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css">\n'
            )
            html += (
                '        <link rel="stylesheet" '
                'href="https://cdn.datatables.net/1.10.11/css/dataTables.bootstrap.min.css">\n'
            )
            html += '        <script src="https://code.jquery.com/jquery-1.12.0.min.js"></script>\n'
            html += '        <script src="https://cdn.datatables.net/1.10.11/js/jquery.dataTables.min.js"></script>\n'
            html += (
                "        <script "
                'src="https://cdn.datatables.net/1.10.11/js/dataTables.bootstrap.min.js"></script>\n'
            )
            html += '          <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>\n'
            html += '          <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>\n'
            html += '        <script type="text/javascript" class="init">\n'
            html += "    $(document).ready(function() {\n"
            html += "        $('#main-table').DataTable();\n"
            html += "    } );\n"
            html += "        </script>   \n"
            html += "    <title>PANDDA Inspect Summary</title>\n"
            html += "</head>\n"
            html += "<body>\n"
            html += '    <div class="container">\n'
            html += "      <h1>Consensus of PANDDA Inspect Summaries " + "_".join(filters) + "</h1>\n"
            html += "      <h2>Summary of Inspection of Datasets</h2>\n"
            html += "      \n"

            # Styles CSS
            html += "<style>\n"
            html += "    .container {\n"
            html += "        max-width: 100% !important;\n"
            html += "        margin: 0 50px 50px 150px !important;\n"
            html += "        width: calc(100% - 200px) !important;\n"
            html += "    }\n"
            html += "    .col-md-8 {\n"
            html += "    width: 100% !important;\n"
            html += "    }\n"
            html += "    </style>\n"

            # Fitting process plot (necessary?)
            html += '      <div class="row">\n'
            html += '        <div class="col-xs-12">\n'
            html += "          <p>Fitting Progress</p>\n"
            html += '          <div class="progress">\n'
            html += '            <div class="progress-bar progress-bar-success" style="width:100%">\n'
            html += '              <span class="sr-only">Fitted - ' + str(ligEvents) + " Events</span>\n"
            html += "              <strong>Fitted - " + str(ligEvents) + " Events (100%)</strong>\n"
            html += "            </div>\n"
            html += '            <div class="progress-bar progress-bar-warning" style="width:0.0%">\n'
            html += '              <span class="sr-only">Unviewed - 0 Events</span>\n'
            html += "              <strong>Unviewed - 0 Events (0%)</strong>\n"
            html += "            </div>\n"
            html += '            <div class="progress-bar progress-bar-danger" style="width:0.0%">\n'
            html += '              <span class="sr-only">No Ligand Fitted - 10 Events</span>\n'
            html += "              <strong>No Ligand Fitted - 10 Events (16%)</strong>\n"
            html += "            </div>\n"
            html += "            </div>\n"
            html += "        </div>\n"

            # Site distribution plot
            html += '        <div class="col-xs-12">\n'
            html += "          <p>Identified Ligands by Site</p>\n"
            html += '          <div class="progress">\n'
            colour = "progress-bar-info"
            for k, v1 in siteP.items():

                v = siteN[k]
                html += '            <div class="progress-bar ' + colour + '" style="width:' + str(siteP[k]) + '%">\n'
                html += '              <span class="sr-only">S' + k + ": " + str(v) + " hits</span>\n"
                html += (
                    "              <strong>S" + k + ": " + str(v) + " hits (" + str(int(siteP[k])) + "%)</strong>\n"
                )
                html += "            </div>\n"
                if colour == "progress-bar-info":
                    colour = "progress-bar-default"
                else:
                    colour = "progress-bar-info"

            # Inspections facts

            html += "            </div>\n"
            html += "        </div>\n"
            html += "        </div>\n"
            html += "      \n"
            html += "      \n"
            html += '      <div class="row">\n'
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert">'
                "<strong>Datasets w. ligands: " + str(ligEvents) + " (of #dataset collected)</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert">'
                "<strong>Sites w. ligands: " + str(len(siteP)) + " (of 10)</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-info" role="alert">'
                "<strong>Unique fragments: " + uniqueEvents + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-info" role="alert">'
                "<strong>Total number of events: " + str(totalEvents) + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-success" role="alert">'
                "<strong>High confidence hits:   " + str(high_conf) + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-warning" role="alert">'
                "<strong>Medium confidence hits: " + str(medium_conf) + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-danger" role="alert">'
                "<strong>Low confidence hits:    " + str(low_conf) + "</strong></div></div>\n"
            )
            html += "        </div>\n"
            html += "      \n"
            html += "      \n"
            html += '      <div class="row">\n'
            html += "        </div>\n"
            html += "<hr>\n"

            # Table header
            html += '<div class="table-responsive">\n'
            html += '<table id="main-table" class="table table-bordered table-striped" data-page-length="50">\n'
            html += "    <thead>\n"
            html += "    <tr>\n"
            html += '        <th class="text-nowrap"></th>\n'

            html += '        <th class="text-nowrap">Dataset</th>\n'
            html += '        <th class="text-nowrap">Method</th>\n'
            html += '        <th class="text-nowrap">Event</th>\n'
            html += '        <th class="text-nowrap">Site</th>\n'
            html += '        <th class="text-nowrap">1 - BDC</th>\n'
            html += '        <th class="text-nowrap">Z-Peak</th>\n'
            html += '        <th class="text-nowrap">Map Res.</th>\n'
            html += '        <th class="text-nowrap">Map Unc.</th>\n'
            html += '        <th class="text-nowrap">Confidence</th>\n'
            html += '        <th class="text-nowrap">Comment</th>\n'
            html += '        <th class="text-nowrap"></th>\n'
            html += "        </tr>\n"
            html += "    </thead>\n"

            # Table body
            html += "<tbody>\n"

            for k, v in natsort.natsorted(eventDict.items()):
                for k1, v1 in v.items():
                    detailsDict = dataset_details(proj, k, k1, v1[0][:-4])

                    dataset = k
                    site_idx = k1.split("_")[0]
                    event_idx = k1.split("_")[1]
                    proc_method = "_".join(v1[0].split("_")[0:2])
                    ddtag = v1[0].split("_")[2]
                    run = v1[0].split("_")[-1]

                    ds = dataset + ";" + site_idx + ";" + event_idx + ";" + proc_method + ";" + ddtag + ";" + run

                    if (
                        detailsDict["viewed"] == "False\n"
                        or detailsDict["ligplaced"] == "False"
                        or detailsDict["interesting"] == "False"
                    ):
                        html += "        <tr class=info>\n"
                    else:
                        html += "        <tr class=success>\n"

                    html += (
                        '          <th class="text-nowrap" scope="row" style="text-align: center;">'
                        '<form action="/pandda_densityC/" method="get" id="pandda_form" target="_blank">'
                        '<button class="btn" type="submit" value="' + ds + '" name="structure" size="1">'
                        "Open</button></form></th>\n"
                    )
                    html += '          <th class="text-nowrap" scope="row">' + k + v1[0][-3:] + "</th>\n"
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span>'
                        + v1[0][:-4]
                        + "</td>\n"
                    )

                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["event_idx"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["site_idx"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["bdc"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["z_peak"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["map_res"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["map_unc"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["ligconfid"]
                        + "</td>\n"
                    )
                    html += (
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '
                        + detailsDict["comment"]
                        + "</td>\n"
                    )
                    html += '          <td><span class="label label-success">Hit</span></td></tr>\n'
            html += "\n"
            html += "</tbody>\n"
            html += "</table>\n"
            html += "</div>\n"
            html += "\n"
            html += "</body>\n"
            html += "</html>\n"

            return render(
                request,
                "fragview/pandda_inspect.html",
                {
                    "proc_methods": proc_methods,
                    "Report": html,
                    "xdsapp": xdsapp,
                    "autoproc": autoproc,
                    "dials": dials,
                    "edna": edna,
                    "fastdp": fastdp,
                    "xdsxscale": xdsxscale,
                    "dimple": dimple,
                    "fspipeline": fspipeline,
                    "buster": buster,
                },
            )

    else:
        inspect_file = os.path.join(res_dir, method, "pandda", "analyses", "html_summaries", "pandda_inspect.html")

        if os.path.exists(inspect_file):
            with open(inspect_file, "r") as inp:
                inspectfile = inp.readlines()
                html = ""
                for n, line in enumerate(inspectfile):
                    if '<th class="text-nowrap" scope="row">' in line:

                        event = inspectfile[n + 4].split("/span>")[-1].split("</td>")[0].replace(" ", "")
                        site = inspectfile[n + 5].split("/span>")[-1].split("</td>")[0].replace(" ", "")
                        ds = method + ";" + line.split('row">')[-1].split("</th")[0] + ";" + event + ";" + site

                        html += (
                            '<td><form action="/pandda_density/" method="get" id="pandda_form" target="_blank">'
                            '<button class="btn" type="submit" value="' + ds + ';stay" name="structure" size="1">'
                            "Open</button></form>"
                        )
                        html += line
                    else:
                        html += line

                html = "".join(html)
                html = html.replace(
                    '<th class="text-nowrap">Dataset</th>',
                    '<th class="text-nowrap">Open</th><th class="text-nowrap">Dataset</th>',
                )
                flat_filters = method.split("_")
                xdsapp = 1 if "xdsapp" in flat_filters else 0
                autoproc = 1 if "autoproc" in flat_filters else 0
                dials = 1 if "dials" in flat_filters else 0
                edna = 1 if "edna" in flat_filters else 0
                fastdp = 1 if "fastdp" in flat_filters else 0
                xdsxscale = 1 if "xdsxscale" in flat_filters else 0
                dimple = 1 if "dimple" in flat_filters else 0
                fspipeline = 1 if "fspipeline" in flat_filters else 0
                buster = 1 if "buster" in flat_filters else 0

                return render(
                    request,
                    "fragview/pandda_inspect.html",
                    {
                        "proc_methods": proc_methods,
                        "Report": html.replace("PANDDA Inspect Summary", "PANDDA Inspect Summary for " + method),
                        "xdsapp": xdsapp,
                        "autoproc": autoproc,
                        "dials": dials,
                        "edna": edna,
                        "fastdp": fastdp,
                        "xdsxscale": xdsxscale,
                        "dimple": dimple,
                        "fspipeline": fspipeline,
                        "buster": buster,
                    },
                )
        else:
            return render(
                request,
                "fragview/pandda.html",
                {
                    "proc_methods": proc_methods,
                    "xdsapp": 0,
                    "autoproc": 0,
                    "dials": 0,
                    "edna": 0,
                    "fastdp": 0,
                    "xdsxscale": 0,
                    "dimple": 0,
                    "fspipeline": 0,
                    "buster": 0,
                },
            )


def pandda_events(proj, filters):
    eventscsv = glob(f"{project_results_dir(proj)}/pandda/{proj.protein}/*/pandda/analyses/pandda_inspect_events.csv")

    if len(filters) != 0:
        eventscsv = [x for x in eventscsv if any(xs in x for xs in filters)]
    eventDict = dict()
    allEventDict = dict()

    high_conf = 0
    medium_conf = 0
    low_conf = 0

    for eventcsv in eventscsv:
        method = eventcsv.split("/")[10]
        with open(eventcsv, "r") as inp:
            a = inp.readlines()
        a = [x.split(",") for x in a]
        headers = a[0]
        for line in a:

            if line[headers.index("Ligand Placed")] == "True":

                dtag = line[0][:-3]
                event_idx = line[1]
                site_idx = line[11]
                bdc = line[2]
                intersting = line[headers.index("Ligand Confidence")]
                if intersting == "High":
                    high_conf += 1
                if intersting == "Medium":
                    medium_conf += 1
                if intersting == "Low":
                    low_conf += 1

                if dtag not in eventDict:

                    eventDict[dtag] = {site_idx + "_" + event_idx: {method + "_" + line[0][-3:]: bdc}}
                    allEventDict[dtag] = {site_idx + "_" + event_idx: {method + "_" + line[0][-3:]: bdc}}
                else:

                    if site_idx not in eventDict[dtag]:
                        eventDict[dtag].update({site_idx + "_" + event_idx: {method + "_" + line[0][-3:]: bdc}})
                        allEventDict[dtag].update({site_idx + "_" + event_idx: {method + "_" + line[0][-3]: bdc}})
                    else:
                        eventDict[dtag][site_idx + "_" + event_idx].update({method + "_" + line[0][-3:]: bdc})
                        allEventDict[dtag][site_idx + "_" + event_idx].update({method + "_" + line[0][-3:]: bdc})

    for k, v in eventDict.items():
        for k1, v1 in v.items():
            v[k1] = sorted(v1.items(), key=lambda t: t[1])[0]
    return allEventDict, eventDict, low_conf, medium_conf, high_conf


def dataset_details(proj, dataset, site_idx, method):
    detailsDict = dict()

    events_csv = os.path.join(
        project_results_dir(proj), "pandda", proj.protein, method, "pandda", "analyses", "pandda_inspect_events.csv"
    )

    with open(events_csv, "r") as inp:
        a = inp.readlines()

    for i in a:
        if dataset in i:
            if i.split(",")[11] + "_" + i.split(",")[1] == site_idx:
                k = i.split(",")

    headers = a[0].split(",")
    detailsDict["event_idx"] = k[1]
    detailsDict["bdc"] = k[2]
    detailsDict["site_idx"] = k[11]
    detailsDict["center"] = "[" + k[12] + "," + k[13] + "," + k[14] + "]"
    detailsDict["z_peak"] = k[16]
    detailsDict["resolution"] = k[18]
    detailsDict["rfree"] = k[20]
    detailsDict["rwork"] = k[21]
    detailsDict["spg"] = k[35]
    detailsDict["map_res"] = k[headers.index("analysed_resolution")]
    detailsDict["map_unc"] = k[headers.index("map_uncertainty")]
    detailsDict["analysed"] = k[headers.index("analysed")]
    detailsDict["interesting"] = k[headers.index("Interesting")]
    detailsDict["ligplaced"] = k[headers.index("Ligand Placed")]
    detailsDict["ligconfid"] = k[headers.index("Ligand Confidence")]
    detailsDict["comment"] = k[headers.index("Comment")]
    detailsDict["viewed"] = k[headers.index("Viewed\n")]

    return detailsDict


def giant(request):
    proj = current_project(request)

    available_scores = glob(
        f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/*/pandda-scores/residue_scores.html"
    )

    if not available_scores:
        # no panda scores files found
        return render(request, "fragview/pandda_notready.html")
    else:
        scoreDict = dict()
        for score in available_scores:
            with open(score, "r") as readFile:
                htmlcontent = "".join(readFile.readlines())

            htmlcontent = htmlcontent.replace(
                'src="./residue_plots', 'src="/static/' + "/".join(score.split("/")[3:-1]) + "/residue_plots"
            )
            scoreDict[score.split("/")[-3]] = htmlcontent

        return render(request, "fragview/pandda_export.html", {"scores_plots": scoreDict})


def analyse(request):
    proj = current_project(request)
    panda_results_path = os.path.join(proj.data_path(), "fragmax", "results", "pandda", proj.protein)

    fixsl = request.GET.get("fixsymlinks")
    if fixsl is not None and "FixSymlinks" in fixsl:
        t1 = threading.Thread(target=fix_pandda_symlinks, args=(proj,))
        t1.daemon = True
        t1.start()

    proc_methods = [x.split("/")[-2] for x in glob(panda_results_path + "/*/pandda")]
    newest = datetime.strptime("2000-01-01-1234", "%Y-%m-%d-%H%M")
    newestpath = ""
    newestmethod = ""
    for methods in proc_methods:
        if len(glob(panda_results_path + "/" + methods + "/pandda/analyses-*")) > 0:
            last = sorted(glob(panda_results_path + "/" + methods + "/pandda/analyses-*"))[-1]
            last_path = last + "/html_summaries/"
            if os.path.exists(last_path + "pandda_initial.html") or os.path.exists(last_path + "pandda_analsyse.html"):
                cur_time = datetime.strptime(last.split("analyses-")[-1], "%Y-%m-%d-%H%M")
                if cur_time > newest:
                    newest = cur_time
                    newestpath = last
                    newestmethod = methods

    method = request.GET.get("methods")

    if method is None or "panddaSelect" in method:
        if os.path.exists(newestpath + "/html_summaries/pandda_analyse.html"):
            with open(newestpath + "/html_summaries/pandda_analyse.html", "r", encoding="utf-8") as inp:
                pandda_html = inp.readlines()
                localcmd = panda_results_path + "/" + newestmethod + "/pandda/; pandda.inspect"

            for n, line in enumerate(pandda_html):
                if '<th class="text-nowrap" scope="row">' in line:
                    dt = line.split('scope="row">')[-1].split("<")[0]
                    pandda_html[n] = (
                        f'<td class="sorting_1" style="text-align: center;" >'
                        f'<form action="/pandda_densityA/" method="get" id="pandda_form" '
                        f'target="_blank"><button class="btn" type="submit" '
                        f'value="{newestmethod};{dt};1;1;stay" '
                        f'name="structure" size="1">Open</button></form></td>' + line
                    )
            pandda_html = "".join(pandda_html)
            pandda_html = pandda_html.replace(
                '<th class="text-nowrap">Dataset</th>',
                '<th class="text-nowrap">Open</th><th class="text-nowrap">Dataset</th>',
            )
            pandda_html = pandda_html.replace(
                'class="table table-bordered table-striped"',
                'class="table table-bordered table-striped" data-page-length="50"',
            )
            pandda_html = pandda_html.replace(
                "PANDDA Processing Output", "PANDDA Processing Output for " + newestmethod
            )
            return render(
                request,
                "fragview/pandda_analyse.html",
                {
                    "opencmd": localcmd,
                    "pandda_res": os.path.dirname(os.path.dirname(localcmd)),
                    "proc_methods": proc_methods,
                    "Report": pandda_html,
                },
            )
        elif os.path.exists(newestpath + "/html_summaries/pandda_initial.html"):
            with open(newestpath + "/html_summaries/pandda_initial.html", "r", encoding="utf-8") as inp:
                a = "".join(inp.readlines())
                localcmd = "initial"

                return render(
                    request,
                    "fragview/pandda_analyse.html",
                    {
                        "opencmd": localcmd,
                        "pandda_res": os.path.dirname(os.path.dirname(localcmd)),
                        "proc_methods": proc_methods,
                        "Report": a.replace(
                            "PANDDA Processing Output", "PANDDA Processing Output for " + newestmethod
                        ),
                    },
                )

        else:
            running = [x.split("/")[10] for x in glob(panda_results_path + "/*/pandda/*running*")]
            return render(request, "fragview/pandda_notready.html", {"Report": "<br>".join(running)})

    else:
        if os.path.exists(panda_results_path + "/" + method + "/pandda/analyses/html_summaries/pandda_analyse.html"):
            with open(
                panda_results_path + "/" + method + "/pandda/analyses/html_summaries/pandda_analyse.html",
                "r",
                encoding="utf-8",
            ) as inp:
                pandda_html = inp.readlines()
                localcmd = panda_results_path + "/" + newestmethod + "/pandda/; pandda.inspect"

            for n, line in enumerate(pandda_html):
                if '<th class="text-nowrap" scope="row">' in line:
                    dt = line.split('scope="row">')[-1].split("<")[0]
                    pandda_html[n] = (
                        f'<td class="sorting_1" style="text-align: center;" >'
                        f'<form action="/pandda_densityA/" method="get" id="pandda_form" '
                        f'target="_blank"><button class="btn" type="submit" '
                        f'value="{method};{dt};1;1;stay" '
                        f'name="structure" size="1">Open</button></form></td>' + line
                    )
            pandda_html = "".join(pandda_html)
            pandda_html = pandda_html.replace(
                '<th class="text-nowrap">Dataset</th>',
                '<th class="text-nowrap">Open</th><th class="text-nowrap">Dataset</th>',
            )
            pandda_html = pandda_html.replace("PANDDA Processing Output", "PANDDA Processing Output for " + method)
            return render(
                request,
                "fragview/pandda_analyse.html",
                {
                    "opencmd": localcmd,
                    "pandda_res": os.path.dirname(os.path.dirname(localcmd)),
                    "proc_methods": proc_methods,
                    "Report": pandda_html,
                },
            )
        else:
            running = [x.split("/")[9] for x in glob(panda_results_path + "/*/pandda/*running*")]
            return render(request, "fragview/pandda_notready.html", {"Report": "<br>".join(running)})


def fix_pandda_symlinks(proj):
    os.system("chmod -R 777 " + proj.data_path() + "/fragmax/results/pandda/")

    subprocess.call(
        "cd "
        + proj.data_path()
        + "/fragmax/results/pandda/"
        + proj.protein
        + """/ ; find -type l -iname *-pandda-input.* -exec bash -c 'ln -f "$(readlink -m "$0")" "$0"' {} \;""",  # noqa
        shell=True,
    )

    subprocess.call(
        "cd "
        + proj.data_path()
        + "/fragmax/results/pandda/"
        + proj.protein
        + """/ ; find -type l -iname *pandda-model.pdb -exec bash -c 'ln -f "$(readlink -m "$0")" "$0"' {} \;""",  # noqa
        shell=True,
    )

    subprocess.call(
        proj.data_path() + "/fragmax/results/pandda/" + proj.protein + """/ ; chmod -R 770 .""", shell=True
    )

    glob_pattern = (
        f"{project_results_dir(proj)}/pandda/{proj.protein}/*/pandda/"
        f"processed_datasets/*/modelled_structures/*pandda-model.pdb"
    )
    linksFolder = glob(glob_pattern)

    for dst in linksFolder:
        folder = "/".join(dst.split("/")[:-1]) + "/"
        pdbs = os.listdir(folder)
        src = folder + sorted([x for x in pdbs if "fitted" in x])[-1]
        os.remove(dst)
        shutil.copyfile(src, dst)


def submit(request):
    proj = current_project(request)

    panddaCMD = str(request.GET.get("panddaform"))
    giantCMD = str(request.GET.get("giantform"))

    if "giantscore" in giantCMD:
        function, method = giantCMD.split(";")
        t2 = threading.Thread(target=giant_score, args=(proj, method))
        t2.daemon = True
        t2.start()
        return render(request, "fragview/jobs_submitted.html", {"command": giantCMD})

    if "analyse" in panddaCMD:
        (
            function,
            proc,
            ref,
            complete,
            use_apo,
            use_dmso,
            reproZmaps,
            use_CAD,
            ref_CAD,
            ign_errordts,
            keepup_last,
            ign_symlink,
            PanDDAfilter,
            min_dataset,
            customPanDDA,
            cifMethod,
        ) = panddaCMD.split(";")

        method = proc + "_" + ref

        if PanDDAfilter == "null":
            useSelected = False
        else:
            useSelected = True

        if min_dataset.isnumeric():
            min_dataset = int(min_dataset)
        else:
            min_dataset = 40

        options = {
            "method": method,
            "useApos": str2bool(use_apo),
            "useSelected": useSelected,
            "reprocessZmap": str2bool(reproZmaps),
            "initpass": True,
            "min_datasets": min_dataset,
            "rerun_state": False,
            "complete_results": str2bool(complete),
            "dtsfilter": PanDDAfilter,
            "customPanDDA": customPanDDA,
            "reprocessing": False,
            "reprocessing_mode": "reload",
            "nproc": 32,
        }

        res_dir = os.path.join(project_results_dir(proj), "pandda", proj.protein, method)
        res_pandda = os.path.join(res_dir, "pandda")
        if not options["reprocessing"] and path.exists(res_pandda):
            shutil.rmtree(res_pandda)

        if options["reprocessing"] and path.exists(res_dir):
            shutil.rmtree(res_dir)

        methodshort = proc[:2] + ref[:2]
        if methodshort == "bebe":
            methodshort = "best"
        _write_main_script(proj, method, methodshort, options)

        t1 = threading.Thread(target=pandda_worker, args=(proj, method, options, cifMethod))
        t1.daemon = True
        t1.start()

        return render(request, "fragview/jobs_submitted.html", {"command": panddaCMD})


def _write_main_script(proj, method, methodshort, options):
    script = project_script(proj, f"panddaRUN_{proj.protein}{method}.sh")

    epoch = round(time.time())
    log_prefix = project_log_path(proj, f"{proj.protein}PanDDA_{method}_{epoch}_%j_")
    data_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method)

    pandda_script = project_script(proj, PANDDA_WORKER)
    pandda_method_dir = f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/{method}"

    if proj.encrypted:
        body = f"""#!/bin/bash
#!/bin/bash
#SBATCH -t 99:00:00
#SBATCH -J PDD{methodshort}
#SBATCH --exclusive
#SBATCH -N1
#SBATCH -p fujitsu
#SBATCH --cpus-per-task=64
#SBATCH --mem=310G
#SBATCH -o {log_prefix}out.txt
#SBATCH -e {log_prefix}err.txt

{crypt_shell.crypt_cmd(proj)}

WORK_DIR=$(mktemp -d)
cd $WORK_DIR

{crypt_shell.fetch_dir(proj, data_dir, ".")}

module add CCP4/7.0.077-SHELX-ARP-8.0-0a-PReSTO PyMOL
python {pandda_script} $WORK_DIR {proj.protein} "{options}"

{crypt_shell.upload_dir(proj, '$WORK_DIR/pandda', data_dir + '/pandda')}
rm -rf "$WORK_DIR"
"""
    else:
        body = f"""#!/bin/bash
#!/bin/bash
#SBATCH -t 99:00:00
#SBATCH -J PDD{methodshort}
#SBATCH --exclusive
#SBATCH -N1
#SBATCH -p fujitsu
#SBATCH --cpus-per-task=64
#SBATCH --mem=310G
#SBATCH -o {log_prefix}out.txt
#SBATCH -e {log_prefix}err.txt

cd {pandda_method_dir}
module purge
module add CCP4/7.0.077-SHELX-ARP-8.0-0a-PReSTO PyMOL
python {pandda_script} {pandda_method_dir} {proj.protein} "{options}"
"""
    utils.write_script(script, body)


def giant_score(proj, method):
    res_dir = os.path.join(project_results_dir(proj), "pandda", proj.protein, method)
    pandda_dir = os.path.join(res_dir, "pandda")
    export_dir = os.path.join(res_dir, "pandda-export")

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 00:05:00\n"""
    header += """#SBATCH -J GiantScore\n"""
    header += """#SBATCH --nice=25\n"""
    header += """#SBATCH --cpus-per-task=1\n"""
    header += """#SBATCH --mem=2500\n"""
    header += """sleep 15000\n"""

    script = project_script(proj, "giant_holder.sh")
    utils.write_script(script, header)
    hpc.run_sbatch(script)

    rn = str(randint(10000, 99999))
    jname = "Gnt" + rn
    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 02:00:00\n"""
    header += """#SBATCH -J """ + jname + """\n"""
    header += """#SBATCH --nice=25\n"""
    header += """#SBATCH --cpus-per-task=2\n"""
    header += """#SBATCH --mem=5000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pandda_export_%j.out\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pandda_export_%j.err\n\n"""
    header += """module purge\n"""
    header += """module load CCP4 Phenix\n"""

    panddaExport = f"pandda.export pandda_dir='{pandda_dir}' export_dir='{export_dir}'"

    export_script = project_script(proj, "pandda-export.sh")
    utils.write_script(export_script, header + panddaExport)
    hpc.frontend_run(export_script)

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 02:00:00\n"""
    header += """#SBATCH -J """ + jname + """\n"""
    header += """#SBATCH --nice=25\n"""
    header += """#SBATCH --cpus-per-task=1\n"""
    header += """#SBATCH --mem=2500\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pandda_giant_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pandda_giant_%j_err.txt\n\n"""
    header += """module purge\n"""
    header += """module load CCP4 Phenix\n"""

    _dirs = glob(f"{export_dir}/*")

    line = "#! /bin/bash"
    line += f"\njid1=$(sbatch {export_script})"
    line += "\njid1=`echo $jid1|cut -d ' ' -f4`"

    for _dir in _dirs:
        dataset = _dir.split("/")[-1]

        src = os.path.join(res_dir, dataset, "final_original.mtz")
        dst = os.path.join(export_dir, dataset, f"{dataset}-pandda-input.mtz")

        cpcmd3 = "cp -f " + src + " " + dst
        make_restraints = ""
        quick_refine = ""
        frag = ""
        if "Apo" not in _dir:
            try:
                ens = glob(_dir + "/*ensemble*.pdb")[0]
                make_restraints = "giant.make_restraints " + ens + " all=True resname=XXX"
                inp_mtz = ens.replace("-ensemble-model.pdb", "-pandda-input.mtz")
                frag = _dir.split("/")[-1].split("-")[-1].split("_")[0]
                quick_refine = (
                    "giant.quick_refine "
                    + ens
                    + " "
                    + inp_mtz
                    + " "
                    + frag
                    + ".cif multi-state-restraints.refmac.params resname=XXX"
                )
            except Exception:
                make_restraints = ""
                quick_refine = ""
        script = project_script(proj, f"giant_pandda_{frag}.sh")
        utils.write_script(script, f"{header}\n" f"cd {_dir}\n{cpcmd3}\n{make_restraints}\n{quick_refine}")

        line += "\nsbatch  --dependency=afterany:$jid1 " + script
        line += "\nsleep 0.05"

    pandda_score_script = project_script(proj, "pandda-score.sh")
    giant_worker_script = project_script(proj, "giant_worker.sh")

    utils.write_script(
        giant_worker_script, f"{line}\n\n" f"sbatch --dependency=singleton --job-name={jname} {pandda_score_script}"
    )

    header = """#!/bin/bash\n"""
    header += """#!/bin/bash\n"""
    header += """#SBATCH -t 02:00:00\n"""
    header += """#SBATCH -J """ + jname + """\n"""
    header += """#SBATCH --nice=25\n"""
    header += """#SBATCH --cpus-per-task=2\n"""
    header += """#SBATCH --mem=2000\n"""
    header += """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/pandda_score_%j_out.txt\n"""
    header += """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/pandda_score_%j_err.txt\nn"""
    header += """module purge\n"""
    header += """module load CCP4 Phenix\n\n"""

    scores_dir = os.path.join(res_dir, "pandda-scores")
    scoreModel = f'giant.score_model_multiple out_dir="{scores_dir}" {export_dir}/* res_names="XXX" cpu=24'

    body = ""
    for _dir in _dirs:
        dataset = _dir.split("/")[-1]

        src = path.join(res_dir, dataset, "final_original.mtz")
        dst = path.join(export_dir, dataset, f"{dataset}-pandda-input.mtz")

        body += "\ncp -f " + src + " " + dst

    scorecmd = (
        f"\necho 'source $HOME/Apps/CCP4/ccp4-7.0/bin/ccp4.setup-sh;{scoreModel}' | ssh -F ~/.ssh/ w-guslim-cc-0"
    )

    utils.write_script(pandda_score_script, f"{header}{body}{scorecmd}")

    hpc.frontend_run(giant_worker_script)


def pandda_worker(proj, method, options, cifMethod):
    rn = str(randint(10000, 99999))

    fragDict = dict()

    for _dir in glob(f"{project_process_dir(proj)}/fragment/{proj.library.name}/*"):
        fragDict[_dir.split("/")[-1]] = _dir

    if "best" in method:
        print("FragMAXapp will select best datasets")

        selectedDict = {
            x.split("/")[-4]: x
            for x in sorted(glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/*/final.pdb"))
        }
        for dataset in selectedDict.keys():
            selectedDict[dataset] = get_best_alt_dataset(proj, dataset, options)
    else:
        method_dir = method.replace("_", "/")
        datasetList = set(
            [x.split("/")[-4] for x in glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*" f"/*/*/final.pdb")]
        )
        selectedDict = {
            x.split("/")[-4]: x
            for x in sorted(glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/{method_dir}/*/final.pdb"))
        }
        missingDict = set(datasetList) - set(selectedDict)

        for dataset in missingDict:
            selectedDict[dataset] = get_best_alt_dataset(proj, dataset, options)

    for dataset, pdb in selectedDict.items():
        if "buster" in pdb:
            pdb = pdb.replace("final.pdb", "refine.pdb")

        if path.exists(pdb):
            hklin = pdb.replace(".pdb", ".mtz")
            resHigh, freeRflag, fsigf_Flag = _read_mtz_file(proj, hklin)
            script = _write_prepare_script(proj, rn, method, dataset, pdb, resHigh, freeRflag, fsigf_Flag, cifMethod)

            hpc.run_sbatch(script)
            # os.remove(script)

    pandda_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method)
    os.makedirs(pandda_dir, exist_ok=True)

    with open_proj_file(proj, path.join(pandda_dir, "selection.json")) as f:
        json_str = json.dumps(selectedDict)
        f.write(json_str.encode())

    script = project_script(proj, f"panddaRUN_{proj.protein}{method}.sh")
    hpc.run_sbatch(script, f"--dependency=singleton --job-name=PnD{rn}")
    # os.remove(script)


def _write_prepare_script(proj, rn, method, dataset, pdb, resHigh, freeRflag, fsigf_Flag, cifMethod):
    mtz = path.join(path.dirname(pdb), "final.mtz")
    fset = dataset.split("-")[-1]
    epoch = round(time.time())
    output_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method, dataset)
    script = f"pandda_prepare_{proj.protein}{fset}.sh"
    lib = proj.library

    copy_frags_cmd = ""

    if "Apo" not in dataset:
        fragments_path = project_fragments_dir(proj)
        frag = dataset.split("-")[-1].split("_")[0]
        frag_cif = path.join(fragments_path, f"{frag}.cif")
        frag_pdb = path.join(fragments_path, f"{frag}.pdb")
        smiles = lib.get_fragment(frag).smiles
        if cifMethod == "elbow":
            cif_cmd = f"phenix.elbow --smiles='{smiles}' --output=$WORK_DIR/{frag}\n"
            clear_tmp_cmd = ""
        elif cifMethod == "acedrg":
            cif_cmd = f"acedrg -i '{smiles}' -o $WORK_DIR/{frag}\n"
            clear_tmp_cmd = f"rm -rf $WORK_DIR/{frag}_TMP/\n"
        elif cifMethod == "grade":
            cif_cmd = f"grade '{smiles}' -ocif $WORK_DIR/{frag}.cif -opdb $WORK_DIR/{frag}.pdb -nomogul\n"
        copy_frags_cmd = cif_cmd + "\n" + clear_tmp_cmd
        if path.exists(f"{os.path.join(fragments_path, frag_cif)}") and False:
            copy_frags_cmd = f"cp {frag_cif} $WORK_DIR\ncp {frag_pdb} $WORK_DIR"

    body = f"""#!/bin/bash
#!/bin/bash
#SBATCH -t 00:15:00
#SBATCH -J PnD{rn}
#SBATCH --nice=25
#SBATCH --cpus-per-task=1
#SBATCH --mem=2500
#SBATCH -o {proj.data_path()}/fragmax/logs/{fset}_PanDDA_{epoch}_%j_out.txt
#SBATCH -e {proj.data_path()}/fragmax/logs/{fset}_PanDDA_{epoch}_%j_err.txt
module purge
module load Phenix CCP4 BUSTER/20190607-3-PReSTO

{crypt_shell.crypt_cmd(proj)}

DEST_DIR="{output_dir}"
WORK_DIR=$(mktemp -d)
cd $WORK_DIR

{crypt_shell.fetch_file(proj, pdb, "final.pdb")}
{crypt_shell.fetch_file(proj, mtz, "final.mtz")}

module purge
module load CCP4 Phenix

echo -e " monitor BRIEF\\n labin file 1 -\\n  ALL\\n resolution file 1 999.0 {resHigh}" | \\
    cad hklin1 final.mtz hklout final.mtz

uniqueify -f {freeRflag} final.mtz final.mtz

echo -e "COMPLETE FREE={freeRflag} \\nEND" | \\
    freerflag hklin final.mtz hklout final_rfill.mtz

phenix.maps final_rfill.mtz final.pdb maps.input.reflection_data.labels='{fsigf_Flag}'
mv final.mtz final_original.mtz
mv final_map_coeffs.mtz final.mtz

{copy_frags_cmd}

mkdir -p $DEST_DIR
{crypt_shell.upload_dir(proj, '$WORK_DIR', output_dir)}

rm -rf $WORK_DIR
"""

    script = project_script(proj, script)
    utils.write_script(script, body)

    return script


def _read_mtz_file(proj, mtz_file):
    with tempfile.NamedTemporaryFile(suffix=".mtz", delete=False) as f:
        temp_name = f.name
        f.write(read_proj_file(proj, mtz_file))

    stdout = subprocess.run(["mtzdmp", temp_name], stdout=subprocess.PIPE).stdout

    for i in stdout.decode().splitlines():
        if "A )" in i:
            resHigh = i.split()[-3]
        if "free" in i.lower() and "flag" in i.lower():
            freeRflag = i.split()[-1]

    stdout = subprocess.run([read_mtz_flags_path(), temp_name], stdout=subprocess.PIPE).stdout
    fsigf_Flag = stdout.decode("utf-8").split()[1].split(":")[-1]

    # make sure unencrypted MTZ is removed as soon as possible
    os.remove(temp_name)

    return resHigh, freeRflag, fsigf_Flag


def _get_pdb_data(proj, pdb_file):
    r_work = ""
    resolution = ""

    for line in read_text_lines(proj, pdb_file):
        if "REMARK Final:" in line:
            r_work = line.split()[4]
        if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
            resolution = line.split(":")[-1].replace(" ", "").replace("\n", "")

    return r_work, resolution


def get_best_alt_dataset(proj, dataset, options):
    if options["complete_results"]:
        optionList = glob(f"{proj.data_path()}/fragmax/results/{dataset}/*/*/final.pdb")
    else:
        proc, ref = options["method"].split("_")
        optionList = glob(f"{proj.data_path()}/fragmax/results/{dataset}/{proc}/{ref}/final.pdb")
    rwork_res = list()

    if not optionList:
        return ""
    else:
        for pdb in optionList:
            r_work, resolution = _get_pdb_data(proj, pdb)
            rwork_res.append((pdb, r_work, resolution))
        rwork_res.sort(key=lambda pair: pair[1:3])
        return rwork_res[0][0]
