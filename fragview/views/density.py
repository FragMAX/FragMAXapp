import pyfastcopy  # noqa
import shutil
import csv
from os import path
from glob import glob
from ast import literal_eval

from django.shortcuts import render

from fragview.projects import current_project, project_results_file, project_static_url, project_results_dir
from fragview.projects import project_process_protein_dir
from fragview.versions import base_static


def show(request):
    proj = current_project(request)

    value = str(request.GET.get("structure"))
    with open(project_results_file(proj), "r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]
    result_info = list(filter(lambda x: x[0] == value, lines))[0]
    if len(result_info) == 23:
        usracr, pdbout, nat_map, dif_map, spg, resolution, isa, r_work, r_free, bonds, angles, a, b, c, \
            alpha, beta, gamma, blist, ligfit_dataset, pipeline, rhofitscore, ligfitscore, \
            ligblob = result_info
    else:
        usracr, pdbout, nat_map, dif_map, spg, resolution, isa, r_work, r_free, bonds, angles, a, b, c, \
            alpha, beta, gamma, blist, ligfit_dataset, pipeline, rhofitscore, ligfitscore, \
            ligblob, modelscore = result_info

    res_dir = path.join(project_results_dir(proj), "_".join(usracr.split("_")[:-2]), *pipeline.split("_"))
    mtzfd = path.join(res_dir, "final.mtz")

    refineLog, pipelineLog = find_refinement_log(res_dir)
    rhofitlog, ligandfitlog = find_ligandfitting_log(res_dir)

    if path.exists(path.join(res_dir, "final.pdb")):
        if not path.exists(mtzfd):
            final_glob = f"{res_dir}/final*.mtz"
            if glob(final_glob):
                mtzf = glob(final_glob)[0]
                shutil.copyfile(mtzf, mtzfd)

    processM = pipeline.split("_")[0]
    refineM = pipeline.split("_")[1]

    ligand = None

    if "apo" not in usracr.lower():
        ligbox = "block"
        ligfitbox = "block"
        rhofitbox = "block"
        rpos = 0
        lpos = 0
        ligand = usracr.split("-")[-1].split("_")[0]

        fitres_dir = path.join(proj.data_path(), "fragmax", "results", ligfit_dataset, processM, refineM)
        rhofit = path.join(fitres_dir, "rhofit", "best.pdb")

        if path.exists(rhofit):
            lpos = 1
            with open(rhofit, "r") as rhofitfile:
                for line in rhofitfile.readlines():
                    if line.startswith("HETATM"):
                        coords = line[32:54].split()
                        coords = list(map(float, coords))
                        coords = list(map(str, coords))
                        rhocenter = "[" + ",".join(coords) + "]"
                        break
        else:
            rhofit = ""
            rhocenter = "[0,0,0]"
            rhofitbox = "none"
        try:
            ligfit = sorted(glob(f"{fitres_dir}/ligfit/LigandFit_run_*/ligand*.pdb"))[-1]
            with open(ligfit, "r") as ligfitfile:
                for line in ligfitfile.readlines():
                    if line.startswith("HETATM"):
                        coords = line[32:54].split()
                        coords = list(map(float, coords))
                        coords = list(map(str, coords))
                        ligcenter = "[" + ",".join(coords) + "]"
                        break
        except Exception:
            ligfit = ""
            ligcenter = "[0,0,0]"
            ligfitbox = "none"
    else:
        ligfit = ""
        rhofit = ""
        rhofitscore = "-"
        ligfitscore = "-"
        ligcenter = "[]"
        rhocenter = "[]"
        ligbox = "none"
        rhofitbox = "none"
        ligfitbox = "none"
        rpos = 0
        lpos = 0

    try:
        currentpos = [n for n, line in enumerate(lines) if usracr in line[0]][0]
        if currentpos == len(lines) - 1:
            prevstr = lines[currentpos - 1][0]
            nextstr = lines[0][0]
        elif currentpos == 0:
            prevstr = lines[-1][0]
            nextstr = lines[currentpos + 1][0]

        else:
            prevstr = lines[currentpos - 1][0]
            nextstr = lines[currentpos + 1][0]

    except Exception:
        prevstr = usracr
        nextstr = usracr

    pdbout = pdbout.replace("/data/visitors/", "/static/")
    ligfit = ligfit.replace("/data/visitors/", "/static/")
    rhofit = rhofit.replace("/data/visitors/", "/static/")

    fitres_dir = path.join(proj.data_path(), "fragmax", "results", ligfit_dataset, processM, refineM)
    pdb_path = path.join(fitres_dir, "final.pdb").replace("/data/visitors/", "/static/")
    mtz_path = path.join(fitres_dir, "final.mtz").replace("/data/visitors/", "/static/")

    # get xyz for ligands
    blist = blist.replace(" ", "")
    center = blist[1:blist.index("]") + 1]

    if rhofitbox == "none" or ligfitbox == "none":
        dualviewbox = "none"
    else:
        dualviewbox = "block"

    if refineM == "dimple":
        refineName = "Refmac"
        pipelineName = "DIMPLE"
    elif refineM == "fspipeline":
        refineName = "Phenix.refine"
        pipelineName = "fspipeline"
    else:
        refineName = "autoBUSTER"
        pipelineName = ""

    return render(
        request,
        "fragview/density.html",
        {
            "name": usracr,
            "pdb": pdbout,
            "pdb_path": pdb_path,
            "mtz_path": mtz_path,
            "xyzlist": blist,
            "center": center,
            "ligand": ligand,
            "rscore": rhofitscore,
            "lscore": ligfitscore,
            "rwork": r_work,
            "rfree": r_free,
            "resolution": resolution,
            "spg": spg,
            "ligfit_dataset": ligfit_dataset,
            "process": processM,
            "refine": refineM,
            "blob": ligblob,
            "rhofitcenter": rhocenter,
            "ligfitcenter": ligcenter,
            "ligbox": ligbox,
            "prevstr": prevstr,
            "nextstr": nextstr,
            "ligfitbox": ligfitbox,
            "rhofitbox": rhofitbox,
            "dualviewbox": dualviewbox,
            "lpos": lpos,
            "rpos": rpos,
            "ligfitpdb": ligfit,
            "rhofitpdb": rhofit,
            "refineLog": refineLog,
            "pipelineLog": pipelineLog,
            "rhofitlog": rhofitlog,
            "ligandfitlog": ligandfitlog,
            "pipelineName": pipelineName,
            "refineName": refineName
        })


def compare_poses(request):
    proj = current_project(request)
    static_url = project_static_url(proj)

    ligfit_dataset = str(request.GET.get("ligfit_dataset"))
    data = ligfit_dataset.split(";")[0]
    blob = ligfit_dataset.split(";")[1]
    ligand = data.split("-")[-1].split("_")[0]

    entry_dir = path.join("_".join(data.split("_")[:2]), data.split("_")[2], data.split("_")[3])

    rhofit = proj.data_path() + "/fragmax/results/" + entry_dir + "/rhofit/best.pdb"
    ligfit = sorted(glob(
        proj.data_path() + "/fragmax/results/" + entry_dir + "/ligfit/LigandFit*/ligand_fit*pdb"))[-1]
    pdb = static_url + "/fragmax/results/" + entry_dir + "/final.pdb"
    mtz = static_url + "/fragmax/results/" + entry_dir + "/final.mtz"
    nat = static_url + "/fragmax/results/" + entry_dir + "/final_mFo-DFc.ccp4"
    dif = static_url + "/fragmax/results/" + entry_dir + "/final_2mFo-DFc.ccp4"

    ligcenter = "[]"
    rhocenter = "[]"
    if path.exists(ligfit):
        with open(ligfit, "r") as ligfitfile:
            for line in ligfitfile.readlines():
                if line.startswith("HETATM"):
                    ligcenter = "[" + ",".join(line[32:54].split()) + "]"
                    break

    if path.exists(rhofit):
        with open(rhofit, "r") as rhofitfile:
            for line in rhofitfile.readlines():
                if line.startswith("HETATM"):
                    rhocenter = "[" + ",".join(line[32:54].split()) + "]"
                    break

    rhofit = rhofit.replace("/data/visitors/", "/static/")
    ligfit = ligfit.replace("/data/visitors/", "/static/")

    l_dataset = "_".join(data.split("_")[:2])
    process = data.split("_")[2]
    refine = data.split("_")[3]
    return render(
        request,
        "fragview/dual_density.html",
        {
            "ligfit_dataset": data,
            "blob": blob,
            "rhofitcenter": rhocenter,
            "ligandfitcenter": ligcenter,
            "ligand": proj.library.name + "_" + ligand,
            "lig": ligand,
            "pdb": pdb,
            "mtz": mtz,
            "l_dataset": l_dataset,
            "process": process,
            "refine": refine,
            "dif": dif,
            "nat": nat,
            "rhofit": rhofit,
            "ligfit": ligfit
        })


def show_pipedream(request):
    proj = current_project(request)

    sample = str(request.GET.get('structure'))

    with open(path.join(project_process_protein_dir(proj), "pipedream.csv"), "r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]

    for n, line in enumerate(lines):
        if line[0] == sample:
            ligand = line[2]
            symmetry = sym2spg(line[4])
            resolution = line[5]
            rwork = line[6]
            rfree = line[7]
            rhofitscore = line[8]
            ligsvg = line[-1]
            currentpos = n
            if currentpos == len(lines) - 1:
                prevstr = lines[currentpos - 1][0]
                nextstr = lines[0][0]
            elif currentpos == 0:
                prevstr = lines[-1][0]
                nextstr = lines[currentpos + 1][0]

            else:
                prevstr = lines[currentpos - 1][0]
                nextstr = lines[currentpos + 1][0]

    if "Apo" not in sample:
        process = "rhofit"
        files = glob(f"{project_process_protein_dir(proj)}/*/{sample}/pipedream/rhofit*/")
        files.sort(key=lambda x: path.getmtime(x))
        if files != []:
            pdb = files[-1] + "refine.pdb"
            rhofit = files[-1] + "best.pdb"

        with open(rhofit, "r") as inp:
            for line in inp.readlines():
                if line.startswith("HETATM"):
                    center = "[" + ",".join(line[32:54].split()) + "]"
        cE = "true"

    else:
        process = "refine"
        files = glob(f"{project_process_protein_dir(proj)}/*/{sample}/pipedream/refine*/")
        files.sort(key=lambda x: path.getmtime(x))
        if files != []:
            pdb = files[-1] + "refine.pdb"
            rhofit = ""
            rhofitscore = "-"
            center = "[0,0,0]"
            cE = "false"

    return render(
        request,
        "fragview/pipedream_density.html",
        {
            "name": sample.replace("/data/visitors/", "/static/"),
            "pdb": pdb.replace("/data/visitors/", "/static/"),
            "mtz": pdb.replace("/data/visitors/", "/static/").replace(".pdb", ".mtz"),
            "sample": sample,
            "process": process,
            "rhofit": rhofit.replace("/data/visitors/", "/static/"),
            "center": center,
            "symmetry": symmetry,
            "resolution": resolution,
            "rwork": rwork,
            "rfree": rfree,
            "rhofitscore": rhofitscore,
            "ligand": ligand.replace("/data/visitors/", "/static/"),
            "prevstr": prevstr,
            "nextstr": nextstr,
            "cE": cE,
            "ligsvg": ligsvg,
        })


def sym2spg(sym):
    spgDict = {
        "1": "P 1", "2": " P -1", "3": " P 2    ", "4": "P 21", "5": "C 2",
        "6": "P m", "7": " P c    ", "8": " C m    ", "9": "C c", "10": "P 2/m",
        "11": "P 21/m", "12": " C 2/m", "13": " P 2/c", "14": "P 21/c", "15": "C 2/c",
        "16": "P 2 2 2", "17": " P 2 2 21    ", "18": " P 21 21 2 ", "19": "P 21 21 21", "20": "C 2 2 21",
        "21": "C 2 2 2", "22": " F 2 2 2", "23": " I 2 2 2", "24": "I 21 21 21", "25": "P m m 2",
        "26": "P m c 21 ", "27": " P c c 2", "28": " P m a 2", "29": "P c a 21", "30": "P n c 2",
        "31": "P m n 21 ", "32": " P b a 2", "33": " P n a 21    ", "34": "P n n 2", "35": "C m m 2",
        "36": "C m c 21 ", "37": " C c c 2", "38": " A m m 2", "39": "A b m 2", "40": "A m a 2",
        "41": "A b a 2", "42": " F m m 2", "43": " F d d 2", "44": "I m m 2", "45": "I b a 2",
        "46": "I m a 2", "47": " P m m m", "48": " P n n n", "49": "P c c m", "50": "P b a n",
        "51": "P m m a", "52": " P n n a", "53": " P m n a", "54": "P c c a", "55": "P b a m",
        "56": "P c c n", "57": " P b c m", "58": " P n n m", "59": "P m m n", "60": "P b c n",
        "61": "P b c a", "62": " P n m a", "63": " C m c m", "64": "C m c a", "65": "C m m m",
        "66": "C c c m", "67": " C m m a", "68": " C c c a", "69": "F m m m", "70": "F d d d",
        "71": "I m m m", "72": " I b a m", "73": " I b c a", "74": "I m m a", "75": "P 4",
        "76": "P 41", "77": " P 42", "78": " P 43", "79": "I 4", "80": "I 41",
        "81": "P -4", "82": " I -4", "83": " P 4/m", "84": "P 42/m", "85": "P 4/n",
        "86": "P 42/n", "87": " I 4/m", "88": " I 41/a", "89": "P 4 2 2", "90": "P 4 21 2",
        "91": "P 41 2 2 ", "92": " P 41 21 2 ", "93": " P 42 2 2 ", "94": "P 42 21 2", "95": "P 43 2 2",
        "96": "P 43 21 2 ", "97": " I 4 2 2", "98": " I 41 2 2 ", "99": "P 4 m m", "100": "P 4 b m",
        "101": "P 42 c m ", "102": " P 42 n m ", "103": " P 4 c c", "104": "P 4 n c", "105": "P 42 m c",
        "106": "P 42 b c ", "107": " I 4 m m", "108": " I 4 c m", "109": "I 41 m d", "110": "I 41 c d",
        "111": "P -4 2 m ", "112": " P -4 2 c ", "113": " P -4 21 m ", "114": "P -4 21 c", "115": "P -4 m 2",
        "116": "P -4 c 2 ", "117": " P -4 b 2 ", "118": " P -4 n 2 ", "119": "I -4 m 2", "120": "I -4 c 2",
        "121": "I -4 2 m ", "122": " I -4 2 d ", "123": " P 4/m m m ", "124": "P 4/m c c", "125": "P 4/n b m",
        "126": "P 4/n n c ", "127": " P 4/m b m ", "128": " P 4/m n c ", "129": "P 4/n m m", "130": "P 4/n c c",
        "131": "P 42/m m c ", "132": " P 42/m c m ", "133": " P 42/n b c ", "134": "P 42/n n m", "135": "P 42/m b c",
        "136": "P 42/m n m ", "137": " P 42/n m c ", "138": " P 42/n c m ", "139": "I 4/m m m", "140": "I 4/m c m",
        "141": "I 41/a m d ", "142": " I 41/a c d ", "143": " P 3    ", "144": "P 31", "145": "P 32",
        "146": "R 3    ", "147": " P -3", "148": " R -3", "149": "P 3 1 2", "150": "P 3 2 1",
        "151": "P 31 1 2 ", "152": " P 31 2 1 ", "153": " P 32 1 2 ", "154": "P 32 2 1", "155": "R 3 2",
        "156": "P 3 m 1", "157": " P 3 1 m", "158": " P 3 c 1", "159": "P 3 1 c", "160": "R 3 m",
        "161": "R 3 c", "162": " P -3 1 m ", "163": " P -3 1 c ", "164": "P -3 m 1", "165": "P -3 c 1",
        "166": "R -3 m", "167": " R -3 c", "168": " P 6    ", "169": "P 61", "170": "P 65",
        "171": "P 62", "172": " P 64", "173": " P 63", "174": "P -6", "175": "P 6/m",
        "176": "P 63/m", "177": " P 6 2 2", "178": " P 61 2 2 ", "179": "P 65 2 2", "180": "P 62 2 2",
        "181": "P 64 2 2 ", "182": " P 63 2 2 ", "183": " P 6 m m", "184": "P 6 c c", "185": "P 63 c m",
        "186": "P 63 m c ", "187": " P -6 m 2 ", "188": " P -6 c 2 ", "189": "P -6 2 m", "190": "P -6 2 c",
        "191": "P 6/m m m ", "192": " P 6/m c c ", "193": " P 63/m c m ", "194": "P 63/m m c", "195": "P 2 3",
        "196": "F 2 3", "197": " I 2 3", "198": " P 21 3", "199": "I 21 3", "200": "P m -3",
        "201": "P n -3", "202": " F m -3", "203": " F d -3", "204": "I m -3", "205": "P a -3",
        "206": "I a -3", "207": " P 4 3 2", "208": " P 42 3 2 ", "209": "F 4 3 2", "210": "F 41 3 2",
        "211": "I 4 3 2", "212": " P 43 3 2 ", "213": " P 41 3 2 ", "214": "I 41 3 2", "215": "P -4 3 m",
        "216": "F -4 3 m ", "217": " I -4 3 m ", "218": " P -4 3 n ", "219": "F -4 3 c", "220": "I -4 3 d",
        "221": "P m -3 m ", "222": " P n -3 n ", "223": " P m -3 n ", "224": "P n -3 m", "225": "F m -3 m",
        "226": "F m -3 c ", "227": " F d -3 m ", "228": " F d -3 c ", "229": "I m -3 m", "230": "I a -3 d"}

    return spgDict[sym]


def pandda_analyse(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get('structure'))
    if len(panddaInput.split(";")) == 5:
        method, dataset, event, site, nav = panddaInput.split(";")
    if len(panddaInput.split(";")) == 3:
        method, dataset, nav = panddaInput.split(";")

    pandda_res_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method, "pandda")
    datasets_dir = path.join(pandda_res_dir, "processed_datasets")
    mdl = [x.split("/")[-2] for x in sorted(glob(f"{datasets_dir}/*/*pandda-input.pdb"))]
    if len(mdl) != 0:
        indices = [i for i, s in enumerate(mdl) if dataset in s][0]

        if "prev" in nav:

            try:
                dataset = mdl[indices - 1]
            except IndexError:
                dataset = mdl[-1]

        if "next" in nav:
            try:
                dataset = mdl[indices + 1]
            except IndexError:
                dataset = mdl[0]

        ligand = dataset.split("-")[-1].split("_")[0]

        processedDir = path.join(datasets_dir, dataset)

        pdb = sorted(glob(f"{processedDir}/*pandda-input*"))[-1]
        with open(path.join(pandda_res_dir, "analyses", "pandda_analyse_events.csv"), "r") as inp:
            inspect_events = inp.readlines()

        for i in inspect_events:
            if dataset in i:
                k = i.split(",")
                break
            else:
                k = False
        if k:
            bdc = k[2]
            site_idx = k[11]
            center = "[" + k[12] + "," + k[13] + "," + k[14] + "]"
            resolution = k[18]
            rfree = k[20]
            rwork = k[21]
            spg = k[35]

            if len(panddaInput.split(";")) == 3:
                event = k[1]

            pdb = pdb.replace(base_static, "")
            map1 = \
                proj.data_path() + "/fragmax/results/pandda/" + proj.protein + "/" + method + \
                "/pandda/processed_datasets/" + dataset + "/" + dataset + "-z_map.native.ccp4"
            map1 = map1.replace(base_static, "")

            map2 = glob(f"{datasets_dir}/{dataset}/*BDC*ccp4")[0]
            map2 = map2.replace(base_static, "")
            average_map = map2.split("event")[0] + "ground-state-average-map.native.ccp4"
            name = map2.split("/")[-2]
        else:
            with open(path.join(pandda_res_dir, "analyses", "all_datasets_info.csv"), "r") as inp:
                inspect_events = inp.readlines()

            for i in inspect_events:
                if dataset in i:
                    k = i.split(",")
                    break
            bdc = k[0]
            site_idx = 0
            center = "['','','']"
            resolution = k[2]
            rfree = 0
            rwork = 0
            spg = k[19]

            if len(panddaInput.split(";")) == 3:
                event = k[1]

            pdb = pdb.replace(base_static, "")
            map1 = ""
            map2 = ""
            average_map = ""
            name = "Apo"

        summarypath = proj.data_path() + "/fragmax/results/pandda/" + proj.protein + \
            "/" + method + "/pandda/processed_datasets/" + dataset + "/html/" + dataset + ".html"
        summarypath = summarypath.replace(base_static, "")
        mtzFile = pdb.replace(".pdb", ".mtz")

        _sites = path.join(pandda_res_dir, "analyses", "pandda_analyse_sites.csv")
        centroids = find_site_centroids(_sites)

        with open(path.join(project_process_protein_dir(proj), "panddainspects.csv"), "r") as csvFile:
            reader = csv.reader(csvFile)
            lines = list(reader)

        lines = lines[1:]
        prevstr = ""
        nextstr = ""
        for n, i in enumerate(lines):
            if panddaInput.split(";") == i[:-1]:
                if n == len(lines) - 1:
                    prevstr = (";".join(lines[n - 1][:-1]))
                    nextstr = (";".join(lines[0][:-1]))
                elif n == 0:
                    prevstr = (";".join(lines[-1][:-1]))
                    nextstr = (";".join(lines[n + 1][:-1]))
                else:
                    prevstr = (";".join(lines[n - 1][:-1]))
                    nextstr = (";".join(lines[n + 1][:-1]))
        return render(
            request,
            "fragview/pandda_densityA.html",
            {
                "siten": site_idx,
                "event": event,
                "method": method,
                "rwork": rwork,
                "rfree": rfree,
                "resolution": resolution,
                "spg": spg,
                "dataset": dataset,
                "pdb": pdb,
                "mtz": mtzFile,
                "2fofc": map2,
                "fofc": map1,
                "ligand": ligand,
                "center": center,
                "centroids": centroids,
                "bdc": bdc,
                "summary": summarypath,
                "average_map": average_map,
                "name": name,
                "library": proj.library,
                "prevstr": prevstr,
                "nextstr": nextstr,
                "panddatype": "analyses"
            })

    else:
        return render(
            request,
            "fragview/error.html",
            {"issue": "No modelled structure for " + method + "_" + dataset + " was found."})


def pandda(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get('structure'))

    if len(panddaInput.split(";")) == 5:
        method, dataset, event, site, nav = panddaInput.split(";")
    if len(panddaInput.split(";")) == 3:
        method, dataset, nav = panddaInput.split(";")

    pandda_res_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method, "pandda")
    datasets_dir = path.join(pandda_res_dir, "processed_datasets")

    mdl = [x.split("/")[-3] for x in sorted(glob(f"{datasets_dir}/*/modelled_structures/*model.pdb"))]

    if len(mdl) != 0:
        indices = [i for i, s in enumerate(mdl) if dataset in s][0]

        if "prev" in nav:

            try:
                dataset = mdl[indices - 1]
            except IndexError:
                dataset = mdl[-1]

        if "next" in nav:
            try:
                dataset = mdl[indices + 1]
            except IndexError:
                dataset = mdl[0]

        ligand = dataset.split("-")[-1].split("_")[0]

        modelledDir = path.join(datasets_dir, dataset, "modelled_structures")

        pandda_res_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method, "pandda")
        _sites = path.join(pandda_res_dir, "analyses", "pandda_analyse_sites.csv")
        centroids = find_site_centroids(_sites)

        pdb = sorted(glob(f"{modelledDir}/*fitted*"))[-1]

        with open(path.join(pandda_res_dir, "analyses", "pandda_inspect_events.csv"), "r") as inp:
            inspect_events = inp.readlines()

        for i in inspect_events:
            if dataset in i:
                k = i.split(",")
                break
        headers = inspect_events[0].split(",")
        bdc = k[2]
        site_idx = k[11]
        center = "[" + k[12] + "," + k[13] + "," + k[14] + "]"
        resolution = k[18]
        rfree = k[20]
        rwork = k[21]
        spg = k[35]
        analysed = k[headers.index("analysed")]
        interesting = k[headers.index("Interesting")]
        ligplaced = k[headers.index("Ligand Placed")]
        ligconfid = k[headers.index("Ligand Confidence")]
        comment = k[headers.index("Comment")]

        if len(panddaInput.split(";")) == 3:
            event = k[1]

        if "true" in ligplaced.lower():
            ligplaced = "lig_radio"
        else:
            ligplaced = "nolig_radio"

        if "true" in interesting.lower():
            interesting = "interesting_radio"
        else:
            interesting = "notinteresting_radio"

        if "high" in ligconfid.lower():
            ligconfid = "high_conf_radio"
        elif "medium" in ligconfid.lower():
            ligconfid = "medium_conf_radio"
        else:
            ligconfid = "low_conf_radio"

        pdb = pdb.replace("/data/visitors/", "")

        map1 = \
            "biomax/" + proj.proposal + "/" + proj.shift + "/fragmax/results/pandda/" + proj.protein + "/" + method + \
            "/pandda/processed_datasets/" + dataset + "/" + dataset + "-z_map.native.ccp4"

        map2 = glob(f"{datasets_dir}/{dataset}/*BDC*ccp4")[0].replace("/data/visitors/", "")

        summarypath = "biomax/" + proj.proposal + "/" + proj.shift + "/fragmax/results/pandda/" + proj.protein + \
            "/" + method + "/pandda/processed_datasets/" + dataset + "/html/" + dataset + ".html"

        return render(
            request,
            "fragview/pandda_density.html",
            {
                "method": method,
                "data_path": proj.data_path().replace("/data/visitors", "/static"),
                "siten": site_idx,
                "event": event,
                "centroids": centroids,
                "method": method,
                "rwork": rwork,
                "rfree": rfree,
                "resolution": resolution,
                "spg": spg,
                "dataset": dataset,
                "pdb": pdb,
                "2fofc": map2,
                "fofc": map1,
                "ligand": ligand,
                "center": center,
                "analysed": analysed,
                "interesting": interesting,
                "ligplaced": ligplaced,
                "ligconfid": ligconfid,
                "comment": comment,
                "bdc": bdc,
                "summary": summarypath,
                "panddatype": "inspection"
            })
    else:
        return render(
            request,
            "fragview/error.html",
            {"issue": "No modelled structure for " + method + "_" + dataset + " was found."})


