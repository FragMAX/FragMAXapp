import os
import csv
from glob import glob
import xmltodict
import natsort
import pyfastcopy  # noqa
import shutil
import subprocess
import itertools

from django.shortcuts import render

from fragview.projects import project_all_status_file, project_shift_dirs, project_process_dir, project_results_dir
from fragview.projects import current_project, project_static_url, project_results_file


def set_details(request):
    proj = current_project(request)

    dataset = str(request.GET["proteinPrefix"])
    prefix = dataset.split(";")[0]
    images = dataset.split(";")[1]
    run = dataset.split(";")[2]

    images = str(int(images) / 2)

    curp = proj.data_path()
    xmlfile = os.path.join(proj.data_path(), "fragmax", "process", proj.protein, prefix, prefix + "_" + run + ".xml")
    datainfo = retrieve_parameters(xmlfile)

    energy = format(12.4 / float(datainfo["wavelength"]), ".2f")
    totalExposure = format(float(datainfo["exposureTime"]) * float(datainfo["numberOfImages"]), ".2f")
    edgeResolution = str(float(datainfo["resolution"]) * 0.75625)
    ligpng = "/static/img/nolig.png"
    if "Apo" not in prefix.split("-"):
        ligpng = prefix.split("-")[-1]

    fragConc = "10 mM"
    solventConc = "10%"
    soakTime = "2h"

    snapshot1 = datainfo["snapshot1"].replace("/mxn/groups/ispybstorage/", "/static/")
    if datainfo["snapshot2"] == "None":
        snapshot2 = datainfo["snapshot1"].replace("/mxn/groups/ispybstorage/", "/static/")
    else:
        snapshot2 = datainfo["snapshot2"].replace("/mxn/groups/ispybstorage/", "/static/")

    diffraction1 = \
        proj.data_path() + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "_1.jpeg"
    if not os.path.exists(diffraction1):
        h5data = datainfo["imageDirectory"] + "/" + prefix + "_" + run + "_data_0000"
        cmd = "adxv -sa -slabs 10 -weak_data " + h5data + "01.h5 " + diffraction1
        subprocess.call(cmd, shell=True)
    diffraction1 = diffraction1.replace("/data/visitors/", "/static/")

    diffraction2 = \
        proj.data_path() + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" + run + "_2.jpeg"
    if not os.path.exists(diffraction2):
        half = int(float(images) / 200)
        if half < 10:
            half = "0" + str(half)
        h5data = datainfo["imageDirectory"] + "/" + prefix + "_" + run + "_data_0000"
        cmd = "adxv -sa -slabs 10 -weak_data " + h5data + half + ".h5 " + diffraction2
        subprocess.call(cmd, shell=True)
    diffraction2 = diffraction2.replace("/data/visitors/", "/static/")

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

    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/xdsapp/results_" + prefix + "_" + run + "_data.txt"):
        xdsappOK = "ready"
    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/dials/xia2.html"):
        dialsOK = "ready"
    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/xdsxscale/xia2.html"):
        xdsOK = "ready"
    if os.path.exists(
            curp + "/fragmax/process/" + proj.protein + "/" + prefix + "/" + prefix + "_" +
            run + "/autoproc/summary.html"):
        autoprocOK = "ready"
    if os.path.exists(
            curp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" +
            run + "_1/EDNA_proc/results/ep_" + prefix + "_" + run + "_phenix_xtriage_noanom.log"):
        ednaOK = "ready"
    if os.path.exists(
            curp + "/process/" + proj.protein + "/" + prefix + "/xds_" + prefix + "_" +
            run + "_1/fastdp/results/ap_" + prefix + "_run" + run + "_noanom_fast_dp.log"):
        fastdpOK = "ready"

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

    return render(request, 'fragview/dataset_info.html', {
        "csvfile": lines,
        "shift": curp.split("/")[-1],
        "run": run,
        'imgprf': prefix,
        'imgs': images,
        "ligand": ligpng,
        "fragConc": fragConc,
        "solventConc": solventConc,
        "soakTime": soakTime,
        "axisEnd": datainfo["axisEnd"],
        "axisRange": datainfo["axisRange"],
        "axisStart": datainfo["axisStart"],
        "beamShape": datainfo["beamShape"],
        "beamSizeSampleX": datainfo["beamSizeSampleX"],
        "beamSizeSampleY": datainfo["beamSizeSampleY"],
        "detectorDistance": datainfo["detectorDistance"],
        "endTime": datainfo["endTime"],
        "exposureTime": datainfo["exposureTime"],
        "flux": datainfo["flux"],
        "imageDirectory": datainfo["imageDirectory"],
        "imagePrefix": datainfo["imagePrefix"],
        "kappaStart": datainfo["kappaStart"],
        "numberOfImages": datainfo["numberOfImages"],
        "overlap": datainfo["overlap"],
        "phiStart": datainfo["phiStart"],
        "resolution": datainfo["resolution"],
        "rotatioAxis": datainfo["rotatioAxis"],
        "runStatus": datainfo["runStatus"],
        "slitV": datainfo["slitV"],
        "slitH": datainfo["slitH"],
        "startTime": datainfo["startTime"],
        "synchrotronMode": datainfo["synchrotronMode"],
        "transmission": datainfo["transmission"],
        "wavelength": datainfo["wavelength"],
        "xbeampos": datainfo["xbeampos"],
        "snapshot1": snapshot1,
        "snapshot2": snapshot2,
        "diffraction1": diffraction1,
        "diffraction2": diffraction2,
        "ybeampos": datainfo["ybeampos"],
        "energy": energy,
        "totalExposure": totalExposure,
        "edgeResolution": edgeResolution,
        "acr": prefix.split("-")[0],
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
    })


