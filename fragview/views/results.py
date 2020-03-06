import threading
import csv
from glob import glob
from os import path
import pyfastcopy  # noqa
import shutil

from django.shortcuts import render

from fragview.projects import current_project, project_results_file
from fragview.projects import project_results_dir, project_process_protein_dir
from fragview import result_plots
from fragview.views.utils import open_txt


def show(request):
    proj = current_project(request)
    results_file = project_results_file(proj)

    resync = str(request.GET.get("resync"))

    if "resyncresults" in resync or not path.exists(results_file):
        result_summary(proj)

    with open(results_file, "r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]

    return render(request, "fragview/results.html", {"csvfile": lines})


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        threading.Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return


def result_summary(proj):
    def info_func(entry, isaDict):
        usracr, pdbout, dif_map, nat_map, spg, resolution, isa, r_work, r_free, bonds, angles, a, b, c, alpha, \
            beta, gamma, blist, ligfit_dataset, pipeline, rhofitscore, ligfitscore, ligblob = [""] * 23

        pdbout = ""
        usracr = "_".join(entry.split("/")[8:11])
        pipeline = "_".join(entry.split("/")[9:11])
        ka = entry.split("/")[8]
        kb = entry.split("/")[9]
        if kb == "EDNA_proc":
            kb = "edna"  # Updates the name of EDNA taken from file path for isaDict reference
        isa = isaDict[ka][kb]

        if "dimple" in usracr:
            with open(entry, "r") as inp:
                pdb_file = inp.readlines()
            for line in pdb_file:
                if "REMARK   3   FREE R VALUE                     :" in line:
                    r_free = line.split()[-1]
                    r_free = str("{0:.2f}".format(float(r_free)))
                    # bonds=line.split()[10]
                    # angles=line.split()[13]
                if "REMARK   3   R VALUE            (WORKING SET) :" in line:
                    r_work = line.split()[-1]
                    r_work = str("{0:.2f}".format(float(r_work)))
                if "REMARK   3   BOND LENGTHS REFINED ATOMS        (A):" in line:
                    bonds = line.split()[-3]
                if "REMARK   3   BOND ANGLES REFINED ATOMS   (DEGREES):" in line:
                    angles = line.split()[-3]
                if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
                    resolution = line.split(":")[-1].replace(" ", "").replace("\n", "")
                    resolution = str("{0:.2f}".format(float(resolution)))
                if "CRYST1" in line:
                    a = line.split()[1]
                    b = line.split()[2]
                    c = line.split()[3]

                    alpha = line.split()[4]
                    beta = line.split()[5]
                    gamma = line.split()[6]

                    spg = "".join(line.split()[7:])

            entry = entry.replace("final.pdb", "dimple.log")
            with open(entry, "r") as inp:
                dimple_log = inp.readlines()
            blist = []
            for n, line in enumerate(dimple_log):
                if line.startswith("blobs: "):
                    blist = line.split(":")[-1].rstrip()

            pdbout = "/".join(entry.split("/")[3:-1]) + "/final.pdb"
            dif_map = "/".join(entry.split("/")[3:-1]) + "/final_2mFo-DFc.ccp4"
            nat_map = "/".join(entry.split("/")[3:-1]) + "/final_mFo-DFc.ccp4"

        if "buster" in usracr:
            with open(entry, "r") as inp:
                pdb_file = inp.readlines()
            for line in pdb_file:
                if "REMARK   3   R VALUE            (WORKING SET) :" in line:
                    r_work = line.split(" ")[-1]
                    r_work = str("{0:.2f}".format(float(r_work)))
                if "REMARK   3   FREE R VALUE                     :" in line:
                    r_free = line.split(" ")[-1]
                    r_free = str("{0:.2f}".format(float(r_free)))
                if "REMARK   3   BOND LENGTHS                       (A) :" in line:
                    bonds = line.split()[-1]
                if "REMARK   3   BOND ANGLES                  (DEGREES) :" in line:
                    angles = line.split()[-1]
                if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
                    resolution = line.split(":")[-1].replace(" ", "").replace("\n", "")
                    resolution = str("{0:.2f}".format(float(resolution)))
                if "CRYST1" in line:
                    a = line.split()[1]
                    b = line.split()[2]
                    c = line.split()[3]

                    alpha = line.split()[4]
                    beta = line.split()[5]
                    gamma = line.split()[6]

                    spg = "".join(line.split()[7:])

            if not path.exists(entry.replace("refine.pdb", "final.pdb")):
                shutil.copyfile(entry, entry.replace("refine.pdb", "final.pdb"))

            if not path.exists(entry.replace("refine.pdb", "final.mtz")):
                shutil.copyfile(entry.replace("refine.pdb", "refine.mtz"), entry.replace("refine.pdb", "final.mtz"))

            blist = "[]"
            pdbout = "/".join(entry.split("/")[3:-1]) + "/final.pdb"
            dif_map = "/".join(entry.split("/")[3:-1]) + "/final_2mFo-DFc.ccp4"
            nat_map = "/".join(entry.split("/")[3:-1]) + "/final_mFo-DFc.ccp4"

        if "fspipeline" in usracr:

            if path.exists("/".join(entry.split("/")[:-1]) + "/mtz2map.log") and \
                    path.exists("/".join(entry.split("/")[:-1]) + "/blobs.log"):
                with open(entry, "r") as inp:
                    pdb_file = inp.readlines()
                for line in pdb_file:
                    if "REMARK Final:" in line:
                        r_work = line.split()[4]
                        r_free = line.split()[7]
                        r_free = str("{0:.2f}".format(float(r_free)))
                        r_work = str("{0:.2f}".format(float(r_work)))
                        bonds = line.split()[10]
                        angles = line.split()[13]
                    if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
                        resolution = line.split(":")[-1].replace(" ", "").replace("\n", "")
                        resolution = str("{0:.2f}".format(float(resolution)))
                    if "CRYST1" in line:
                        a = line.split()[1]
                        b = line.split()[2]
                        c = line.split()[3]

                        alpha = line.split()[4]
                        beta = line.split()[5]
                        gamma = line.split()[6]

                        spg = "".join(line.split()[7:])

                with open("/".join(entry.split("/")[:-1]) + "/blobs.log", "r") as inp:
                    readFile = inp.readlines()
                    blist = []
                    for line in readFile:
                        if "INFO:: cluster at xyz = " in line:
                            blob = line.split("(")[-1].split(")")[0].replace("  ", "").rstrip()
                            blob = "[" + blob + "]"
                            blist.append(blob)
                            blist = [",".join(blist).replace(" ", "")]
                    try:
                        blist = "[" + blist[0] + "]"
                    except Exception:
                        blist = "[]"
                with open("/".join(entry.split("/")[:-1]) + "/mtz2map.log", "r") as inp:
                    readFile = inp.readlines()
                    for mline in readFile:
                        if "_2mFo-DFc.ccp4" in mline:
                            pdbout = "/".join(entry.split("/")[3:-1]) + "/final.pdb"
                            dif_map = "/".join(entry.split("/")[3:-1]) + "/final_2mFo-DFc.ccp4"
                            nat_map = "/".join(entry.split("/")[3:-1]) + "/final_mFo-DFc.ccp4"

        rhofitscore = "-"
        ligfitscore = "-"
        ligblob = [0, 0, 0]

        res_dir = path.join(
            project_results_dir(proj),
            "_".join(usracr.split("_")[0:2]) + "/" + "/".join(pipeline.split("_")))

        if path.exists("/data/visitors/" + pdbout) and "Apo" not in pdbout:
            ligfitPath = path.join(res_dir, "ligfit")
            rhofitPath = path.join(res_dir, "rhofit")

            if path.exists(rhofitPath):
                hit_corr_log = path.join(rhofitPath, "Hit_corr.log")
                if path.exists(hit_corr_log):
                    with open(hit_corr_log, "r") as inp:
                        rhofitscore = inp.readlines()[0].split()[1]

            if path.exists(ligfitPath):
                try:
                    ligfitRUNPath = sorted(glob(f"{res_dir}/ligfit/LigandFit*"))[-1]
                    if glob(f"{res_dir}/ligfit/LigandFit*") != []:
                        if glob(ligfitRUNPath + "/LigandFit*.log") != []:
                            if path.exists(ligfitRUNPath + "/LigandFit_summary.dat"):
                                with open(ligfitRUNPath + "/LigandFit_summary.dat", "r") as inp:
                                    ligfitscore = inp.readlines()[6].split()[2]

                            ligfitlog = glob(ligfitRUNPath + "/LigandFit*.log")[0]
                            if path.exists(ligfitlog):
                                with open(ligfitlog, "r") as inp:
                                    for line in inp.readlines():
                                        if line.startswith(" lig_xyz"):
                                            ligblob = line.split("lig_xyz ")[-1].replace("\n", "")
                except Exception:
                    pass

        ligfit_dataset = "_".join(usracr.split("_")[:-2])

        return [usracr, pdbout, dif_map, nat_map, spg, resolution, isa, r_work, r_free, bonds, angles,
                a, b, c, alpha, beta, gamma, blist, ligfit_dataset, pipeline, rhofitscore, ligfitscore, ligblob]

    xdsappLogs = list()
    autoprocLogs = list()
    dialsLogs = list()
    xdsxscaleLogs = list()
    fastdpLogs = list()
    EDNALogs = list()
    isaDict = dict()
    resultsList = list()

    fmax_proc_dir = project_process_protein_dir(proj)
    res_dir = path.join(project_results_dir(proj), proj.protein)

    xdsappLogs += glob(f"{fmax_proc_dir}/*/*/xdsapp/results*txt")
    autoprocLogs += glob(f"{fmax_proc_dir}/*/*/autoproc/process.log")
    dialsLogs += glob(f"{fmax_proc_dir}/*/*/dials/LogFiles/*log")
    xdsxscaleLogs += glob(f"{fmax_proc_dir}/*/*/xdsxscale/LogFiles/*XSCALE.log")
    # old way, still looking for datasets in the regular process folder, not fragmax
    # fastdpLogs += glob(f"{proc_dir}/*/*/fastdp/results/*.LP")
    # EDNALogs += glob(f"{proc_dir}/*/*/EDNA_proc/results/*.LP")

    # new way, looking for datasets inside the fragmax/process folder
    # It wont work with old project unless fastdp and EDNA is synchronised with fragmax folder
    fastdpLogs = glob(f"{fmax_proc_dir}/*/*/fastdp/*.LP")
    EDNALogs = glob(f"{fmax_proc_dir}/*/*/edna/*.LP")

    allLogs = xdsappLogs + autoprocLogs + dialsLogs + xdsxscaleLogs + EDNALogs + fastdpLogs
    # h5List += glob(f"{shift_dir}/raw/{proj.protein}/*/*master.h5")
    resultsList += \
        glob(f"{res_dir}**/*/dimple/final.pdb") + \
        glob(f"{res_dir}**/*/fspipeline/final.pdb") + \
        glob(f"{res_dir}**/*/buster/refine.pdb")

    datasetList = sorted(set([x.split("/")[-3] for x in allLogs] + [x.split("/")[-4] for x in resultsList]),
                         key=lambda x: ("Apo" in x, x))
    for dataset in datasetList:
        isaDict[dataset] = {"xdsapp": "", "autoproc": "", "xdsxscale": "", "dials": "", "fastdp": "", "edna": ""}

    resultsList = sorted(resultsList, key=lambda x: ("Apo" in x, x))

    for log in xdsappLogs:
        dataset = log.split("/")[10]
        with open(log, "r") as readFile:
            logfile = readFile.readlines()
        for line in logfile:
            if "    ISa" in line:
                isa = line.split()[-1]
                isaDict[dataset].update({"xdsapp": isa})

    for log in autoprocLogs:
        dataset = log.split("/")[10]
        with open_txt(log) as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict[dataset].update({"autoproc": isa})

    for log in dialsLogs:
        dataset = log.split("/")[10]
        with open_txt(log) as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict[dataset].update({"dials": isa})

    for log in xdsxscaleLogs:
        dataset = log.split("/")[10]
        with open_txt(log) as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                if logfile[n + 3].split() != []:
                    isa = logfile[n + 3].split()[-2]
        isaDict[dataset].update({"xdsxscale": isa})

    for log in fastdpLogs:
        dataset = log.split("/")[10]
        with open_txt(log) as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict[dataset].update({"fastdp": isa})

    for log in EDNALogs:
        dataset = log.split("/")[10]
        with open_txt(log) as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                if logfile[n + 3].split() != []:
                    isa = logfile[n + 3].split()[-2]
                    if isa == "b":
                        isa = ""
        isaDict[dataset].update({"edna": isa})

    with open(project_results_file(proj), "w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(
            ["usracr", "pdbout", "dif_map", "nat_map", "spg", "resolution", "ISa", "r_work", "r_free", "bonds",
             "angles", "a", "b", "c", "alpha", "beta", "gamma", "blist", "dataset", "pipeline", "rhofitscore",
             "ligfitscore", "ligblob"])
        for entry in resultsList:
            row = ThreadWithReturnValue(target=info_func, args=(entry, isaDict,))
            row.start()

            if row.join() is not None:
                if "" not in row.join():
                    writer.writerow(row.join())

    result_plots.generate(project_results_file(proj), project_process_protein_dir(proj))
