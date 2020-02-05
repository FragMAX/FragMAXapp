import os
import csv
import natsort
import pyfastcopy  # noqa
import shutil
import threading
import json
import subprocess
from os import path
from glob import glob
from random import randint
from datetime import datetime
from collections import Counter
from django.shortcuts import render
from fragview import hpc
from fragview.views import utils
from fragview.projects import current_project, project_results_dir, project_script, project_process_protein_dir
from fragview.projects import project_process_dir


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

    if proc_methods == []:
        localcmd = f"cd {proj.data_path()}/fragmax/results/pandda/xdsapp_fspipeline/pandda/; pandda.inspect"
        return render(request, "fragview/pandda_notready.html", {"cmd": localcmd})

    filters = []

    glob_pattern = f"{res_dir}/*/pandda/analyses/pandda_inspect_events.csv"
    eventscsv = [x for x in glob(glob_pattern)]

    filterform = request.GET.get("filterForm")
    if filterform is not None:
        if ";" in filterform:
            AP, DI, FD, ED, XD, XA, BU, DP, FS = filterform.split(";")
            xdsapp = (1 if "true" in XA else 0)
            autoproc = (1 if "true" in AP else 0)
            dials = (1 if "true" in DI else 0)
            edna = (1 if "true" in ED else 0)
            fastdp = (1 if "true" in FD else 0)
            xdsxscale = (1 if "true" in XD else 0)
            dimple = (1 if "true" in DP else 0)
            fspipeline = (1 if "true" in FS else 0)
            buster = (1 if "true" in BU else 0)
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
            xdsapp = (1 if "xdsapp" in flat_filters else 0)
            autoproc = (1 if "autoproc" in flat_filters else 0)
            dials = (1 if "dials" in flat_filters else 0)
            edna = (1 if "edna" in flat_filters else 0)
            fastdp = (1 if "fastdp" in flat_filters else 0)
            xdsxscale = (1 if "xdsxscale" in flat_filters else 0)
            dimple = (1 if "dimple" in flat_filters else 0)
            fspipeline = (1 if "fspipeline" in flat_filters else 0)
            buster = (1 if "buster" in flat_filters else 0)

    else:
        flat_filters = set([j for sub in [x.split("/")[10].split("_") for x in eventscsv] for j in sub])
        xdsapp = (1 if "xdsapp" in flat_filters else 0)
        autoproc = (1 if "autoproc" in flat_filters else 0)
        dials = (1 if "dials" in flat_filters else 0)
        edna = (1 if "edna" in flat_filters else 0)
        fastdp = (1 if "fastdp" in flat_filters else 0)
        xdsxscale = (1 if "xdsxscale" in flat_filters else 0)
        dimple = (1 if "dimple" in flat_filters else 0)
        fspipeline = (1 if "fspipeline" in flat_filters else 0)
        buster = (1 if "buster" in flat_filters else 0)

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

            html = ''
            # HTML Head
            html += '    <!DOCTYPE html>\n'
            html += '    <html lang="en">\n'
            html += '      <head>\n'
            html += '        <meta charset="utf-8">\n'
            html += '        <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            html += '        <link rel="stylesheet" ' \
                    'href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css">\n'
            html += '        <link rel="stylesheet" ' \
                    'href="https://cdn.datatables.net/1.10.11/css/dataTables.bootstrap.min.css">\n'
            html += '        <script src="https://code.jquery.com/jquery-1.12.0.min.js"></script>\n'
            html += '        <script src="https://cdn.datatables.net/1.10.11/js/jquery.dataTables.min.js"></script>\n'
            html += '        <script ' \
                    'src="https://cdn.datatables.net/1.10.11/js/dataTables.bootstrap.min.js"></script>\n'
            html += '          <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>\n'
            html += '          <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>\n'
            html += '        <script type="text/javascript" class="init">\n'
            html += '    $(document).ready(function() {\n'
            html += "        $('#main-table').DataTable();\n"
            html += '    } );\n'
            html += '        </script>   \n'
            html += '    <title>PANDDA Inspect Summary</title>\n'
            html += '</head>\n'
            html += '<body>\n'
            html += '    <div class="container">\n'
            html += '      <h1>Consensus of PANDDA Inspect Summaries ' + "_".join(filters) + '</h1>\n'
            html += '      <h2>Summary of Inspection of Datasets</h2>\n'
            html += '      \n'

            # Styles CSS
            html += '<style>\n'
            html += '    .container {\n'
            html += '        max-width: 100% !important;\n'
            html += '        margin: 0 50px 50px 150px !important;\n'
            html += '        width: calc(100% - 200px) !important;\n'
            html += '    }\n'
            html += '    .col-md-8 {\n'
            html += '    width: 100% !important;\n'
            html += '    }\n'
            html += '    </style>\n'

            # Fitting process plot (necessary?)
            html += '      <div class="row">\n'
            html += '        <div class="col-xs-12">\n'
            html += '          <p>Fitting Progress</p>\n'
            html += '          <div class="progress">\n'
            html += '            <div class="progress-bar progress-bar-success" style="width:100%">\n'
            html += '              <span class="sr-only">Fitted - ' + str(ligEvents) + ' Events</span>\n'
            html += '              <strong>Fitted - ' + str(ligEvents) + ' Events (100%)</strong>\n'
            html += '            </div>\n'
            html += '            <div class="progress-bar progress-bar-warning" style="width:0.0%">\n'
            html += '              <span class="sr-only">Unviewed - 0 Events</span>\n'
            html += '              <strong>Unviewed - 0 Events (0%)</strong>\n'
            html += '            </div>\n'
            html += '            <div class="progress-bar progress-bar-danger" style="width:0.0%">\n'
            html += '              <span class="sr-only">No Ligand Fitted - 10 Events</span>\n'
            html += '              <strong>No Ligand Fitted - 10 Events (16%)</strong>\n'
            html += '            </div>\n'
            html += '            </div>\n'
            html += '        </div>\n'

            # Site distribution plot
            html += '        <div class="col-xs-12">\n'
            html += '          <p>Identified Ligands by Site</p>\n'
            html += '          <div class="progress">\n'
            colour = "progress-bar-info"
            for k, v1 in siteP.items():

                v = siteN[k]
                html += '            <div class="progress-bar ' + colour + '" style="width:' + str(siteP[k]) + '%">\n'
                html += '              <span class="sr-only">S' + k + ': ' + str(v) + ' hits</span>\n'
                html += '              <strong>S' + k + ': ' + str(v) + ' hits (' + str(int(siteP[k])) + '%)</strong>\n'
                html += '            </div>\n'
                if colour == "progress-bar-info":
                    colour = "progress-bar-default"
                else:
                    colour = "progress-bar-info"

            # Inspections facts

            html += '            </div>\n'
            html += '        </div>\n'
            html += '        </div>\n'
            html += '      \n'
            html += '      \n'
            html += '      <div class="row">\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert">' \
                '<strong>Datasets w. ligands: ' + str(ligEvents) + ' (of #dataset collected)</strong></div></div>\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert">' \
                '<strong>Sites w. ligands: ' + str(len(siteP)) + ' (of 10)</strong></div></div>\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-info" role="alert">' \
                '<strong>Unique fragments: ' + uniqueEvents + '</strong></div></div>\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-info" role="alert">' \
                '<strong>Total number of events: ' + str(totalEvents) + '</strong></div></div>\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-success" role="alert">' \
                '<strong>High confidence hits:   ' + str(high_conf) + '</strong></div></div>\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-warning" role="alert">' \
                '<strong>Medium confidence hits: ' + str(medium_conf) + '</strong></div></div>\n'
            html += \
                '        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-danger" role="alert">' \
                '<strong>Low confidence hits:    ' + str(low_conf) + '</strong></div></div>\n'
            html += '        </div>\n'
            html += '      \n'
            html += '      \n'
            html += '      <div class="row">\n'
            html += '        </div>\n'
            html += '<hr>\n'

            # Table header
            html += '<div class="table-responsive">\n'
            html += '<table id="main-table" class="table table-bordered table-striped" data-page-length="50">\n'
            html += '    <thead>\n'
            html += '    <tr>\n'
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
            html += '        </tr>\n'
            html += '    </thead>\n'

            # Table body
            html += '<tbody>\n'

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

                    if detailsDict["viewed"] == "False\n" or \
                            detailsDict["ligplaced"] == "False" or \
                            detailsDict["interesting"] == "False":
                        html += '        <tr class=info>\n'
                    else:
                        html += '        <tr class=success>\n'

                    html += \
                        '          <th class="text-nowrap" scope="row" style="text-align: center;">' \
                        '<form action="/pandda_densityC/" method="get" id="pandda_form" target="_blank">' \
                        '<button class="btn" type="submit" value="' + ds + '" name="structure" size="1">' \
                                                                           'Open</button></form></th>\n'
                    html += \
                        '          <th class="text-nowrap" scope="row">' + k + v1[0][-3:] + '</th>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span>' + \
                        v1[0][:-4] + '</td>\n'

                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict['event_idx'] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["site_idx"] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["bdc"] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["z_peak"] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["map_res"] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["map_unc"] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["ligconfid"] + '</td>\n'
                    html += \
                        '          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> ' + \
                        detailsDict["comment"] + '</td>\n'
                    html += '          <td><span class="label label-success">Hit</span></td></tr>\n'
            html += '\n'
            html += '</tbody>\n'
            html += '</table>\n'
            html += '</div>\n'
            html += '\n'
            html += '</body>\n'
            html += '</html>\n'

            return render(request, 'fragview/pandda_inspect.html', {
                'proc_methods': proc_methods,
                'Report': html,
                'xdsapp': xdsapp,
                'autoproc': autoproc,
                'dials': dials,
                'edna': edna,
                'fastdp': fastdp,
                'xdsxscale': xdsxscale,
                'dimple': dimple,
                'fspipeline': fspipeline,
                'buster': buster,
            })

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
                        ds = method + ";" + line.split('row">')[-1].split('</th')[0] + ";" + event + ";" + site

                        html += \
                            '<td><form action="/pandda_density/" method="get" id="pandda_form" target="_blank">' \
                            '<button class="btn" type="submit" value="' + ds + ';stay" name="structure" size="1">' \
                                                                               'Open</button></form>'
                        html += line
                    else:
                        html += line

                html = "".join(html)
                html = html.replace('<th class="text-nowrap">Dataset</th>',
                                    '<th class="text-nowrap">Open</th><th class="text-nowrap">Dataset</th>')
                flat_filters = method.split("_")
                xdsapp = (1 if "xdsapp" in flat_filters else 0)
                autoproc = (1 if "autoproc" in flat_filters else 0)
                dials = (1 if "dials" in flat_filters else 0)
                edna = (1 if "edna" in flat_filters else 0)
                fastdp = (1 if "fastdp" in flat_filters else 0)
                xdsxscale = (1 if "xdsxscale" in flat_filters else 0)
                dimple = (1 if "dimple" in flat_filters else 0)
                fspipeline = (1 if "fspipeline" in flat_filters else 0)
                buster = (1 if "buster" in flat_filters else 0)

                return render(
                    request,
                    "fragview/pandda_inspect.html",
                    {
                        "proc_methods": proc_methods,
                        "Report": html.replace("PANDDA Inspect Summary",
                                               "PANDDA Inspect Summary for " + method),
                        "xdsapp": xdsapp,
                        "autoproc": autoproc,
                        "dials": dials,
                        "edna": edna,
                        "fastdp": fastdp,
                        "xdsxscale": xdsxscale,
                        "dimple": dimple,
                        "fspipeline": fspipeline,
                        "buster": buster})
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
                    "buster": 0})


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

    events_csv = os.path.join(project_results_dir(proj), "pandda", proj.protein,
                              method, "pandda", "analyses", "pandda_inspect_events.csv")

    with open(events_csv, "r") as inp:
        a = inp.readlines()

    for i in a:
        if dataset in i:
            if i.split(",")[11] + "_" + i.split(",")[1] == site_idx:
                k = i.split(",")

    headers = a[0].split(",")
    detailsDict['event_idx'] = k[1]
    detailsDict['bdc'] = k[2]
    detailsDict['site_idx'] = k[11]
    detailsDict['center'] = "[" + k[12] + "," + k[13] + "," + k[14] + "]"
    detailsDict['z_peak'] = k[16]
    detailsDict['resolution'] = k[18]
    detailsDict['rfree'] = k[20]
    detailsDict['rwork'] = k[21]
    detailsDict['spg'] = k[35]
    detailsDict['map_res'] = k[headers.index("analysed_resolution")]
    detailsDict['map_unc'] = k[headers.index("map_uncertainty")]
    detailsDict['analysed'] = k[headers.index("analysed")]
    detailsDict['interesting'] = k[headers.index("Interesting")]
    detailsDict['ligplaced'] = k[headers.index("Ligand Placed")]
    detailsDict['ligconfid'] = k[headers.index("Ligand Confidence")]
    detailsDict['comment'] = k[headers.index("Comment")]
    detailsDict['viewed'] = k[headers.index("Viewed\n")]

    return detailsDict


