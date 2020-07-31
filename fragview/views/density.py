import pyfastcopy  # noqa
import shutil
from os import path
from glob import glob
from ast import literal_eval

from django.shortcuts import render

from fragview.projects import current_project, project_results_file, project_static_url, project_results_dir
from fragview.projects import project_process_protein_dir
from fragview.versions import base_static
from fragview.fileio import read_csv_lines


def show(request):
    proj = current_project(request)

    value = str(request.GET.get("structure"))

    lines = read_csv_lines(project_results_file(proj))[1:]

    result_info = list(filter(lambda x: x[0] == value, lines))[0]
    if len(result_info) == 23:
        (
            usracr,
            pdbout,
            nat_map,
            dif_map,
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
        ) = result_info
    else:
        (
            usracr,
            pdbout,
            nat_map,
            dif_map,
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
        ) = result_info

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

    center = blist[1 : blist.index("]") + 1]  # noqa E203

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
        refineName = "BUSTER"
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
            "refineName": refineName,
        },
    )


def compare_poses(request):
    proj = current_project(request)
    static_url = project_static_url(proj)

    ligfit_dataset = str(request.GET.get("ligfit_dataset"))
    data = ligfit_dataset.split(";")[0]
    blob = ligfit_dataset.split(";")[1]
    ligand = data.split("-")[-1].split("_")[0]

    entry_dir = path.join("_".join(data.split("_")[:2]), data.split("_")[2], data.split("_")[3])

    rhofit = proj.data_path() + "/fragmax/results/" + entry_dir + "/rhofit/best.pdb"
    ligfit = sorted(glob(proj.data_path() + "/fragmax/results/" + entry_dir + "/ligfit/LigandFit*/ligand_fit*pdb"))[-1]
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
            "ligfit": ligfit,
        },
    )


def show_pipedream(request):
    proj = current_project(request)

    sample = str(request.GET.get("structure"))

    lines = read_csv_lines(path.join(project_process_protein_dir(proj), "results.csv"))[1:]

    for n, line in enumerate(lines):
        if line[0] == f"{sample}":
            symmetry = line[4]
            resolution = line[5]
            rwork = line[7]
            rfree = line[8]
            rhofitscore = line[20]
            ligsvg = ""
            currentpos = n
            center = line[22]
            prefix = line[18]
            ligand = prefix.split("-")[-1].split("_")[0]
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
        files = glob(f"{project_results_dir(proj)}/{prefix}/pipedream/rhofit*/")
        files.sort(key=lambda x: path.getmtime(x))
        if files:
            pdb = files[-1] + "refine.pdb"
            rhofit = files[-1] + "best.pdb"

        cE = "true"

    else:
        process = "refine"
        files = glob(f"{project_results_dir(proj)}/{prefix}/pipedream/refine*/")
        files.sort(key=lambda x: path.getmtime(x))
        if files:
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
            "prefix": prefix,
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
        },
    )


def pandda_analyse(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get("structure"))
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
            map1 = (
                proj.data_path()
                + "/fragmax/results/pandda/"
                + proj.protein
                + "/"
                + method
                + "/pandda/processed_datasets/"
                + dataset
                + "/"
                + dataset
                + "-z_map.native.ccp4"
            )
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

        summarypath = (
            proj.data_path()
            + "/fragmax/results/pandda/"
            + proj.protein
            + "/"
            + method
            + "/pandda/processed_datasets/"
            + dataset
            + "/html/"
            + dataset
            + ".html"
        )
        summarypath = summarypath.replace(base_static, "")
        mtzFile = pdb.replace(".pdb", ".mtz")

        _sites = path.join(pandda_res_dir, "analyses", "pandda_analyse_sites.csv")
        centroids = find_site_centroids(_sites)

        lines = read_csv_lines(path.join(pandda_res_dir, "analyses", "pandda_analyse_events.csv"))[1:]

        prevstr = ""
        nextstr = ""
        for n, i in enumerate(lines):
            if panddaInput.split(";") == i[:-1]:
                if n == len(lines) - 1:
                    prevstr = ";".join(lines[n - 1][:-1])
                    nextstr = ";".join(lines[0][:-1])
                elif n == 0:
                    prevstr = ";".join(lines[-1][:-1])
                    nextstr = ";".join(lines[n + 1][:-1])
                else:
                    prevstr = ";".join(lines[n - 1][:-1])
                    nextstr = ";".join(lines[n + 1][:-1])
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
                "panddatype": "analyses",
            },
        )

    else:
        return render(
            request,
            "fragview/error.html",
            {"issue": "No modelled structure for " + method + "_" + dataset + " was found."},
        )


