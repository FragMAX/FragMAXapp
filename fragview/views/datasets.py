import os
import csv
from glob import glob
import pyfastcopy  # noqa
import itertools

from django.shortcuts import render

from fragview.projects import project_all_status_file, project_process_dir
from fragview.projects import current_project, project_results_file, project_results_dir
from fragview.projects import project_data_collections_file
from fragview.xsdata import XSDataCollection
from fragview import versions


def set_details(request):
    proj = current_project(request)

    dataset = str(request.GET["proteinPrefix"])
    prefix = dataset.split(";")[0]
    images = dataset.split(";")[1]
    run = dataset.split(";")[2]

    images = str(int(images) / 2)

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

    snapshots = [
        spath.replace("/mxn/groups/ispybstorage/", "/static/")
        for spath in xsdata.snapshots
    ]

    half = int(float(images) / 200)

    # getreports
    scurp = curp.replace("/data/visitors/", "/static/")
    xdsappreport = \
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + \
        "/xdsapp/results_" + prefix + "_" + run + "_data.txt"

    dialsreport = \
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "/dials/xia2.html"

    xdsreport = \
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "/xdsxscale/xia2.html"

    autoprocreport = \
        scurp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + \
        "/autoproc/summary.html"

    ednareport = \
        scurp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" + run + \
        "_1/EDNA_proc/results/ep_" + prefix + "_" + run + "_phenix_xtriage_noanom.log"

    fastdpreport = \
        scurp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" + run + \
        "_1/fastdp/results/ap_" + prefix + "_run" + run + "_noanom_fast_dp.log"

    xdsappOK = "no"
    dialsOK = "no"
    xdsOK = "no"
    autoprocOK = "no"
    ednaOK = "no"
    fastdpOK = "no"
    fastdpLogs = ""
    ednaLogs = ""
    autoprocLogs = ""
    xdsappLogs = ""
    xdsLogs = ""
    dialsLogs = ""

    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/xdsapp/results_" + prefix + "_" + run + "_data.txt"):
        xdsappOK = "ready"
        searchPath = curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + \
            run + "/xdsapp"
        logPaths = [x for x in glob(f"{searchPath}/*") if "txt" in x or "LP" in x or "log" in x]
        logNames = [x.split("/")[-1] for x in logPaths]
        xdsappLogs = list(zip(logNames, logPaths))
    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/dials/xia2.html"):
        dialsOK = "ready"
        searchPath = curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + \
            run + "/dials/LogFiles"
        logPaths = [x for x in glob(f"{searchPath}/*") if "txt" in x or "LP" in x or "log" in x]
        logNames = [x.split("/")[-1] for x in logPaths]
        dialsLogs = list(zip(logNames, logPaths))
    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/xdsxscale/xia2.html"):
        xdsOK = "ready"
        searchPath = curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + \
            run + "/xdsxscale/LogFiles"
        logPaths = [x for x in glob(f"{searchPath}/*") if "txt" in x or "LP" in x or "log" in x]
        logNames = [x.split("/")[-1] for x in logPaths]
        xdsLogs = list(zip(logNames, logPaths))
    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/autoproc/summary.html"):
        autoprocOK = "ready"
        searchPath = curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + \
            run + "/autoproc/"
        logPaths = [x for x in glob(f"{searchPath}/*") if "txt" in x or "LP" in x or "log" in x]
        logNames = [x.split("/")[-1] for x in logPaths]
        autoprocLogs = list(zip(logNames, logPaths))
    if os.path.exists(
            curp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" +
            run + "_1/EDNA_proc/results/ep_" + prefix + "_" + run + "_phenix_xtriage_noanom.log"):
        ednaOK = "ready"
        searchPath = curp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" + \
            run + "_1/EDNA_proc/results/"
        logPaths = [x for x in glob(f"{searchPath}/*") if "txt" in x or "LP" in x or "log" in x]
        logNames = [x.split("/")[-1] for x in logPaths]
        ednaLogs = list(zip(logNames, logPaths))
    if os.path.exists(
            curp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" +
            run + "_1/fastdp/results/ap_" + prefix + "_run" + run + "_noanom_fast_dp.log"):
        fastdpOK = "ready"
        searchPath = curp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + '_' + \
            run + "_1/fastdp/results/"
        logPaths = [x for x in glob(f"{searchPath}/*") if "txt" in x or "LP" in x or "log" in x]
        logNames = [x.split("/")[-1] for x in logPaths]
        fastdpLogs = list(zip(logNames, logPaths))

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
    # beamline parameters
    BL_site = f"{versions.BL_site}"
    BL_name = f"{versions.BL_name}"
    BL_detector = f"{versions.BL_detector}"
    BL_detector_type = f"{versions.BL_detector_type}"
    BL_detector_pixel_size = f"{versions.BL_detector_pixel_size}"
    BL_focusing_optics = f"{versions.BL_focusing_optics}"
    BL_monochrom_type = f"{versions.BL_monochrom_type}"
    BL_beam_shape = f"{versions.BL_beam_shape}"
    BL_beam_divergence = f"{versions.BL_beam_divergence}"
    BL_polarisation = f"{versions.BL_polarisation}"
    return render(request, "fragview/dataset_info.html", {
        "csvfile": lines,
        "shift": curp.split("/")[-1],
        "run": run,
        'imgprf': prefix,
        'imgs': images,
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
        "ednaOK": ednaOK,
        "fastdpOK": fastdpOK,
        "fastdpLogs": fastdpLogs,
        "ednaLogs": ednaLogs,
        "autoprocLogs": autoprocLogs,
        "xdsappLogs": xdsappLogs,
        "xdsLogs": xdsLogs,
        "dialsLogs": dialsLogs,
        "BL_site": BL_site,
        "BL_name": BL_name,
        "BL_detector": BL_detector,
        "BL_detector_type": BL_detector_type,
        "BL_detector_pixel_size": BL_detector_pixel_size,
        "BL_focusing_optics": BL_focusing_optics,
        "BL_monochrom_type": BL_monochrom_type,
        "BL_beam_shape": BL_beam_shape,
        "BL_beam_divergence": BL_beam_divergence,
        "BL_polarisation": BL_polarisation
    })