def pandda_consensus(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get("structure"))

    dataset, site_idx, event_idx, method, ddtag, run = panddaInput.split(";")

    map1 = \
        "biomax/" + proj.proposal + "/" + proj.shift + "/fragmax/results/pandda/" + proj.protein + "/" + method + \
        "/pandda/processed_datasets/" + dataset + ddtag + "_" + run + "/" + dataset + ddtag + \
        "_" + run + "-z_map.native.ccp4"

    glob_pattern = \
        f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/{method}/pandda/processed_datasets/" + \
        f"{dataset}{ddtag}_{run}/*BDC*ccp4"
    map2 = glob(glob_pattern)[0].replace("/data/visitors/", "")
    average_map = map2.split("event")[0] + "ground-state-average-map.native.ccp4"
    library = proj.library
    name = map2.split("/")[-2]

    summarypath = \
        "biomax/" + proj.proposal + "/" + proj.shift + "/fragmax/results/pandda/" + proj.protein + "/" + method + \
        "/pandda/processed_datasets/" + dataset + ddtag + "_" + run + "/html/" + dataset + ddtag + "_" + run + ".html"

    ligand = dataset.split("-")[-1].split("_")[0] + ddtag

    pandda_res_dir = path.join(project_results_dir(proj), "pandda", proj.protein, method, "pandda")
    _sites = path.join(pandda_res_dir, "analyses", "pandda_analyse_sites.csv")
    centroids = find_site_centroids(_sites)
    modelledDir = path.join(pandda_res_dir, "processed_datasets", f"{dataset}{ddtag}_{run}", "modelled_structures")

    pdb = sorted(glob(f"{modelledDir}/*fitted*"))[-1]
    pdb = pdb.replace("/data/visitors/", "")

    events_csv = path.join(pandda_res_dir, "analyses", "pandda_inspect_events.csv")
    with open(events_csv, "r") as inp:
        inspect_events = inp.readlines()

    for i in inspect_events:
        if dataset + ddtag + "_" + run in i:
            line = i.split(",")
            if dataset + ddtag + "_" + run == line[0] and event_idx == line[1] and site_idx == line[11]:
                k = line

    headers = inspect_events[0].split(",")
    bdc = k[2]
    site_idx = k[11]
    center = "[" + k[12] + "," + k[13] + "," + k[14] + "]"
    resolution = k[18]
    rfree = k[20]
    rwork = k[21]
    spg = k[35]
    analysed = k[headers.index("analysed")]
    interesting = k[headers.index("Interesting")]
    ligplaced = k[headers.index("Ligand Placed")]
    ligconfid = k[headers.index("Ligand Confidence")]
    comment = k[headers.index("Comment")]

    if "true" in ligplaced.lower():
        ligplaced = "lig_radio"
    else:
        ligplaced = "nolig_radio"

    if "true" in interesting.lower():
        interesting = "interesting_radio"
    else:
        interesting = "notinteresting_radio"

    if "high" in ligconfid.lower():
        ligconfid = "high_conf_radio"
    elif "medium" in ligconfid.lower():
        ligconfid = "medium_conf_radio"
    else:
        ligconfid = "low_conf_radio"

    with open(path.join(project_process_protein_dir(proj), "panddainspects.csv"), "r") as csvFile:
        reader = csv.reader(csvFile)
        lines = list(reader)

    lines = lines[1:]
    for n, i in enumerate(lines):
        if panddaInput.split(";") == i[:-1]:
            if n == len(lines) - 1:
                prevstr = (";".join(lines[n - 1][:-1]))
                nextstr = (";".join(lines[0][:-1]))
            elif n == 0:
                prevstr = (";".join(lines[-1][:-1]))
                nextstr = (";".join(lines[n + 1][:-1]))
            else:
                prevstr = (";".join(lines[n - 1][:-1]))
                nextstr = (";".join(lines[n + 1][:-1]))

    return render(
        request,
        "fragview/pandda_densityC.html",
        {
            "protein": proj.protein,
            "data_path": proj.data_path().replace("/data/visitors", "/static"),
            "siten": site_idx,
            "event": event_idx,
            "dataset": dataset + ddtag + "_" + run,
            "method": method,
            "rwork": rwork,
            "rfree": rfree,
            "resolution": resolution,
            "spg": spg,
            "pdb": pdb,
            "2fofc": map2,
            "fofc": map1,
            "average_map": average_map,
            "name": name,
            "library": library,
            "ligand": ligand,
            "center": center,
            "centroids": centroids,
            "analysed": analysed,
            "interesting": interesting,
            "ligplaced": ligplaced,
            "ligconfid": ligconfid,
            "comment": comment,
            "bdc": bdc,
            "summary": summarypath,
            "prevstr": prevstr,
            "nextstr": nextstr,
            "panddatype": "consensus"
        })


def find_refinement_log(res_dir):
    logFile = "refinelog"
    pipelineLog = "pipelinelong"

    if "dimple" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/*refmac*log"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = "/".join(logFile.split("/")[:-1]) + "/dimple.log"

    if "fspipeline" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/*/*-*log"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = path.join(path.dirname(path.dirname(logFile)), "fspipeline.log")

    if "buster" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/refine.log"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = logSearch[-1]

    return logFile, pipelineLog


def find_ligandfitting_log(res_dir):
    rhofitSearch = glob(f"{res_dir}/rhofit/results.txt")
    ligandfitSearch = glob(f"{res_dir}/ligfit/LigandFit_run*/ligand_*.log")
    if rhofitSearch:
        rhofitlog = rhofitSearch[0].replace("/data/visitors/", "")
    else:
        rhofitlog = ""
    if ligandfitSearch:
        ligandfitlog = ligandfitSearch[0].replace("/data/visitors/", "")
    else:
        ligandfitlog = ""
    return rhofitlog, ligandfitlog


def find_site_centroids(_sites):
    with open(_sites, "r") as r:
        sitelist = r.readlines()
    centroids = list()
    for _site in sitelist[1:]:
        centroid = literal_eval(",".join(_site.replace('"', "").split(",")[8:11]))
        centroids.append(list(centroid))
    return centroids
