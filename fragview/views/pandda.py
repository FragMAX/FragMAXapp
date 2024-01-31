from typing import Optional
import time
import shutil
import natsort
from glob import glob
from random import randint
from pathlib import Path
from collections import Counter
from django.shortcuts import render, reverse
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
    HttpResponseBadRequest,
)
from fragview import versions
from fragview.forms import PanddaProcessForm
from fragview.mtz import read_info
from fragview.sites import SITE
from fragview.sites.current import (
    add_pandda_init_commands,
    get_giant_datasets_cluster_command,
)
from fragview.fileio import read_text_lines, upload_dir
from fragview.views.utils import png_http_response, start_thread, get_crystals_fragment
from fragview.projects import (
    Project,
    current_project,
    project_script,
    project_log_path,
    PANDDA_WORKER,
)
from fragview.pandda import (
    get_latest_method,
    load_method_reports,
    get_analysis_dir,
    get_analysis_html_file,
    get_available_methods,
    PanddaSelectedDatasets,
    Inspects,
    Inspect,
)
from pony.orm import db_session, select
from fragview.sites.plugin import Duration, DataSize
from jobs.client import JobsSet


def inspect(request):
    project = current_project(request)
    pandda_dir = project.pandda_dir

    glob_pattern = f"{pandda_dir}/*/pandda/analyses/html_summaries/*inspect.html"
    proc_methods = [x.split("/")[-5] for x in glob(glob_pattern)]

    if not proc_methods:
        localcmd = f"none"
        return render(request, "pandda_notready.html", {"cmd": localcmd})

    filters = []

    glob_pattern = f"{pandda_dir}/*/pandda/analyses/pandda_inspect_events.csv"
    eventscsv = [x for x in glob(glob_pattern)]

    filterform = request.GET.get("filterForm")
    if filterform is not None:
        if ";" in filterform:
            AP, DI, ED, XD, XA, DP, FS = filterform.split(";")
            xdsapp = 1 if "true" in XA else 0
            autoproc = 1 if "true" in AP else 0
            dials = 1 if "true" in DI else 0
            edna = 1 if "true" in ED else 0
            xdsxscale = 1 if "true" in XD else 0
            dimple = 1 if "true" in DP else 0
            fspipeline = 1 if "true" in FS else 0
            filters = list()
            filters.append("autoproc") if AP == "true" else ""
            filters.append("dials") if DI == "true" else ""
            filters.append("EDNA_proc") if ED == "true" else ""
            filters.append("xdsapp") if XA == "true" else ""
            filters.append("xdsxscale") if XD == "true" else ""
            filters.append("dimple") if DP == "true" else ""
            filters.append("fspipeline") if FS == "true" else ""
        else:
            flat_filters = set(
                [
                    j
                    for sub in [x.split("/")[10].split("_") for x in eventscsv]
                    for j in sub
                ]
            )
            xdsapp = 1 if "xdsapp" in flat_filters else 0
            autoproc = 1 if "autoproc" in flat_filters else 0
            dials = 1 if "dials" in flat_filters else 0
            edna = 1 if "edna" in flat_filters else 0
            xdsxscale = 1 if "xdsxscale" in flat_filters else 0
            dimple = 1 if "dimple" in flat_filters else 0
            fspipeline = 1 if "fspipeline" in flat_filters else 0

    else:
        flat_filters = set(
            [j for sub in [x.split("/")[10].split("_") for x in eventscsv] for j in sub]
        )
        xdsapp = 1 if "xdsapp" in flat_filters else 0
        autoproc = 1 if "autoproc" in flat_filters else 0
        dials = 1 if "dials" in flat_filters else 0
        edna = 1 if "edna" in flat_filters else 0
        xdsxscale = 1 if "xdsxscale" in flat_filters else 0
        dimple = 1 if "dimple" in flat_filters else 0
        fspipeline = 1 if "fspipeline" in flat_filters else 0

    method = request.GET.get("methods")
    if method is None or "panddaSelect" in method or ";" in method:

        if len(eventscsv) != 0:
            if method is not None and ";" in method:
                filters = list()
                AP, DI, FD, ED, XD, XA, BU, DP, FS = method.split(";")
                filters.append("autoproc") if AP == "true" else ""
                filters.append("dials") if DI == "true" else ""
                filters.append("EDNA_proc") if ED == "true" else ""
                filters.append("xdsapp") if XA == "true" else ""
                filters.append("xdsxscale") if XD == "true" else ""
                filters.append("dimple") if DP == "true" else ""
                filters.append("fspipeline") if FS == "true" else ""
            allEventDict, eventDict, low_conf, medium_conf, high_conf = pandda_events(
                pandda_dir, filters
            )

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

            inspects = Inspects()
            for k, v in natsort.natsorted(eventDict.items()):
                for k1, v1 in v.items():
                    dataset = k
                    site_idx = k1.split("_")[0]
                    event_idx = k1.split("_")[1]
                    proc_method = "_".join(v1[0].split("_")[0:2])
                    ddtag = v1[0].split("_")[2]
                    run = v1[0].split("_")[-1]

                    inspects.add(
                        Inspect(
                            f"{dataset}{ddtag}_{run}",
                            proc_method,
                            site_idx,
                            event_idx,
                        )
                    )

            inspects.save(pandda_dir)

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
            html += (
                "      <h1>Consensus of PANDDA Inspect Summaries "
                + "_".join(filters)
                + "</h1>\n"
            )
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
            html += (
                '              <span class="sr-only">Fitted - '
                + str(ligEvents)
                + " Events</span>\n"
            )
            html += (
                "              <strong>Fitted - "
                + str(ligEvents)
                + " Events (100%)</strong>\n"
            )
            html += "            </div>\n"
            html += '            <div class="progress-bar progress-bar-warning" style="width:0.0%">\n'
            html += '              <span class="sr-only">Unviewed - 0 Events</span>\n'
            html += "              <strong>Unviewed - 0 Events (0%)</strong>\n"
            html += "            </div>\n"
            html += '            <div class="progress-bar progress-bar-danger" style="width:0.0%">\n'
            html += '              <span class="sr-only">No Ligand Fitted - 10 Events</span>\n'
            html += (
                "              <strong>No Ligand Fitted - 10 Events (16%)</strong>\n"
            )
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
                html += (
                    '            <div class="progress-bar '
                    + colour
                    + '" style="width:'
                    + str(siteP[k])
                    + '%">\n'
                )
                html += (
                    '              <span class="sr-only">S'
                    + k
                    + ": "
                    + str(v)
                    + " hits</span>\n"
                )
                html += (
                    "              <strong>S"
                    + k
                    + ": "
                    + str(v)
                    + " hits ("
                    + str(int(siteP[k]))
                    + "%)</strong>\n"
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
                "<strong>Datasets w. ligands: "
                + str(ligEvents)
                + " (of #dataset collected)</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert">'
                "<strong>Sites w. ligands: "
                + str(len(siteP))
                + " (of 10)</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-info" role="alert">'
                "<strong>Unique fragments: " + uniqueEvents + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-info" role="alert">'
                "<strong>Total number of events: "
                + str(totalEvents)
                + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-success" role="alert">'
                "<strong>High confidence hits:   "
                + str(high_conf)
                + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-warning" role="alert">'
                "<strong>Medium confidence hits: "
                + str(medium_conf)
                + "</strong></div></div>\n"
            )
            html += (
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-danger" role="alert">'
                "<strong>Low confidence hits:    "
                + str(low_conf)
                + "</strong></div></div>\n"
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
                    detailsDict = dataset_details(pandda_dir, k, k1, v1[0][:-4])

                    dataset = k
                    site_idx = k1.split("_")[0]
                    event_idx = k1.split("_")[1]
                    proc_method = "_".join(v1[0].split("_")[0:2])
                    ddtag = v1[0].split("_")[2]
                    run = v1[0].split("_")[-1]

                    ds = (
                        dataset
                        + ";"
                        + site_idx
                        + ";"
                        + event_idx
                        + ";"
                        + proc_method
                        + ";"
                        + ddtag
                        + ";"
                        + run
                    )

                    if (
                        detailsDict["viewed"] == "False\n"
                        or detailsDict["ligplaced"] == "False"
                        or detailsDict["interesting"] == "False"
                    ):
                        html += "        <tr class=info>\n"
                    else:
                        html += "        <tr class=success>\n"

                    html += (
                        '<th class="text-nowrap" scope="row" style="text-align: center;">'
                        f'<a href="/pandda_densityC/{proc_method}/{dataset}{ddtag}_{run}/{site_idx}/{event_idx}"'
                        ' target="_blank">'
                        '<button class="btn" type="submit" value="'
                        + ds
                        + '" name="structure" size="1">'
                        "Open</button></a></th>\n"
                    )
                    html += (
                        '          <th class="text-nowrap" scope="row">'
                        + k
                        + v1[0][-3:]
                        + "</th>\n"
                    )
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
                "pandda_inspect.html",
                {
                    "proc_methods": proc_methods,
                    "Report": html,
                    "xdsapp": xdsapp,
                    "autoproc": autoproc,
                    "dials": dials,
                    "edna": edna,
                    "xdsxscale": xdsxscale,
                    "dimple": dimple,
                    "fspipeline": fspipeline,
                },
            )

    else:
        inspect_file = Path(
            pandda_dir,
            method,
            "pandda",
            "analyses",
            "html_summaries",
            "pandda_inspect.html",
        )

        if inspect_file.is_file():
            with open(inspect_file, "r") as inp:
                inspectfile = inp.readlines()
                html = ""
                for n, line in enumerate(inspectfile):
                    if '<th class="text-nowrap" scope="row">' in line:

                        event = (
                            inspectfile[n + 4]
                            .split("/span>")[-1]
                            .split("</td>")[0]
                            .replace(" ", "")
                        )
                        site = (
                            inspectfile[n + 5]
                            .split("/span>")[-1]
                            .split("</td>")[0]
                            .replace(" ", "")
                        )
                        ds = (
                            method
                            + ";"
                            + line.split('row">')[-1].split("</th")[0]
                            + ";"
                            + event
                            + ";"
                            + site
                        )

                        html += (
                            '<td><form action="/pandda_density/" method="get" id="pandda_form" target="_blank">'
                            '<button class="btn" type="submit" value="'
                            + ds
                            + ';stay" name="structure" size="1">'
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
                xdsxscale = 1 if "xdsxscale" in flat_filters else 0
                dimple = 1 if "dimple" in flat_filters else 0
                fspipeline = 1 if "fspipeline" in flat_filters else 0

                return render(
                    request,
                    "pandda_inspect.html",
                    {
                        "proc_methods": proc_methods,
                        "Report": html.replace(
                            "PANDDA Inspect Summary",
                            "PANDDA Inspect Summary for " + method,
                        ),
                        "xdsapp": xdsapp,
                        "autoproc": autoproc,
                        "dials": dials,
                        "edna": edna,
                        "xdsxscale": xdsxscale,
                        "dimple": dimple,
                        "fspipeline": fspipeline,
                    },
                )
        else:
            return HttpResponseNotFound(f"file '{inspect_file}' not found")


def pandda_events(pandda_dir: Path, filters):
    eventscsv = glob(f"{pandda_dir}/*/pandda/analyses/pandda_inspect_events.csv")

    if len(filters) != 0:
        eventscsv = [x for x in eventscsv if any(xs in x for xs in filters)]
    eventDict = dict()
    allEventDict = dict()

    high_conf = 0
    medium_conf = 0
    low_conf = 0

    for eventcsv in eventscsv:
        method = eventcsv.split("/")[-4]

        with open(eventcsv, "r") as inp:
            a = inp.readlines()
        a = [x.split(",") for x in a]  # type: ignore
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

                    eventDict[dtag] = {
                        site_idx + "_" + event_idx: {method + "_" + line[0][-3:]: bdc}
                    }
                    allEventDict[dtag] = {
                        site_idx + "_" + event_idx: {method + "_" + line[0][-3:]: bdc}
                    }
                else:

                    if site_idx not in eventDict[dtag]:
                        eventDict[dtag].update(
                            {
                                site_idx
                                + "_"
                                + event_idx: {method + "_" + line[0][-3:]: bdc}
                            }
                        )
                        allEventDict[dtag].update(
                            {
                                site_idx
                                + "_"
                                + event_idx: {method + "_" + line[0][-3]: bdc}
                            }
                        )
                    else:
                        eventDict[dtag][site_idx + "_" + event_idx].update(
                            {method + "_" + line[0][-3:]: bdc}
                        )
                        allEventDict[dtag][site_idx + "_" + event_idx].update(
                            {method + "_" + line[0][-3:]: bdc}
                        )

    for k, v in eventDict.items():
        for k1, v1 in v.items():
            v[k1] = sorted(v1.items(), key=lambda t: t[1])[0]  # type: ignore

    return allEventDict, eventDict, low_conf, medium_conf, high_conf


def dataset_details(pandda_dir: Path, dataset, site_idx, method):
    detailsDict = dict()

    events_csv = Path(
        pandda_dir, method, "pandda", "analyses", "pandda_inspect_events.csv"
    )

    with events_csv.open("r") as inp:
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


def cluster_image(request, method, cluster):
    project = current_project(request)

    png_path = Path(
        project.pandda_dir,
        method,
        "clustered-datasets",
        "dendrograms",
        f"{cluster}.png",
    )

    if not png_path.is_file():
        return HttpResponseNotFound(f"no dendrogram image for {method}/{cluster} found")

    return png_http_response(png_path)


def analyse(request, method=None):
    project = current_project(request)

    if method is None:
        method = get_latest_method(project)

    if method is None:
        # no pandda resuls found
        return render(request, "pandda_notready.html")

    return render(
        request,
        "pandda_analyse.html",
        {
            "method": method,
            "reports": load_method_reports(project, method),
            "available_methods": get_available_methods(project),
        },
    )


def analysis_report(request, method, date):
    pandda_html = pandda_to_fragmax_html(current_project(request), method, date)
    return HttpResponse(pandda_html)


def delete_report(request, method, date):
    project = current_project(request)

    analysis_dir = get_analysis_dir(project, method, date)
    shutil.rmtree(analysis_dir)

    return HttpResponseRedirect(reverse("pandda_analyse"))


def pandda_to_fragmax_html(project: Project, method: str, date: str):
    pandda_analyse_html = get_analysis_html_file(project, method, date)

    pandda_html = ""
    for line in read_text_lines(project, pandda_analyse_html):
        if '<th class="text-nowrap" scope="row">' in line:
            dt = line.split('scope="row">')[-1].split("<")[0]
            line = (
                f'<td class="sorting_1" style="text-align: center;" >'
                f'<a href="/pandda_densityA/{method}/{dt}" target="_blank" class="btn">'
                f"Open</a></td>{line}"
            )

        pandda_html += f"{line}\n"

    pandda_html = pandda_html.replace(
        '<th class="text-nowrap">Dataset</th>',
        '<th class="text-nowrap">Open</th><th class="text-nowrap">Dataset</th>',
    )
    pandda_html = pandda_html.replace(
        'class="table table-bordered table-striped"',
        'class="table table-bordered table-striped" data-page-length="50"',
    )
    pandda_html = pandda_html.replace(
        "PANDDA Processing Output", "PANDDA Processing Output for " + method
    )

    return pandda_html


def process(request):
    form = PanddaProcessForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid processing arguments {form.errors}")

    project = current_project(request)

    print(f"{form.processing_tool=}")
    print(f"{form.refinement_tool=}")
    print(f"{form.restrains_tool=}")
    print(f"{form.use_known_apo=}")
    print(f"{form.use_dmso_datasets=}")
    print(f"{form.reprocess_z_maps=}")
    print(f"{form.num_of_cores=}")
    print(f"{form.min_ground_datasets=}")
    print(f"{form.max_r_free=}")
    print(f"{form.resolution_upper_limit=}")
    print(f"{form.resolution_lower_limit=}")
    print(f"{form.custom_parameters=}")

    custom_pandda = (
        f"{form.custom_parameters} max_rfree={form.max_r_free} "
        f"high_res_upper_limit={form.resolution_upper_limit} "
        f"high_res_lower_limit={form.resolution_lower_limit}"
    )

    options = {
        "useApos": form.use_known_apo,
        # 'dtsfilter' and 'useSelected' are unused flags to specify
        # specific datasets to process
        "dtsfilter": "null",
        "useSelected": False,
        "reprocessZmap": form.reprocess_z_maps,
        "initpass": True,
        "min_datasets": form.min_ground_datasets,
        "customPanDDA": custom_pandda,
        "reprocessing": False,
        "reprocessing_mode": "reprocess",
        "nproc": form.num_of_cores,
    }

    start_thread(
        pandda_worker,
        project,
        form.processing_tool,
        form.refinement_tool,
        options,
        form.restrains_tool,
    )

    return HttpResponse("ok")


def _write_main_script(
    project: Project, pandda_dir: Path, method, methodshort, options
):
    epoch = round(time.time())

    log_prefix = project_log_path(project, f"PanDDA_{method}_{epoch}_%j_")

    pandda_script = project_script(project, PANDDA_WORKER)

    if options["reprocessZmap"]:
        pandda_cluster = ""
    else:
        cmd = get_giant_datasets_cluster_command()
        pandda_cluster = f"{cmd} ./*/final.pdb pdb_label=foldername"

    hpc = SITE.get_hpc_runner()
    batch = hpc.new_batch_file(
        f"PDD{methodshort}",
        project_script(project, f"pandda_{method}.sh"),
        f"{log_prefix}out.txt",
        f"{log_prefix}err.txt",
        cpus=40,
    )
    batch.set_options(
        time=Duration(hours=99),
        exclusive=True,
        nodes=1,
    )

    batch.add_command(f"cd {pandda_dir}")

    add_pandda_init_commands(batch)

    batch.add_commands(
        pandda_cluster,
        f'python {pandda_script} {pandda_dir} {project.protein} "{options}"',
        f"chmod -R 777 {project.pandda_dir}",
    )

    # add commands to fix symlinks
    ln_command = '\'ln -f "$(readlink -m "$0")" "$0"\' {} \\;'
    batch.add_commands(
        f"cd {project.pandda_dir}; find -type l -iname *-pandda-input.* -exec bash -c {ln_command}",
        f"cd {project.pandda_dir}; find -type l -iname *pandda-model.pdb -exec bash -c {ln_command}",
    )

    batch.save()
    return batch


def _get_refine_results(project: Project, dataset, proc_tool=None, refine_tool=None):
    """
    get refine results for specified dataset produced with processing tool 'proc_tool'
    and refine tool 'refile_tool'

    None value for proc_tool and refine_tool arguments means 'any tool'
    """

    def result_match(refine_result):
        return (
            refine_result.result.result == "ok"
            and refine_result.dataset == dataset
            and (refine_tool is None or refine_result.result.tool == refine_tool)
            and (proc_tool is None or refine_result.result.input.tool == proc_tool)
        )

    return select(r for r in project.db.RefineResult if result_match(r))


def _get_best_results(
    project: Project, proc_tool: Optional[str], refine_tool: Optional[str]
):
    if proc_tool == "fragplex":
        proc_tool = None

    if refine_tool == "fragplex":
        refine_tool = None

    for dataset in project.get_datasets():
        refine_results = _get_refine_results(project, dataset, proc_tool, refine_tool)

        # sort refine results by R-work, R-free and resolution,
        # the result with lowest value(s) is the 'best' one
        best_result = refine_results.order_by(
            lambda r: (r.r_work, r.r_free, r.resolution)
        ).first()

        if best_result is None:
            # no refine results with request proc/refine tool combination
            continue

        yield best_result


@db_session
def pandda_worker(project: Project, proc_tool, refine_tool, options, cif_method):
    rn = str(randint(10000, 99999))
    prepare_scripts = []

    method = f"{proc_tool}_{refine_tool}"
    methodshort = proc_tool[:2] + proc_tool[:2]

    options["method"] = method

    selection = PanddaSelectedDatasets()
    pandda_dir = Path(project.pandda_dir, method)
    pandda_dir.mkdir(parents=True, exist_ok=True)

    if not options["reprocessZmap"]:
        refine_results = _get_best_results(project, proc_tool, refine_tool)
        for refine_result in refine_results:
            res_dir = project.get_refine_result_dir(refine_result)
            final_pdb = Path(res_dir, "final.pdb")
            final_mtz = Path(res_dir, "final.mtz")

            selection.add(refine_result.dataset.name, final_pdb)

            res_high, free_r_flag, native_f, sigma_fp = read_info(str(final_mtz))

            script = _write_prepare_script(
                project,
                rn,
                method,
                refine_result.dataset,
                final_pdb,
                final_mtz,
                res_high,
                free_r_flag,
                native_f,
                sigma_fp,
                cif_method,
            )

            prepare_scripts.append(script)

        selection.save(Path(pandda_dir))

    main_script = _write_main_script(project, pandda_dir, method, methodshort, options)

    #
    # submit all pandda script to the HPC
    #
    jobs = JobsSet(project, "PanDDa")

    for prep_script in prepare_scripts:
        jobs.add_job(prep_script)

    jobs.add_job(main_script, run_after=prepare_scripts)

    print("done!")

    jobs.submit()


def _write_prepare_script(
    project: Project,
    rn,
    method,
    dataset,
    pdb,
    mtz,
    resHigh,
    free_r_flag,
    native_f,
    sigma_fp,
    cif_method,
):
    epoch = round(time.time())
    output_dir = Path(project.pandda_method_dir(method), dataset.name)

    hpc = SITE.get_hpc_runner()
    batch = hpc.new_batch_file(
        f"PnD{rn}",
        project_script(project, f"pandda_prepare_{method}_{dataset.name}.sh"),
        project_log_path(project, f"{dataset.name}_PanDDA_{epoch}_%j_out.txt"),
        project_log_path(project, f"{dataset.name}_PanDDA_{epoch}_%j_err.txt"),
        cpus=1,
    )
    batch.set_options(time=Duration(minutes=15), memory=DataSize(gigabyte=5))

    batch.assign_variable("DEST_DIR", output_dir)
    batch.assign_variable("WORK_DIR", "`mktemp -d`")
    batch.add_commands(
        "cd $WORK_DIR",
        f"cp {pdb} final.pdb",
        f"cp {mtz} final.mtz",
    )

    batch.purge_modules()
    batch.load_modules(
        ["gopresto", versions.PHENIX_MOD, versions.CCP4_MOD, versions.BUSTER_MOD]
    )

    if not dataset.crystal.is_apo():
        fragment = get_crystals_fragment(dataset.crystal)
        # non-apo crystal should have a fragment
        assert fragment
        if cif_method == "elbow":
            cif_cmd = f"phenix.elbow --smiles='{fragment.smiles}' --output=$WORK_DIR/{fragment.code} --opt\n"
        else:
            assert cif_method == "grade"
            cif_cmd = (
                f"grade '{fragment.smiles}' -ocif $WORK_DIR/{fragment.code}.cif "
                f"-opdb $WORK_DIR/{fragment.code}.pdb -nomogul\n"
            )

        batch.add_command(cif_cmd)

    batch.add_commands(
        f'printf "monitor BRIEF\\n labin file 1 -\\n  ALL\\n resolution file 1 999.0 {resHigh}\\n" | \\\n'
        "    cad hklin1 $WORK_DIR/final.mtz hklout $WORK_DIR/final.mtz",
        "uniqueify -f FreeR_flag $WORK_DIR/final.mtz $WORK_DIR/final.mtz",
        f'printf "COMPLETE FREE={free_r_flag} \\nEND\\n" | \\\n'
        "    freerflag hklin $WORK_DIR/final.mtz hklout $WORK_DIR/final_rfill.mtz",
        f"phenix.maps final_rfill.mtz final.pdb maps.input.reflection_data.labels='{native_f},{sigma_fp}'",
        "mv final.mtz final_original.mtz",
        "mv final_map_coeffs.mtz final.mtz",
        "rm -rf $DEST_DIR",
        upload_dir("$WORK_DIR", "$DEST_DIR"),
        "rm -rf $WORK_DIR",
    )

    batch.save()
    return batch