def show_all(request):
    def _sample_2_fragment(sample):
        if sample.startswith("Apo"):
            return None

        return sample

    proj = current_project(request)

    resyncStatus = str(request.GET.get("resyncstButton"))

    if "resyncStatus" in resyncStatus:
        resync_status_project(proj)

    with open(project_data_collections_file(proj), "r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)

        acr_list = [x[3] for x in lines[1:]]
        smp_list = [x[1] for x in lines[1:]]
        fragments_list = [_sample_2_fragment(sample) for sample in smp_list]
        prf_list = [x[0] for x in lines[1:]]
        res_list = [x[6] for x in lines[1:]]
        img_list = [x[5] for x in lines[1:]]
        path_list = [x[2] for x in lines[1:]]
        snap_list = [x[7].split(",")[0].replace("/mxn/groups/ispybstorage/", "/static/") for x in lines[1:]]
        snap2_list = [x.replace("1.snapshot.jpeg", "2.snapshot.jpeg") for x in snap_list]
        run_list = [x[4] for x in lines[1:]]

    dpentry = list()
    rfentry = list()
    lgentry = list()

    if os.path.exists(project_all_status_file(proj)):
        with open(project_all_status_file(proj), "r") as csvFile:
            reader = csv.reader(csvFile)
            lines = list(reader)[1:]

        for i, j in zip(prf_list, run_list):
            dictEntry = i + "_" + j
            status = [line for line in lines if line[0] == dictEntry]

            if status != []:
                da = "<td>"
                if status[0][1] == "full":
                    da += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> autoPROC</font></p>'
                elif status[0][1] == "partial":
                    da += '<p align="left"><font size="2" color="yellow">&#9679;</font>' \
                          '<font size="2"> autoPROC</font></p>'
                else:
                    da += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> autoPROC</font></p>'

                if status[0][2] == "full":
                    da += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> DIALS</font></p>'
                elif status[0][2] == "partial":
                    da += '<p align="left"><font size="2" color="yellow">&#9679;</font>' \
                          '<font size="2"> DIALS</font></p>'
                else:
                    da += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> DIALS</font></p>'

                if status[0][3] == "full":
                    da += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> EDNA_proc</font></p>'
                elif status[0][3] == "partial":
                    da += '<p align="left"><font size="2" color="yellow">&#9679;</font>' \
                          '<font size="2"> EDNA_proc</font></p>'
                else:
                    da += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> EDNA_proc</font></p>'

                if status[0][4] == "full":
                    da += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> Fastdp</font></p>'
                elif status[0][4] == "partial":
                    da += '<p align="left"><font size="2" color="yellow">&#9679;</font>' \
                          '<font size="2"> Fastdp</font></p>'
                else:
                    da += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> Fastdp</font></p>'

                if status[0][5] == "full":
                    da += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> XDSAPP</font></p>'
                elif status[0][5] == "partial":
                    da += '<p align="left"><font size="2" color="yellow">&#9679;</font>' \
                          '<font size="2"> XDSAPP</font></p>'
                else:
                    da += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> XDSAPP</font></p>'

                if status[0][6] == "full":
                    da += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> XDS/XSCALE</font></p>'

                elif status[0][6] == "partial":
                    da += '<p align="left"><font size="2" color="yellow">&#9679;</font>' \
                          '<font size="2"> XDS/XSCALE</font></p>'
                else:
                    da += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> XDS/XSCALE</font></p></td>'

                dpentry.append(da)
                re = "<td>"

                if status[0][9] == "full":
                    re += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> BUSTER</font></p>'
                else:
                    re += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> BUSTER</font></p>'

                if status[0][7] == "full":
                    re += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> Dimple</font></p>'
                else:
                    re += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> Dimple</font></p>'

                if status[0][8] == "full":
                    re += '<p align="left"><font size="2" color="green">&#9679;</font>' \
                          '<font size="2"> FSpipeline</font></p></td>'
                else:
                    re += '<p align="left"><font size="2" color="red">&#9675;</font>' \
                          '<font size="2"> FSpipeline</font></p></td>'

                rfentry.append(re)

                lge = "<td>"
                if status[0][10] == "full":
                    lge += \
                        '<p align="left"><font size="2" color="green">&#9679;</font>' \
                        '<font size="2"> LigFit</font></p>'
                else:
                    lge += \
                        '<p align="left"><font size="2" color="red">&#9675;</font>' \
                        '<font size="2"> LigFit</font></p>'

                if status[0][11] == "full":
                    lge += \
                        '<p align="left"><font size="2" color="green">&#9679;</font>' \
                        '<font size="2"> RhoFit</font></p></td>'
                else:
                    lge += \
                        '<p align="left"><font size="2" color="red">&#9675;</font>' \
                        '<font size="2"> RhoFit</font></p></td>'
                lgentry.append(lge)
    else:
        for i in prf_list:
            dpentry.append("""<td>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> autoPROC</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/DIALS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDSAPP</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> fastdp</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> EDNA_proc</font></p>
                </td>""")
            rfentry.append("""<td>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> BUSTER</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Dimple</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> FSpipeline</font></p>
                    </td>""")

        for i, j in zip(prf_list, run_list):
            lge = \
                """<td>
                  <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>
                  <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p>
                 </td>"""
            lgentry.append(lge)

    datasets = zip(img_list, prf_list, res_list, path_list, snap_list, snap2_list, acr_list,
                   fragments_list, run_list, smp_list, dpentry, rfentry, lgentry)

    return render(request, "fragview/datasets.html", {"datasets": datasets})


def proc_report(request):
    method = ""
    report = str(request.GET.get('dataHeader'))
    if "fastdp" in report or "EDNA" in report:
        method = "log"
        with open(report.replace("/static/", "/data/visitors/"), "r") as readFile:
            report = readFile.readlines()
        report = "<br>".join(report)

    return render(request, "fragview/procReport.html", {"reportHTML": report, "method": method})


def get_dataset_status(proj, dataset, run):
    proc_dir = project_process_dir(proj)
    dps1 = glob(f"{proc_dir}/{proj.protein}/{dataset}/{dataset}_{run}/*/*mtz")
    dps2 = glob(f"{proc_dir}/{proj.protein}/{dataset}/{dataset}_{run}/*/*/*mtz")
    dps3 = glob(f"{proj.data_path()}/process/{proj.protein}/{dataset}/*/*/results/*mtz*")

    dp_full = set(
        [x.split("/")[11] for x in dps1 + dps2] + [x.split("/")[10].replace("EDNA_proc", "edna") for x in dps3 if
                                                   "autoPROC" not in x])

    dp_status = {'autoproc': "none",
                 'dials': "none",
                 'edna': "none",
                 'fastdp': "none",
                 'xdsapp': "none",
                 'xdsxscale': "none"}

    for proc in dp_full:
        dp_status[proc] = "full"

    rf_full = set([x.split("/")[10] for x in glob(
        f"/data/visitors/biomax/{proj.proposal}/{proj.shift}/fragmax/results/{dataset}_{run}/*/*/final.pdb")])
    rf_status = {'dimple': "none",
                 'fspipeline': "none",
                 'buster': "none"}
    for ref in rf_full:
        rf_status[ref] = "full"

    res_dir = project_results_dir(proj)

    lg_full = set([x.split("/")[11] for x in
                   glob(f"{res_dir}/{dataset}_{run}/*/*/ligfit/*/*.pdb") +
                   glob(f"{res_dir}/{dataset}_{run}/*/*/rhofit/*.pdb")])
    lg_status = {'rhofit': "none",
                 'ligfit': "none"}
    for lig in lg_full:
        lg_status[lig] = "full"

    d4 = dict(dp_status, **rf_status)
    d4.update(lg_status)

    return d4


def update_all_status_csv(allcsv, dataset, run, statusDict):
    with open(allcsv, 'r') as readFile:
        csvfile = list(csv.reader(readFile))

    # Get index of the dataset to be updated
    for row in csvfile:
        if row[0] == dataset + "_" + run:
            row_to_change = csvfile.index(row)

            # Create the list with new values for process, refine, ligfit status
            # and update the csv file
            updated_value = [dataset + "_" + run] + list(statusDict.values())
            csvfile[row_to_change] = updated_value

            # write the new csv file with updated values
            with open(allcsv, 'w') as writeFile:
                writer = csv.writer(writeFile)
                writer.writerows(csvfile)


def resync_status_project(proj):
    allcsv = f'{proj.data_path()}/fragmax/process/{proj.protein}/allstatus.csv'

    # Copy data from beamline auto processing to fragmax folders
    h5s = list(itertools.chain(
        *[glob(f"/data/visitors/biomax/{proj.proposal}/{p}/raw/{proj.protein}/{proj.protein}*/{proj.protein}*master.h5")
          for p in proj.shifts()]))

    for h5 in h5s:
        dataset, run = (h5.split("/")[-1][:-10].split("_"))
        statusDict = get_dataset_status(proj, dataset, run)
        update_all_status_csv(allcsv, dataset, run, statusDict)
