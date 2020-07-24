from glob import glob
from os import path
import csv
import sys
import shutil
from collections import defaultdict
from xml.etree import cElementTree as ET

proposal, shift = sys.argv[2].split("/")
biomax_path = "/data/visitors/biomax"


def _generate_results_file(dataset, run, proposal, shift, protein):
    fmax_proc_dir = f"{biomax_path}/{proposal}/{shift}/fragmax/process/{protein}"
    res_dir = f"{biomax_path}/{proposal}/{shift}/fragmax/results"

    xdsappLogs = glob(f"{fmax_proc_dir}/{dataset}/*/xdsapp/results*txt")
    autoprocLogs = glob(f"{fmax_proc_dir}/{dataset}/*/autoproc/summary.html")
    dialsLogs = glob(f"{fmax_proc_dir}/{dataset}/*/dials/LogFiles/*log")
    xdsxscaleLogs = glob(f"{fmax_proc_dir}/{dataset}/*/xdsxscale/LogFiles/*XSCALE.log")
    fastdpLogs = glob(f"{fmax_proc_dir}/{dataset}/*/fastdp/*.LP")
    EDNALogs = sorted(glob(f"{fmax_proc_dir}/{dataset}/*/edna/*XSCALE.LP"), reverse=True)
    ppdprocLogs = glob(f"{res_dir}/{dataset}*/pipedream/process/process.log")
    ppdrefFiles = glob(f"{res_dir}/{dataset}*/pipedream/refine*/BUSTER_model.pdb")
    if ppdrefFiles:
        resultsList = (
            glob(f"{res_dir}/{dataset}_{run}/*/*/final.pdb")
            + [ppdrefFiles[-1]]
            + glob(f"{res_dir}**/*/buster/refine.pdb")
        )
    else:
        resultsList = glob(f"{res_dir}/{dataset}_{run}/*/*/final.pdb") + glob(f"{res_dir}**/*/buster/refine.pdb")
    isaDict = {"xdsapp": "", "autoproc": "", "xdsxscale": "", "dials": "", "fastdp": "", "edna": "", "pipedream": ""}

    project_results_file = f"{biomax_path}/{proposal}/{shift}/fragmax/process/{protein}/results.csv"

    resultsFile = list()
    with open(project_results_file, "r") as r:
        rspam = csv.reader(r)
        for row in rspam:
            resultsFile.append(row)
    header = [
        "usracr",
        "pdbout",
        "dif_map",
        "nat_map",
        "spg",
        "resolution",
        "ISa",
        "r_work",
        "r_free",
        "bonds",
        "angles",
        "a",
        "b",
        "c",
        "alpha",
        "beta",
        "gamma",
        "blist",
        "dataset",
        "pipeline",
        "rhofitscore",
        "ligfitscore",
        "ligblob",
        "modelscore",
    ]
    if resultsFile[0] != header:
        resultsFile.insert(0, header)

    for log in xdsappLogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for line in logfile:
            if "    ISa" in line:
                isa = line.split()[-1]
                isaDict["xdsapp"] = isa

    for log in autoprocLogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa (" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["autoproc"] = isa

    for log in ppdprocLogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["pipedream"] = isa

    for log in dialsLogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["dials"] = isa

    for log in xdsxscaleLogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                if logfile[n + 3].split():
                    isa = logfile[n + 3].split()[-2]
        isaDict["xdsxscale"] = isa

    for log in fastdpLogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                isa = logfile[n + 1].split()[-1]
        isaDict["fastdp"] = isa

    for log in EDNALogs:
        isa = "unknown"
        with open(log, "r", encoding="utf-8") as readFile:
            logfile = readFile.readlines()
        for n, line in enumerate(logfile):
            if "ISa" in line:
                if logfile[n + 1].split():
                    isa = logfile[n + 1].split()[-2]
                    if isa == "b":
                        isa = ""
        isaDict["edna"] = isa

    for entry in resultsList:
        if "pipedream" in entry:
            usracr = "_".join(entry.split("/")[8:10])
            if usracr in [x[0] for x in resultsFile if x is not None]:
                for n, line in enumerate(resultsFile):
                    if usracr in line[0]:
                        entry_results = _get_results_func(usracr, entry, isaDict, res_dir)
                        if entry_results is not None:
                            lst = entry_results
                            resultsFile[n] = lst
            else:
                entry_results = _get_results_func(usracr, entry, isaDict, res_dir)

                if entry_results is not None:
                    resultsFile.append(entry_results)
            with open(project_results_file, "w") as csvFile:
                writer = csv.writer(csvFile)
                for row in resultsFile:
                    if row is not None and len(row) > 22:
                        writer.writerow(row)
                        pass

        else:
            usracr = "_".join(entry.split("/")[8:11])
            if usracr in [x[0] for x in resultsFile if x is not None]:
                for n, line in enumerate(resultsFile):
                    if usracr in line[0]:
                        entry_results = _get_results_func(usracr, entry, isaDict, res_dir)
                        if entry_results is not None:
                            lst = entry_results
                            resultsFile[n] = lst
            else:
                entry_results = _get_results_func(usracr, entry, isaDict, res_dir)
                if entry_results is not None:
                    resultsFile.append(entry_results)
            with open(project_results_file, "w") as csvFile:
                writer = csv.writer(csvFile)
                for row in resultsFile:
                    if row is not None and len(row) > 22:
                        writer.writerow(row)


def _get_results_func(usracr, entry, isaDict, res_dir):
    (
        pdbout,
        dif_map,
        nat_map,
        spg,
        resolution,
        isa,
        r_work,
        r_free,
        bonds,
        angles,
        a,
        b,
        c,
        alpha,
        beta,
        gamma,
        blist,
        ligfit_dataset,
        pipeline,
        rhofitscore,
        ligfitscore,
        ligblob,
        modelscore,
    ) = [""] * 23
    pdbout = ""

    if "pipedream" in entry:
        pipeline = "pipedream"
    else:
        pipeline = "_".join(entry.split("/")[9:11])
    process_method = entry.split("/")[9]
    refine_method = pipeline.split("_")[-1]
    rhofitscore = ""
    ligfitscore = ""
    ligblob = [0, 0, 0]
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

        if path.exists("/".join(entry.split("/")[:-1]) + "/mtz2map.log") and path.exists(
            "/".join(entry.split("/")[:-1]) + "/blobs.log"
        ):
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
    if "pipedream" in usracr:
        with open(entry, "r", encoding="utf-8") as inp:
            pdb_file = inp.readlines()
        for line in pdb_file:
            if "REMARK   3   BOND LENGTHS                       (A) :" in line:
                bonds = line.split()[-1]
            if "REMARK   3   BOND ANGLES                  (DEGREES) :" in line:
                angles = line.split()[-1]

        summary = glob(f"{res_dir}/{dataset}*/pipedream/summary.xml")[0]
        with open(summary, "r") as fd:
            doc = etree_to_dict(ET.XML(fd.read()))

        a = doc["GPhL-pipedream"]["refdata"]["cell"]["a"]
        b = doc["GPhL-pipedream"]["refdata"]["cell"]["b"]
        c = doc["GPhL-pipedream"]["refdata"]["cell"]["c"]
        alpha = doc["GPhL-pipedream"]["refdata"]["cell"]["alpha"]
        beta = doc["GPhL-pipedream"]["refdata"]["cell"]["beta"]
        gamma = doc["GPhL-pipedream"]["refdata"]["cell"]["gamma"]
        if "Apo" not in usracr:
            rhofitscore = doc["GPhL-pipedream"]["ligandfitting"]["ligand"]["rhofitsolution"]["correlationcoefficient"]
        else:
            rhofitscore = ""
        symm = doc["GPhL-pipedream"]["refdata"]["symm"]
        spg = f'{symm} ({sym2spg(symm).replace(" ", "")})'
        r_work = doc["GPhL-pipedream"]["refinement"]["Cycle"][-1]["R"]
        r_free = doc["GPhL-pipedream"]["refinement"]["Cycle"][-1]["Rfree"]
        resolution = doc["GPhL-pipedream"]["inputdata"]["table1"]["shellstats"][0]["reshigh"]

    if not ligblob:
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

    if "pipedream" in usracr:
        ligfit_dataset = "_".join(usracr.split("_")[:-1])
    else:
        ligfit_dataset = "_".join(usracr.split("_")[:-2])

    return [
        usracr,
        pdbout,
        dif_map,
        nat_map,
        spg,
        resolution,
        isa,
        r_work,
        r_free,
        bonds,
        angles,
        a,
        b,
        c,
        alpha,
        beta,
        gamma,
        blist,
        ligfit_dataset,
        pipeline,
        rhofitscore,
        ligfitscore,
        ligblob,
        modelscore,
    ]


def sym2spg(sym):
    spgDict = {
        "1": "P 1",
        "2": " P -1",
        "3": " P 2 ",
        "4": "P 21",
        "5": "C 2",
        "6": "P m",
        "7": " P c    ",
        "8": " C m    ",
        "9": "C c",
        "10": "P 2/m",
        "11": "P 21/m",
        "12": " C 2/m",
        "13": " P 2/c",
        "14": "P 21/c",
        "15": "C 2/c",
        "16": "P 2 2 2",
        "17": " P 2 2 21    ",
        "18": " P 21 21 2 ",
        "19": "P 21 21 21",
        "20": "C 2 2 21",
        "21": "C 2 2 2",
        "22": " F 2 2 2",
        "23": " I 2 2 2",
        "24": "I 21 21 21",
        "25": "P m m 2",
        "26": "P m c 21 ",
        "27": " P c c 2",
        "28": " P m a 2",
        "29": "P c a 21",
        "30": "P n c 2",
        "31": "P m n 21 ",
        "32": " P b a 2",
        "33": " P n a 21    ",
        "34": "P n n 2",
        "35": "C m m 2",
        "36": "C m c 21 ",
        "37": " C c c 2",
        "38": " A m m 2",
        "39": "A b m 2",
        "40": "A m a 2",
        "41": "A b a 2",
        "42": " F m m 2",
        "43": " F d d 2",
        "44": "I m m 2",
        "45": "I b a 2",
        "46": "I m a 2",
        "47": " P m m m",
        "48": " P n n n",
        "49": "P c c m",
        "50": "P b a n",
        "51": "P m m a",
        "52": " P n n a",
        "53": " P m n a",
        "54": "P c c a",
        "55": "P b a m",
        "56": "P c c n",
        "57": " P b c m",
        "58": " P n n m",
        "59": "P m m n",
        "60": "P b c n",
        "61": "P b c a",
        "62": " P n m a",
        "63": " C m c m",
        "64": "C m c a",
        "65": "C m m m",
        "66": "C c c m",
        "67": " C m m a",
        "68": " C c c a",
        "69": "F m m m",
        "70": "F d d d",
        "71": "I m m m",
        "72": " I b a m",
        "73": " I b c a",
        "74": "I m m a",
        "75": "P 4",
        "76": "P 41",
        "77": " P 42",
        "78": " P 43",
        "79": "I 4",
        "80": "I 41",
        "81": "P -4",
        "82": " I -4",
        "83": " P 4/m",
        "84": "P 42/m",
        "85": "P 4/n",
        "86": "P 42/n",
        "87": " I 4/m",
        "88": " I 41/a",
        "89": "P 4 2 2",
        "90": "P 4 21 2",
        "91": "P 41 2 2 ",
        "92": " P 41 21 2 ",
        "93": " P 42 2 2 ",
        "94": "P 42 21 2",
        "95": "P 43 2 2",
        "96": "P 43 21 2 ",
        "97": " I 4 2 2",
        "98": " I 41 2 2 ",
        "99": "P 4 m m",
        "100": "P 4 b m",
        "101": "P 42 c m ",
        "102": " P 42 n m ",
        "103": " P 4 c c",
        "104": "P 4 n c",
        "105": "P 42 m c",
        "106": "P 42 b c ",
        "107": " I 4 m m",
        "108": " I 4 c m",
        "109": "I 41 m d",
        "110": "I 41 c d",
        "111": "P -4 2 m ",
        "112": " P -4 2 c ",
        "113": " P -4 21 m ",
        "114": "P -4 21 c",
        "115": "P -4 m 2",
        "116": "P -4 c 2 ",
        "117": " P -4 b 2 ",
        "118": " P -4 n 2 ",
        "119": "I -4 m 2",
        "120": "I -4 c 2",
        "121": "I -4 2 m ",
        "122": " I -4 2 d ",
        "123": " P 4/m m m ",
        "124": "P 4/m c c",
        "125": "P 4/n b m",
        "126": "P 4/n n c ",
        "127": " P 4/m b m ",
        "128": " P 4/m n c ",
        "129": "P 4/n m m",
        "130": "P 4/n c c",
        "131": "P 42/m m c ",
        "132": " P 42/m c m ",
        "133": " P 42/n b c ",
        "134": "P 42/n n m",
        "135": "P 42/m b c",
        "136": "P 42/m n m ",
        "137": " P 42/n m c ",
        "138": " P 42/n c m ",
        "139": "I 4/m m m",
        "140": "I 4/m c m",
        "141": "I 41/a m d ",
        "142": " I 41/a c d ",
        "143": " P 3    ",
        "144": "P 31",
        "145": "P 32",
        "146": "R 3    ",
        "147": " P -3",
        "148": " R -3",
        "149": "P 3 1 2",
        "150": "P 3 2 1",
        "151": "P 31 1 2 ",
        "152": " P 31 2 1 ",
        "153": " P 32 1 2 ",
        "154": "P 32 2 1",
        "155": "R 3 2",
        "156": "P 3 m 1",
        "157": " P 3 1 m",
        "158": " P 3 c 1",
        "159": "P 3 1 c",
        "160": "R 3 m",
        "161": "R 3 c",
        "162": " P -3 1 m ",
        "163": " P -3 1 c ",
        "164": "P -3 m 1",
        "165": "P -3 c 1",
        "166": "R -3 m",
        "167": " R -3 c",
        "168": " P 6    ",
        "169": "P 61",
        "170": "P 65",
        "171": "P 62",
        "172": " P 64",
        "173": " P 63",
        "174": "P -6",
        "175": "P 6/m",
        "176": "P 63/m",
        "177": " P 6 2 2",
        "178": " P 61 2 2 ",
        "179": "P 65 2 2",
        "180": "P 62 2 2",
        "181": "P 64 2 2 ",
        "182": " P 63 2 2 ",
        "183": " P 6 m m",
        "184": "P 6 c c",
        "185": "P 63 c m",
        "186": "P 63 m c ",
        "187": " P -6 m 2 ",
        "188": " P -6 c 2 ",
        "189": "P -6 2 m",
        "190": "P -6 2 c",
        "191": "P 6/m m m ",
        "192": " P 6/m c c ",
        "193": " P 63/m c m ",
        "194": "P 63/m m c",
        "195": "P 2 3",
        "196": "F 2 3",
        "197": " I 2 3",
        "198": " P 21 3",
        "199": "I 21 3",
        "200": "P m -3",
        "201": "P n -3",
        "202": " F m -3",
        "203": " F d -3",
        "204": "I m -3",
        "205": "P a -3",
        "206": "I a -3",
        "207": " P 4 3 2",
        "208": " P 42 3 2 ",
        "209": "F 4 3 2",
        "210": "F 41 3 2",
        "211": "I 4 3 2",
        "212": " P 43 3 2 ",
        "213": " P 41 3 2 ",
        "214": "I 41 3 2",
        "215": "P -4 3 m",
        "216": "F -4 3 m ",
        "217": " I -4 3 m ",
        "218": " P -4 3 n ",
        "219": "F -4 3 c",
        "220": "I -4 3 d",
        "221": "P m -3 m ",
        "222": " P n -3 n ",
        "223": " P m -3 n ",
        "224": "P n -3 m",
        "225": "F m -3 m",
        "226": "F m -3 c ",
        "227": " F d -3 m ",
        "228": " F d -3 c ",
        "229": "I m -3 m",
        "230": "I a -3 d",
    }

    return spgDict[sym]


def etree_to_dict(t):
    gpl_str = "{http://www.globalphasing.com/buster/manual/pipedream/manual/index.html?xmlversion=0.0.1}"
    d = {t.tag.replace(gpl_str, ""): {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag.replace(gpl_str, ""): {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag.replace(gpl_str, "")].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag.replace(gpl_str, "")]["#text"] = text
        else:
            d[t.tag.replace(gpl_str, "")] = text
    return d


if sys.argv[1] == "alldatasets":
    res_dir = f"{biomax_path}/{proposal}/{shift}/fragmax/results"
    datasets = [path.basename(x) for x in glob(f"{res_dir}/*_*")]
    for d_r in datasets:
        dataset, run = d_r.split("_")
        protein = dataset.split("-")[0]
        _generate_results_file(dataset, run, proposal, shift, protein)
else:
    dataset, run = sys.argv[1].split("_")
    protein = dataset.split("-")[0]
    _generate_results_file(dataset, run, proposal, shift, protein)
