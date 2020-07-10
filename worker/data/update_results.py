from glob import glob
from os import path
import csv
import sys
import shutil

dataset, run = sys.argv[1].split("_")
proposal, shift = sys.argv[2].split("/")
protein = dataset.split("-")[0]

biomax_path = "/data/visitors/biomax"


def _generate_results_file(dataset, run, proposal, shift, protein):
    fmax_proc_dir = f"{biomax_path}/{proposal}/{shift}/fragmax/process/{protein}"
    res_dir = f"{biomax_path}/{proposal}/{shift}/fragmax/results"

    xdsappLogs = glob(f"{fmax_proc_dir}/{dataset}/*/xdsapp/results*txt")
    autoprocLogs = glob(f"{fmax_proc_dir}/{dataset}/*/autoproc/process.log")
    dialsLogs = glob(f"{fmax_proc_dir}/{dataset}/*/dials/LogFiles/*log")
    xdsxscaleLogs = glob(f"{fmax_proc_dir}/{dataset}/*/xdsxscale/LogFiles/*XSCALE.log")
    fastdpLogs = glob(f"{fmax_proc_dir}/{dataset}/*/fastdp/*.LP")
    EDNALogs = glob(f"{fmax_proc_dir}/{dataset}/*/edna/*.LP")

    resultsList = glob(f"{res_dir}/{dataset}_{run}/*/*/final.pdb")
    isaDict = {"xdsapp": "", "autoproc": "", "xdsxscale": "", "dials": "", "fastdp": "", "edna": ""}

    project_results_file = f"{biomax_path}/{proposal}/{shift}/fragmax/process/{protein}/results.csv"
    resultsFile = list()
    with open(project_results_file, "r") as r:
        rspam = csv.reader(r)
        for row in rspam:
            resultsFile.append(row)

    for log in xdsappLogs:
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for line in logfile:
            if "    ISa" in line:
                isa = line.split()[-1]
                isaDict["xdsapp"] = isa

    for log in autoprocLogs:
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["autoproc"] = isa

    for log in dialsLogs:
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["dials"] = isa

    for log in xdsxscaleLogs:
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                if logfile[n + 3].split():
                    isa = logfile[n + 3].split()[-2]
        isaDict["xdsxscale"] = isa

    for log in fastdpLogs:
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["fastdp"] = isa

    for log in EDNALogs:
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                if logfile[n + 3].split():
                    isa = logfile[n + 3].split()[-2]
                    if isa == "b":
                        isa = ""
        isaDict["edna"] = isa

    for entry in resultsList:
        usracr = "_".join(entry.split("/")[8:11])
        if usracr in [x[0] for x in resultsFile if x is not None]:
            for n, line in enumerate(resultsFile):
                if usracr in line[0]:
                    entry_results = _get_results_func(entry, isaDict, res_dir)
                    if entry_results is not None:
                        lst = entry_results
                        resultsFile[n] = lst
        else:
            entry_results = _get_results_func(entry, isaDict, res_dir)
            if entry_results is not None:
                resultsFile.append(entry_results)
        with open(project_results_file, "w") as csvFile:
            writer = csv.writer(csvFile)
            for row in resultsFile:
                if row is not None and len(row) > 22:
                    writer.writerow(row)