def retrieve_parameters(xmlfile):
    with open(xmlfile, "r") as inp:
        a = inp.readlines()

    paramDict = dict()
    paramDict["axisEnd"] = format(float(a[4].split("</")[0].split(">")[1]), ".1f")
    paramDict["axisRange"] = format(float(a[5].split("</")[0].split(">")[1]), ".1f")
    paramDict["axisStart"] = format(float(a[6].split("</")[0].split(">")[1]), ".1f")
    paramDict["beamShape"] = a[7].split("</")[0].split(">")[1]
    paramDict["beamSizeSampleX"] = format(float(a[8].split("</")[0].split(">")[1]) * 1000, ".0f")
    paramDict["beamSizeSampleY"] = format(float(a[9].split("</")[0].split(">")[1]) * 1000, ".0f")
    paramDict["detectorDistance"] = format(float(a[16].split("</")[0].split(">")[1]), ".2f")
    paramDict["endTime"] = a[18].split("</")[0].split(">")[1]
    paramDict["exposureTime"] = format(float(a[19].split("</")[0].split(">")[1]), ".3f")
    paramDict["flux"] = a[22].split("</")[0].split(">")[1]
    paramDict["imageDirectory"] = a[23].split("</")[0].split(">")[1]
    paramDict["imagePrefix"] = a[24].split("</")[0].split(">")[1]
    paramDict["kappaStart"] = format(float(a[26].split("</")[0].split(">")[1]), ".2f")
    paramDict["numberOfImages"] = a[27].split("</")[0].split(">")[1]
    paramDict["overlap"] = format(float(a[29].split("</")[0].split(">")[1]), ".1f")
    paramDict["phiStart"] = format(float(a[30].split("</")[0].split(">")[1]), ".2f")
    paramDict["resolution"] = format(float(a[32].split("</")[0].split(">")[1]), ".2f")
    paramDict["rotatioAxis"] = a[33].split("</")[0].split(">")[1]
    paramDict["runStatus"] = a[34].split("</")[0].split(">")[1]
    paramDict["slitV"] = format(float(a[35].split("</")[0].split(">")[1]) * 1000, ".1f")
    paramDict["slitH"] = format(float(a[36].split("</")[0].split(">")[1]) * 1000, ".1f")
    paramDict["startTime"] = a[38].split("</")[0].split(">")[1]
    paramDict["synchrotronMode"] = a[39].split("</")[0].split(">")[1]
    paramDict["transmission"] = format(float(a[40].split("</")[0].split(">")[1]), ".3f")
    paramDict["wavelength"] = format(float(a[41].split("</")[0].split(">")[1]), ".6f")
    paramDict["xbeampos"] = format(float(a[42].split("</")[0].split(">")[1]), ".2f")
    paramDict["snapshot1"] = a[43].split("</")[0].split(">")[1]
    paramDict["snapshot2"] = a[44].split("</")[0].split(">")[1]
    paramDict["snapshot3"] = a[45].split("</")[0].split(">")[1]
    paramDict["snapshot4"] = a[46].split("</")[0].split(">")[1]
    paramDict["ybeampos"] = format(float(a[47].split("</")[0].split(">")[1]), ".2f")

    return paramDict