def giant(request):
    proj = current_project(request)

    available_scores = glob(
        f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/*/pandda-scores/residue_scores.html")

    if not available_scores:
        # no panda scores files found
        return render(request, "fragview/index.html")

    scoreDict = dict()
    for score in available_scores:
        with open(score, "r") as readFile:
            htmlcontent = "".join(readFile.readlines())

        htmlcontent = htmlcontent.replace('src="./residue_plots',
                                          'src="/static/' + '/'.join(score.split('/')[3:-1]) + '/residue_plots')
        scoreDict[score.split('/')[-3]] = htmlcontent

    return render(request, "fragview/pandda_giant.html", {"scores_plots": scoreDict})


def analyse(request):
    proj = current_project(request)
    panda_results_path = os.path.join(proj.data_path(), "fragmax", "results", "pandda", proj.protein)

    fixsl = request.GET.get("fixsymlinks")
    if fixsl is not None and "FixSymlinks" in fixsl:
        t1 = threading.Thread(target=fix_pandda_symlinks, args=(proj,))
        t1.daemon = True
        t1.start()

    proc_methods = [x.split("/")[-2] for x in glob(panda_results_path + "/*/pandda")]
    newest = datetime.strptime("2000-01-01-1234", '%Y-%m-%d-%H%M')
    newestpath = ""
    newestmethod = ""
    for methods in proc_methods:
        if len(glob(panda_results_path + "/" + methods + "/pandda/analyses-*")) > 0:
            last = sorted(glob(panda_results_path + "/" + methods + "/pandda/analyses-*"))[-1]
            if os.path.exists(last + "/html_summaries/pandda_analyse.html"):
                time = datetime.strptime(last.split("analyses-")[-1], '%Y-%m-%d-%H%M')
                if time > newest:
                    newest = time
                    newestpath = last
                    newestmethod = methods

    method = request.GET.get("methods")

    if method is None or "panddaSelect" in method:
        if os.path.exists(newestpath + "/html_summaries/pandda_analyse.html"):
            with open(newestpath + "/html_summaries/pandda_analyse.html", "r") as inp:
                a = "".join(inp.readlines())
                localcmd = "cd " + panda_results_path + "/" + newestmethod + "/pandda/; pandda.inspect"

                return render(request, 'fragview/pandda_analyse.html',
                              {"opencmd": localcmd, 'proc_methods': proc_methods,
                               'Report': a.replace("PANDDA Processing Output",
                                                   "PANDDA Processing Output for " + newestmethod)})
        else:
            running = [x.split("/")[10] for x in glob(panda_results_path + "/*/pandda/*running*")]
            return render(request, 'fragview/pandda_notready.html', {'Report': "<br>".join(running)})

    else:
        if os.path.exists(panda_results_path + "/" + method + "/pandda/analyses/html_summaries/pandda_analyse.html"):
            with open(panda_results_path + "/" + method + "/pandda/analyses/html_summaries/pandda_analyse.html",
                      "r") as inp:
                a = "".join(inp.readlines())
                localcmd = "cd " + panda_results_path + "/" + method + "/pandda/; pandda.inspect"

            return render(
                request,
                "fragview/pandda_analyse.html",
                {
                    "opencmd": localcmd, "proc_methods": proc_methods,
                    "Report": a.replace("PANDDA Processing Output",
                                        "PANDDA Processing Output for " + method)
                })
        else:
            running = [x.split("/")[9] for x in glob(panda_results_path + "/*/pandda/*running*")]
            return render(request, 'fragview/pandda_notready.html', {'Report': "<br>".join(running)})


def fix_pandda_symlinks(proj):
    os.system("chmod -R 775 " + proj.data_path() + "/fragmax/results/pandda/")

    subprocess.call(
        "cd " + proj.data_path() + "/fragmax/results/pandda/" + proj.protein +
        """/ ; find -type l -iname *-pandda-input.* -exec bash -c 'ln -f "$(readlink -m "$0")" "$0"' {} \;""",  # noqa
        shell=True)

    subprocess.call(
        "cd " + proj.data_path() + "/fragmax/results/pandda/" + proj.protein +
        """/ ; find -type l -iname *pandda-model.pdb -exec bash -c 'ln -f "$(readlink -m "$0")" "$0"' {} \;""",  # noqa
        shell=True)

    subprocess.call("cd " + proj.data_path() + "/fragmax/results/pandda/" + proj.protein + """/ ; chmod -R 770 .""",
                    shell=True)

    glob_pattern = f"{project_results_dir(proj)}/pandda/{proj.protein}/*/pandda/" \
                   f"processed_datasets/*/modelled_structures/*pandda-model.pdb"
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
        function, proc, ref, complete, use_apo, use_dmso, use_cryo, use_CAD, ref_CAD, \
            ign_errordts, keepup_last, ign_symlink = panddaCMD.split(";")

        method = proc + "_" + ref

        res_dir = os.path.join(project_results_dir(proj), "pandda", proj.protein, method)
        res_pandda = os.path.join(res_dir, "pandda")
        if os.path.exists(res_pandda):
            if os.path.exists(os.path.join(res_dir, "pandda_backup")):
                shutil.rmtree(os.path.join(res_dir, "pandda_backup"))
            shutil.move(res_pandda, os.path.join(res_dir, "pandda_backup"))

        py_script = project_script(proj, "pandda_worker.py")
        with open(py_script, "w") as outp:
            outp.write('''  # noqa E501
import os
import glob
import sys
import subprocess
import shutil
import multiprocessing
path=sys.argv[1]
method=sys.argv[2]
acr=sys.argv[3]
fraglib=sys.argv[4]
shiftList=sys.argv[5].split(",")
proposal=path.split("/")[4]
noZmapmode=True
initpass=True
ground_state_entries=','.join([x.split("/")[-1] for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/*Apo*")])
def pandda_run(method,ground_state_entries,initpass):
    os.chdir(path+"/fragmax/results/pandda/"+acr+"/"+method)
    command="pandda.analyse data_dirs='"+path+"/fragmax/results/pandda/"+acr+"/"+method+"/*' ground_state_datasets='"+ground_state_entries+"' cpus=16 "
    subprocess.call(command, shell=True)
    if len(glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/logs/*.log"))>0:
        lastlog=sorted(glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/logs/*.log"))[-1]
        with open(lastlog,"r") as logfile:
            log=logfile.readlines()
        badDataset=dict()
        for line in log:
            if "Structure factor column"  in line:
                bd=line.split(" has ")[0].split("in dataset ")[-1]
                bdpath=glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+bd+"*")
                badDataset[bd]=bdpath
            if "Failed to align dataset" in line:
                bd=line.split("Failed to align dataset ")[1].rstrip()
                bdpath=glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+bd+"*")
                badDataset[bd]=bdpath
            if "Writing PanDDA End-of-Analysis Summary" in line and noZmapmode==True and initpass==True:
                with open(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/pandda_analyse_events.csv","r") as readFile:
                    events=csv.reader(readFile)
                    events=[x for x in events][1:]
                noZmap=[x[0] for x in events]
                alldts=[x.split("/")[-1] for x in glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+acr+"*")]
                newGroundStates=",".join(list(set(alldts) - set(noZmap)))
                initpass=False
                pandda_run(method,newGroundStates,initpass)

        for k,v in badDataset.items():
            if len(v)>0 and initpass==True:
                if os.path.exists(v[0]):
                    shutil.rmtree(v[0])
                    if os.path.exists(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k):
                        shutil.rmtree(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k)
                pandda_run(method,ground_state_entries,initpass)
pandda_run(method,ground_state_entries,initpass)
os.system('chmod -R g+rw '+path+'/fragmax/results/pandda/')
'''
                       )

        script = project_script(proj, f"panddaRUN_{proj.protein}{method}.sh")
        methodshort = proc[:2] + ref[:2]
        log_prefix = os.path.join(proj.data_path(), "fragmax", "logs", f"panddarun_{proj.protein}{method}_%j_")
        with open(script, "w") as outp:
            outp.write('#!/bin/bash\n')
            outp.write('#!/bin/bash\n')
            outp.write('#SBATCH -t 08:00:00\n')
            outp.write('#SBATCH -J PDD' + methodshort + '\n')
            outp.write('#SBATCH --exclusive\n')
            outp.write('#SBATCH -N1\n')
            outp.write('#SBATCH --cpus-per-task=48\n')
            outp.write('#SBATCH --mem=220000\n')
            outp.write('#SBATCH -o ' + log_prefix + 'out.txt\n')
            outp.write('#SBATCH -e ' + log_prefix + 'err.txt\n')
            outp.write('module purge\n')
            outp.write('module add CCP4/7.0.077-SHELX-ARP-8.0-0a-PReSTO PyMOL\n')
            outp.write('python ' + py_script + ' ' + proj.data_path() + ' ' + method + ' '
                       + proj.protein + ' ' + proj.library + ' ' + ",".join(proj.shifts()) + '\n')

        t1 = threading.Thread(target=pandda_worker, args=(method, proj))
        t1.daemon = True
        t1.start()

        return render(request, "fragview/jobs_submitted.html", {"command": panddaCMD})


def giant_score(proj, method):
    res_dir = os.path.join(project_results_dir(proj), "pandda", proj.protein, method)
    pandda_dir = os.path.join(res_dir, "pandda")
    export_dir = os.path.join(res_dir, "pandda-export")

    header = '''#!/bin/bash\n'''
    header += '''#!/bin/bash\n'''
    header += '''#SBATCH -t 00:05:00\n'''
    header += '''#SBATCH -J GiantScore\n'''
    header += '''#SBATCH --nice=25\n'''
    header += '''#SBATCH --cpus-per-task=1\n'''
    header += '''#SBATCH --mem=2500\n'''
    header += '''sleep 15000\n'''

    script = project_script(proj, "giant_holder.sh")
    utils.write_script(script, header)
    hpc.run_sbatch(script)

    rn = str(randint(10000, 99999))
    jname = "Gnt" + rn
    header = '''#!/bin/bash\n'''
    header += '''#!/bin/bash\n'''
    header += '''#SBATCH -t 02:00:00\n'''
    header += '''#SBATCH -J ''' + jname + '''\n'''
    header += '''#SBATCH --nice=25\n'''
    header += '''#SBATCH --cpus-per-task=2\n'''
    header += '''#SBATCH --mem=5000\n'''
    header += '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/pandda_export_%j.out\n'''
    header += '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/pandda_export_%j.err\n\n'''
    header += '''module purge\n'''
    header += '''module load CCP4 Phenix\n'''

    panddaExport = f"pandda.export pandda_dir='{pandda_dir}' export_dir='{export_dir}'"

    export_script = project_script(proj, "pandda-export.sh")
    utils.write_script(export_script, header+panddaExport)
    hpc.frontend_run(export_script)

    header = '''#!/bin/bash\n'''
    header += '''#!/bin/bash\n'''
    header += '''#SBATCH -t 02:00:00\n'''
    header += '''#SBATCH -J ''' + jname + '''\n'''
    header += '''#SBATCH --nice=25\n'''
    header += '''#SBATCH --cpus-per-task=1\n'''
    header += '''#SBATCH --mem=2500\n'''
    header += '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/pandda_giant_%j_out.txt\n'''
    header += '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/pandda_giant_%j_err.txt\n\n'''
    header += '''module purge\n'''
    header += '''module load CCP4 Phenix\n'''

    _dirs = glob(f"{export_dir}/*")

    line = "#! /bin/bash"
    line += f"\njid1=$(sbatch {export_script})"
    line += "\njid1=`echo $jid1|cut -d ' ' -f4`"

    for _dir in _dirs:
        dataset = _dir.split("/")[-1]

        src = os.path.join(res_dir, dataset, "final_original.mtz")
        dst = os.path.join(export_dir, dataset, f"{dataset}-pandda-input.mtz")

        cpcmd3 = "cp -f " + src + " " + dst
        if "Apo" not in _dir:
            try:
                ens = glob(_dir + "/*ensemble*.pdb")[0]
                make_restraints = "giant.make_restraints " + ens + " all=True resname=XXX"
                inp_mtz = ens.replace("-ensemble-model.pdb", "-pandda-input.mtz")
                frag = _dir.split("/")[-1].split("-")[-1].split("_")[0]
                quick_refine = \
                    "giant.quick_refine " + ens + " " + inp_mtz + " " + frag + \
                    ".cif multi-state-restraints.refmac.params resname=XXX"
            except Exception:
                make_restraints = ""
                quick_refine = ""

        script = project_script(proj, f"giant_pandda_{frag}.sh")
        utils.write_script(script,
                           f"{header}\n"
                           f"cd {_dir}\n{cpcmd3}\n{make_restraints}\n{quick_refine}")

        line += "\nsbatch  --dependency=afterany:$jid1 " + script
        line += "\nsleep 0.1"

    pandda_score_script = project_script(proj, "pandda-score.sh")
    giant_worker_script = project_script(proj, "giant_worker.sh")

    utils.write_script(giant_worker_script,
                       f"{line}\n\n"
                       f"sbatch --dependency=singleton --job-name={jname} {pandda_score_script}")

    header = '''#!/bin/bash\n'''
    header += '''#!/bin/bash\n'''
    header += '''#SBATCH -t 02:00:00\n'''
    header += '''#SBATCH -J ''' + jname + '''\n'''
    header += '''#SBATCH --nice=25\n'''
    header += '''#SBATCH --cpus-per-task=2\n'''
    header += '''#SBATCH --mem=2000\n'''
    header += '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/pandda_score_%j_out.txt\n'''
    header += '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/pandda_score_%j_err.txt\nn'''
    header += '''module purge\n'''
    header += '''module load CCP4 Phenix\n\n'''

    scores_dir = os.path.join(res_dir, "pandda-scores")
    scoreModel = f'giant.score_model_multiple out_dir="{scores_dir}" {export_dir}/* res_names="XXX" cpu=24'

    body = ""
    for _dir in _dirs:
        dataset = _dir.split("/")[-1]

        src = path.join(res_dir, dataset, "final_original.mtz")
        dst = path.join(export_dir, dataset, f"{dataset}-pandda-input.mtz")

        body += f"\ncp -f " + src + " " + dst

    scorecmd = \
        f"\necho 'source $HOME/Apps/CCP4/ccp4-7.0/bin/ccp4.setup-sh;{scoreModel}' | ssh -F ~/.ssh/ w-guslim-cc-0"

    utils.write_script(pandda_score_script,
                       f"{header}{body}{scorecmd}")

    hpc.frontend_run(giant_worker_script)


def pandda_worker(method, proj):
    rn = str(randint(10000, 99999))

    header = '''#!/bin/bash\n'''
    header += '''#!/bin/bash\n'''
    header += '''#SBATCH -t 00:15:00\n'''
    header += '''#SBATCH -J PnD''' + rn + '''\n'''
    # header+='''#SBATCH --nice=25\n'''
    header += '''#SBATCH --cpus-per-task=1\n'''
    header += '''#SBATCH --mem=2500\n'''
    header += '''#SBATCH -o ''' + proj.data_path() + '''/fragmax/logs/pandda_prepare_''' + \
              proj.protein + '''_%j_out.txt\n'''
    header += '''#SBATCH -e ''' + proj.data_path() + '''/fragmax/logs/pandda_prepare_''' + \
              proj.protein + '''_%j_err.txt\n'''
    header += '''module purge\n'''
    header += '''module load CCP4 Phenix\n'''

    fragDict = dict()
    for _dir in glob(f"{project_process_dir(proj)}/fragment/{proj.library}/*"):
        fragDict[_dir.split("/")[-1]] = _dir

    if "best" in method:

        selectedDict = {
            x.split("/")[-4]: x
            for x in sorted(glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/*/*/final.pdb"))
        }
        for dataset in selectedDict.keys():
            selectedDict[dataset] = get_best_alt_dataset(proj, dataset)
    else:
        method_dir = method.replace("_", "/")
        datasetList = set([x.split("/")[-4] for x in glob(f"{proj.data_path()}/fragmax/results/*/*/*/final.pdb")])
        selectedDict = {
            x.split("/")[-4]: x
            for x in sorted(glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*/{method_dir}/*/final.pdb"))
        }
        missingDict = set(datasetList) - set(selectedDict)

        for dataset in missingDict:
            selectedDict[dataset] = get_best_alt_dataset(proj, dataset)

    pandda_selection = f"{proj.data_path()}/fragmax/results/{proj.protein}*/{method_dir}/selection.json"
    with open(pandda_selection, "w") as writeFile:
        writeFile.write(json.dumps(selectedDict))  # use `json.loads` to do the reverse

    for dataset, pdb in selectedDict.items():
        if os.path.exists(pdb):
            fset = dataset.split("-")[-1]
            script = project_script(proj, f"pandda_prepare_{proj.protein}{fset}.sh")
            with open(script, "w") as writeFile:
                writeFile.write(header)
                frag = dataset.split("-")[-1].split("_")[0]
                hklin = pdb.replace(".pdb", ".mtz")
                output_dir = os.path.join(proj.data_path(), "fragmax", "results",
                                          "pandda", proj.protein, method, dataset)
                os.makedirs(output_dir, exist_ok=True)
                hklout = os.path.join(output_dir, "final.mtz")

                cmdcp1 = f"cp {pdb} " + os.path.join(output_dir, "final.pdb")

                cmd = """mtzdmp """ + hklin
                output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")

                for i in output.splitlines():
                    if "A )" in i:
                        resHigh = i.split()[-3]
                    if "free" in i.lower() and "flag" in i.lower():
                        freeRflag = i.split()[-1]

                cad_fill = '''echo -e " monitor BRIEF\\n labin file 1 -\\n  ALL\\n resolution file 1 999.0 ''' + \
                           resHigh + '''" | cad hklin1 ''' + hklin + ''' hklout ''' + hklout
                uniqueify = '''uniqueify -f ''' + freeRflag + ''' ''' + hklout + ''' ''' + hklout
                hklout_rfill = hklout.replace(".mtz", "_rfill.mtz")

                freerflag = '''echo -e "COMPLETE FREE=''' + freeRflag + ''' \\nEND" | freerflag hklin ''' + \
                            hklout + ''' hklout ''' + hklout_rfill

                # Find F and SIGF flags for phenix maps
                cmd = """mtzdmp """ + hklout_rfill
                output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
                flags = ""
                for i in output.splitlines():
                    if "H K L " in i:
                        flags = i.split()
                fsigf_Flag = ""
                if "F" in flags and "SIGF" in flags:
                    fsigf_Flag = "maps.input.reflection_data.labels=F,SIGF"
                phenix_maps = \
                    "phenix.maps " + hklout_rfill + " " + hklout.replace(".mtz", ".pdb") + " " + \
                    fsigf_Flag + "; mv " + hklout + " " + \
                    hklout.replace(".mtz", "_original.mtz") + "; mv " + \
                    hklout.replace(".mtz", "_map_coeffs.mtz") + " " + hklout

                writeFile.write(cmdcp1 + "\n")
                writeFile.write(cad_fill + "\n")
                writeFile.write(uniqueify + "\n")
                writeFile.write(freerflag + "\n")
                writeFile.write(phenix_maps + "\n")

                if "Apo" not in dataset:
                    frag_cif = f"{frag}.cif"
                    frag_pdb = f"{frag}.pdb"
                    dest_dir = os.path.join(
                        proj.data_path(), "fragmax", "results", "pandda", proj.protein, method, dataset)

                    writeFile.write(
                        f"cp {os.path.join(fragDict[frag], frag_cif)} {os.path.join(dest_dir, frag_cif)}\n"
                        f"cp {os.path.join(fragDict[frag], frag_pdb)} {os.path.join(dest_dir, frag_pdb)}\n")

            hpc.run_sbatch(script)
            # os.remove(script)

    script = project_script(proj, f"panddaRUN_{proj.protein}{method}.sh")
    hpc.run_sbatch(script, f"--dependency=singleton --job-name=PnD{rn}")
    os.remove(script)


def get_best_alt_dataset(proj, dataset):
    optionList = glob(f"{proj.data_path()}/fragmax/results/{dataset}/*/*/final.pdb")
    rwork_res = list()
    r_work = ""
    resolution = ""
    if optionList == []:
        return ""
    else:
        for pdb in optionList:
            with open(pdb, "r") as readFile:
                pdb_file = readFile.readlines()
            for line in pdb_file:
                if "REMARK Final:" in line:
                    r_work = line.split()[4]
                if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
                    resolution = line.split(":")[-1].replace(" ", "").replace("\n", "")
            rwork_res.append((pdb, r_work, resolution))
        rwork_res.sort(key=lambda pair: pair[1:3])
        return rwork_res[0][0]