def pandda(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get("structure"))

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

        map1 = (
            "biomax/"
            + proj.proposal
            + "/"
            + proj.shift
            + "/fragmax/results/pandda/"
            + proj.protein
            + "/"
            + method
            + "/pandda/processed_datasets/"
            + dataset
            + "/"
            + dataset
            + "-z_map.native.ccp4"
        )

        map2 = glob(f"{datasets_dir}/{dataset}/*BDC*ccp4")[0].replace("/data/visitors/", "")

        summarypath = (
            "biomax/"
            + proj.proposal
            + "/"
            + proj.shift
            + "/fragmax/results/pandda/"
            + proj.protein
            + "/"
            + method
            + "/pandda/processed_datasets/"
            + dataset
            + "/html/"
            + dataset
            + ".html"
        )

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
                "panddatype": "inspection",
            },
        )
    else:
        return render(
            request,
            "fragview/error.html",
            {"issue": "No modelled structure for " + method + "_" + dataset + " was found."},
        )


def pandda_consensus(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get("structure"))

    dataset, site_idx, event_idx, method, ddtag, run = panddaInput.split(";")

    map1 = (
        "biomax/"
        + proj.proposal
        + "/"
        + proj.shift
        + "/fragmax/results/pandda/"
        + proj.protein
        + "/"
        + method
        + "/pandda/processed_datasets/"
        + dataset
        + ddtag
        + "_"
        + run
        + "/"
        + dataset
        + ddtag
        + "_"
        + run
        + "-z_map.native.ccp4"
    )

    glob_pattern = (
        f"{proj.data_path()}/fragmax/results/pandda/{proj.protein}/{method}/pandda/processed_datasets/"
        + f"{dataset}{ddtag}_{run}/*BDC*ccp4"
    )
    map2 = glob(glob_pattern)[0].replace("/data/visitors/", "")
    average_map = map2.split("event")[0] + "ground-state-average-map.native.ccp4"
    library = proj.library
    name = map2.split("/")[-2]

    summarypath = (
        "biomax/"
        + proj.proposal
        + "/"
        + proj.shift
        + "/fragmax/results/pandda/"
        + proj.protein
        + "/"
        + method
        + "/pandda/processed_datasets/"
        + dataset
        + ddtag
        + "_"
        + run
        + "/html/"
        + dataset
        + ddtag
        + "_"
        + run
        + ".html"
    )

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

    lines = read_csv_lines(path.join(project_process_protein_dir(proj), "panddainspects.csv"))[1:]

    for n, i in enumerate(lines):
        if panddaInput.split(";") == i[:-1]:
            if n == len(lines) - 1:
                prevstr = ";".join(lines[n - 1][:-1])
                nextstr = ";".join(lines[0][:-1])
            elif n == 0:
                prevstr = ";".join(lines[-1][:-1])
                nextstr = ";".join(lines[n + 1][:-1])
            else:
                prevstr = ";".join(lines[n - 1][:-1])
                nextstr = ";".join(lines[n + 1][:-1])

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
            "panddatype": "consensus",
        },
    )


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
        logSearch = sorted(glob(f"{res_dir}/*BUSTER/Cycle*/*html"))
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