def show_all(request):
    proj = current_project(request)

    resyncAction = str(request.GET.get("resyncdsButton"))
    resyncStatus = str(request.GET.get("resyncstButton"))

    datacollection_summary(proj)

    if "resyncDataset" in resyncAction:
        datacollection_summary(proj)

    if "resyncStatus" in resyncStatus:
        # os.remove(proj.data_path() + "/fragmax/process/" + proj.protein + "/datacollections.csv")
        # get_project_status(proj)
        # datacollection_summary(proj)
        resync_status_project(proj)

    with open(proj.data_path() + "/fragmax/process/" + proj.protein + "/datacollections.csv", "r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)

        acr_list = [x[3] for x in lines[1:]]
        smp_list = [x[1] for x in lines[1:]]
        prf_list = [x[0] for x in lines[1:]]
        res_list = [x[6] for x in lines[1:]]
        img_list = [x[5] for x in lines[1:]]
        path_list = [x[2] for x in lines[1:]]
        snap_list = [x[7].split(",")[0].replace("/mxn/groups/ispybstorage/", "/static/") for x in lines[1:]]
        png_list = [x[8] for x in lines[1:]]
        run_list = [x[4] for x in lines[1:]]

    if not os.path.exists(project_all_status_file(proj)):
        get_project_status(proj)

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

    results = zip(img_list, prf_list, res_list, path_list, snap_list, acr_list,
                  png_list, run_list, smp_list, dpentry, rfentry, lgentry)

    return render(request, "fragview/datasets.html", {"files": results})


def datacollection_summary(proj):
    lists = list()
    for s in proj.shifts():
        lists += glob(
            "/data/visitors/biomax/" + proj.proposal + "/" + s + "/process/" + proj.protein +
            "/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")

    data_collections_dir = os.path.join(proj.data_path(), "fragmax", "process", proj.protein)
    data_collections_file = os.path.join(data_collections_dir, "datacollections.csv")

    if os.path.exists(data_collections_file):
        return
    else:
        # Create basic folders for a new project
        os.makedirs(data_collections_dir, mode=0o760, exist_ok=True)
        os.makedirs(os.path.join(proj.data_path(), "fragmax", "logs"), mode=0o770, exist_ok=True)
        os.makedirs(os.path.join(proj.data_path(), "fragmax", "scripts"), mode=0o770, exist_ok=True)
        os.makedirs(os.path.join(proj.data_path(), "fragmax", "models"), mode=0o770, exist_ok=True)
        os.makedirs(os.path.join(proj.data_path(), "fragmax", "export"), mode=0o770, exist_ok=True)
        os.makedirs(os.path.join(proj.data_path(), "fragmax", "results"), mode=0o770, exist_ok=True)

        with open(data_collections_file, "w") as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([
                "imagePrefix", "SampleName", "dataCollectionPath", "Acronym", "dataCollectionNumber",
                "numberOfImages", "resolution", "snapshot", "ligsvg"])

            for xml in natsort.natsorted(lists, key=lambda x: ("Apo" in x, x)):
                outdirxml = xml.replace("/process/", "/fragmax/process/").split("fastdp")[0].replace("xds_", "")[:-3]
                if not os.path.exists(outdirxml + ".xml"):
                    if not os.path.exists("/".join(outdirxml.split("/")[:-1])):
                        os.makedirs("/".join(outdirxml.split("/")[:-1]))
                    shutil.copyfile(xml, outdirxml + ".xml")

                with open(xml, "r") as fd:
                    doc = xmltodict.parse(fd.read())

                nIMG = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["numberOfImages"]
                resolution = "%.2f" % float(doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["resolution"])
                run = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["dataCollectionNumber"]
                dataset = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["imagePrefix"]
                sample = dataset.split("-")[-1]
                snaps = ",".join(
                    [doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["xtalSnapshotFullPath" + i]
                     for i in ["1", "2", "3", "4"]
                     if
                     doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["xtalSnapshotFullPath" + i] != "None"]
                )

                if len(snaps) < 1:
                    snaps = "noSnapshots"
                colPath = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["imageDirectory"]

                if "Apo" in doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["imagePrefix"]:
                    ligsvg = "/static/img/apo.png"
                else:
                    ligsvg = f"{project_static_url(proj)}/fragmax/process/fragment/" \
                             f"{proj.library}/{sample}/{sample}.svg"

                writer.writerow([dataset, sample, colPath, proj.protein, run, nIMG, resolution, snaps, ligsvg])


def get_project_status(proj):
    statusDict = dict()
    procList = list()
    resList = list()

    for shift_dir in project_shift_dirs(proj):
        procList += [
            "/".join(x.split("/")[:8]) + "/" + x.split("/")[-2] + "/" for x in
            glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/*/")]
        resList += glob(f"{shift_dir}/fragmax/results/{proj.protein}*/")

    for i in procList:
        dataset_run = i.split("/")[-2]
        statusDict[dataset_run] = {
            "autoproc": "none",
            "dials": "none",
            "EDNA": "none",
            "fastdp": "none",
            "xdsapp": "none",
            "xdsxscale": "none",
            "dimple": "none",
            "fspipeline": "none",
            "buster": "none",
            "rhofit": "none",
            "ligfit": "none",
        }

    for result in resList:
        dts = result.split("/")[-2]
        if dts not in statusDict:
            statusDict[dts] = {
                "autoproc": "none",
                "dials": "none",
                "EDNA": "none",
                "fastdp": "none",
                "xdsapp": "none",
                "xdsxscale": "none",
                "dimple": "none",
                "fspipeline": "none",
                "buster": "none",
                "rhofit": "none",
                "ligfit": "none",
            }

        for j in glob(result + "*"):
            if os.path.exists(j + "/dimple/final.pdb"):
                statusDict[dts].update({"dimple": "full"})

            if os.path.exists(j + "/fspipeline/final.pdb"):
                statusDict[dts].update({"fspipeline": "full"})

            if os.path.exists(j + "/buster/final.pdb"):
                statusDict[dts].update({"buster": "full"})

            if glob(j + "/*/ligfit/LigandFit*/ligand_fit_*.pdb") != []:
                statusDict[dts].update({"ligfit": "full"})

            if glob(j + "/*/rhofit/best.pdb") != []:
                statusDict[dts].update({"rhofit": "full"})

    for process in procList:
        dts = process.split("/")[-2]
        j = list()

        for shift_dir in project_shift_dirs(proj):
            j += glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/{dts}/")

        if j != []:
            j = j[0]

        if glob(j + "/autoproc/*staraniso*.mtz") + glob(j + "/autoproc/*aimless*.mtz") != []:
            statusDict[dts].update({"autoproc": "full"})

        if glob(j + "/dials/DataFiles/*mtz") != []:
            statusDict[dts].update({"dials": "full"})

        ej = list()
        for shift_dir in project_shift_dirs(proj):
            ej += glob(f"{shift_dir}/process/{proj.protein}/*/*{dts}*/EDNA_proc/results/*mtz")

        if ej != []:
            statusDict[dts].update({"EDNA": "full"})
        fj = list()

        for shift_dir in project_shift_dirs(proj):
            fj += glob(f"{shift_dir}/process/{proj.protein}/*/*{dts}*/fastdp/results/*mtz.gz")

        if fj != []:
            statusDict[dts].update({"fastdp": "full"})

        if glob(j + "/xdsapp/*mtz") != []:
            statusDict[dts].update({"xdsapp": "full"})

        if glob(j + "/xdsxscale/DataFiles/*mtz") != []:
            statusDict[dts].update({"xdsxscale": "full"})

    with open(project_all_status_file(proj), "w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["dataset", "run", "autoproc", "dials", "EDNA", "fastdp", "xdsapp",
                         "xdsxscale", "dimple", "fspipeline", "buster", "ligfit", "rhofit"])
        for dataset_run, status in statusDict.items():
            writer.writerow([dataset_run] + list(status.values()))


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