def _get_results_func(entry, isaDict, res_dir):
    usracr, pdbout, dif_map, nat_map, spg, resolution, isa, r_work, r_free, bonds, angles, a, b, c, alpha, beta, \
        gamma, blist, ligfit_dataset, pipeline, rhofitscore, ligfitscore, ligblob, modelscore = [""] * 24
    pdbout = ""
    usracr = "_".join(entry.split("/")[8:11])
    pipeline = "_".join(entry.split("/")[9:11])
    process_method = entry.split("/")[9]
    refine_method = pipeline.split("_")[-1]

    if process_method == "EDNA_proc" or process_method == "EDNA":
        process_method = "edna"  # Updates the name of EDNA taken from file path for isaDict reference
    isa = isaDict[process_method]

    with open(entry, "r", encoding="utf-8") as readFile:
        pdb_file = readFile.readlines()

    if "dimple" in usracr:
        for line in pdb_file:
            if "REMARK   3   FREE R VALUE                     :" in line:
                r_free = line.split()[-1]
                r_free = str("{0:.2f}".format(float(r_free)))

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

        entry_log = entry.replace("final.pdb", "dimple.log")
        blist = []
        with open(entry_log, "r") as readLog:
            log = readLog.readlines()
        for n, line in enumerate(log):
            if line.startswith("blobs: "):
                blist = line.split(":")[-1].rstrip()

        pdbout = "/".join(entry_log.split("/")[3:-1]) + "/final.pdb"
        dif_map = "/".join(entry_log.split("/")[3:-1]) + "/final_2mFo-DFc.ccp4"
        nat_map = "/".join(entry_log.split("/")[3:-1]) + "/final_mFo-DFc.ccp4"

    if "buster" in usracr:
        with open(entry, "r", encoding="utf-8") as inp:
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
            with open(entry, "r", encoding="utf-8") as inp:
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

            with open("/".join(entry.split("/")[:-1]) + "/blobs.log", "r", encoding="utf-8") as inp:
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
            with open("/".join(entry.split("/")[:-1]) + "/mtz2map.log", "r", encoding="utf-8") as inp:
                readFile = inp.readlines()
                for mline in readFile:
                    if "_2mFo-DFc.ccp4" in mline:
                        pdbout = "/".join(entry.split("/")[3:-1]) + "/final.pdb"
                        dif_map = "/".join(entry.split("/")[3:-1]) + "/final_2mFo-DFc.ccp4"
                        nat_map = "/".join(entry.split("/")[3:-1]) + "/final_mFo-DFc.ccp4"

    rhofitscore = "-"
    ligfitscore = "-"
    ligblob = [0, 0, 0]

    if path.exists("/data/visitors/" + pdbout) and "Apo" not in pdbout:

        ligfitPath = path.join(res_dir, f"{dataset}_{run}", process_method, refine_method, "ligfit")
        rhofitPath = path.join(res_dir, f"{dataset}_{run}", process_method, refine_method, "rhofit")
        if path.exists(rhofitPath):
            hit_corr_log = path.join(rhofitPath, "Hit_corr.log")
            if path.exists(hit_corr_log):
                with open(hit_corr_log, "r", encoding="utf-8") as inp:
                    rhofitscore = inp.readlines()[0].split()[1]
        if path.exists(ligfitPath):
            try:
                ligfitRUNPath = sorted(glob(f"{ligfitPath}/LigandFit*"))[-1]
                if ligfitRUNPath:
                    if glob(ligfitRUNPath + "/LigandFit*.log"):
                        if path.exists(ligfitRUNPath + "/LigandFit_summary.dat"):
                            with open(ligfitRUNPath + "/LigandFit_summary.dat", "r", encoding="utf-8") as inp:
                                ligfitscore = inp.readlines()[6].split()[2]
                        ligfitlog = glob(ligfitRUNPath + "/LigandFit*.log")[0]
                        if path.exists(ligfitlog):
                            with open(ligfitlog, "r", encoding="utf-8") as inp:
                                for line in inp.readlines():
                                    if line.startswith(" lig_xyz"):
                                        ligblob = line.split("lig_xyz ")[-1].replace("\n", "")
            except Exception:
                pass

    ligfit_dataset = "_".join(usracr.split("_")[:-2])

    return [usracr, pdbout, dif_map, nat_map, spg, resolution, isa, r_work, r_free, bonds, angles,
            a, b, c, alpha, beta, gamma, blist, ligfit_dataset, pipeline, rhofitscore, ligfitscore, ligblob, modelscore]


_generate_results_file(dataset, run, proposal, shift, protein)
