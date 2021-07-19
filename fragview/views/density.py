from os import path
from glob import glob
from pathlib import Path
from ast import literal_eval
from django.shortcuts import render
from fragview.projects import (
    current_project,
    project_static_url,
    project_results_dir,
)
from fragview.projects import project_process_protein_dir
from fragview.models import Fragment
from fragview.pandda import (
    PanddaAnalyseEvents,
    PanddaAnalyseSites,
    PanddaAllDatasetInfo,
)
from fragview.fileio import read_csv_lines
from fragview.views.wrap import Wrapper
from fragview.views.utils import (
    get_refine_result_by_id,
    get_dataset_by_name,
    get_crystals_fragment,
)


def show(request, result_id):
    project = current_project(request)
    result = get_refine_result_by_id(project, result_id)

    return render(
        request,
        "fragview/density.html",
        {
            "result": result,
            "rhofit_result": result.get_ligfit_result("rhofit"),
            "ligandfit_result": result.get_ligfit_result("ligandfit"),
            "fragment": get_crystals_fragment(result.dataset.crystal),
            "rhofitcenter": None,  # rhocenter,
            "previous_result": result.previous(),
            "next_result": result.next(),
        },
    )


def compare_poses(request):
    proj = current_project(request)
    static_url = project_static_url(proj)

    ligfit_dataset = str(request.GET.get("ligfit_dataset"))
    data = ligfit_dataset.split(";")[0]
    blob = ligfit_dataset.split(";")[1]
    ligand = data.split("-")[-1].split("_")[0]

    entry_dir = path.join(
        "_".join(data.split("_")[:2]), data.split("_")[2], data.split("_")[3]
    )

    rhofit = proj.data_path() + "/fragmax/results/" + entry_dir + "/rhofit/best.pdb"
    ligfit = sorted(
        glob(
            proj.data_path()
            + "/fragmax/results/"
            + entry_dir
            + "/ligfit/LigandFit*/ligand_fit*pdb"
        )
    )[-1]
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

    lines = read_csv_lines(path.join(project_process_protein_dir(proj), "results.csv"))[
        1:
    ]

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


class PanddaDataset(Wrapper):
    """
    wrap pandda dataset description object, so that we
    can remap a couple of attributes for template consumption
    """

    def name(self):
        return self.orig.dtag

    def resolution(self):
        return self.orig.high_resolution


class PanddaEvent(Wrapper):
    """
    wrap pandda event object, to give access to '1-BDC' value to template
    """

    def bdc(self):
        return self.orig["1-BDC"]


def pandda_analyse(request, method: str, dataset_name: str):
    project = current_project(request)

    analysis_dir = Path(project.pandda_method_dir(method), "pandda", "analyses")

    # load analyse events
    events = PanddaAnalyseEvents(Path(analysis_dir, "pandda_analyse_events.csv"))
    event = events.get_first_event(dataset_name)

    # load analyse sites
    sites = PanddaAnalyseSites(Path(analysis_dir, "pandda_analyse_sites.csv"))

    # load pandda dataset description
    all_datasets = PanddaAllDatasetInfo(Path(analysis_dir, "all_datasets_info.csv"))
    dataset = PanddaDataset(all_datasets.get_dataset(dataset_name))

    # fetch fragment object from the database
    db_dataset = get_dataset_by_name(project, dataset_name)
    fragment = db_dataset.crystal.fragment

    # derive path to analysis summary report
    summary_path = Path(
        project.pandda_processed_dataset_dir(method, dataset_name),
        "html",
        f"{dataset_name}.html",
    )

    return render(
        request,
        "fragview/pandda_densityA.html",
        {
            "event": PanddaEvent(event),
            "method": method,
            "dataset": dataset,
            "fragment": fragment,
            "ground_model": event is None,
            "centroids": list(sites.get_native_centroids()),
            "summary": summary_path.relative_to(project.project_dir),
        },
    )


def pandda(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get("structure"))

    if len(panddaInput.split(";")) == 5:
        method, dataset, event, site, nav = panddaInput.split(";")
    if len(panddaInput.split(";")) == 3:
        method, dataset, nav = panddaInput.split(";")

    pandda_res_dir = path.join(
        project_results_dir(proj), "pandda", proj.protein, method, "pandda"
    )
    datasets_dir = path.join(pandda_res_dir, "processed_datasets")

    mdl = [
        x.split("/")[-3]
        for x in sorted(glob(f"{datasets_dir}/*/modelled_structures/*model.pdb"))
    ]

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

        pandda_res_dir = path.join(
            project_results_dir(proj), "pandda", proj.protein, method, "pandda"
        )
        _sites = path.join(pandda_res_dir, "analyses", "pandda_analyse_sites.csv")
        centroids = find_site_centroids(_sites)

        with open(
            path.join(pandda_res_dir, "analyses", "pandda_inspect_events.csv"), "r"
        ) as inp:
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
                "rwork": rwork,
                "rfree": rfree,
                "resolution": resolution,
                "spg": spg,
                "dataset": dataset,
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
            {
                "issue": "No modelled structure for "
                + method
                + "_"
                + dataset
                + " was found."
            },
        )


def pandda_consensus(request):
    proj = current_project(request)

    panddaInput = str(request.GET.get("structure"))

    dataset, site_idx, event_idx, method, ddtag, run = panddaInput.split(";")

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

    pandda_res_dir = path.join(
        project_results_dir(proj), "pandda", proj.protein, method, "pandda"
    )
    _sites = path.join(pandda_res_dir, "analyses", "pandda_analyse_sites.csv")
    centroids = find_site_centroids(_sites)
    events_csv = path.join(pandda_res_dir, "analyses", "pandda_inspect_events.csv")
    with open(events_csv, "r") as inp:
        inspect_events = inp.readlines()

    for i in inspect_events:
        if dataset + ddtag + "_" + run in i:
            line = i.split(",")
            if (
                dataset + ddtag + "_" + run == line[0]
                and event_idx == line[1]
                and site_idx == line[11]
            ):
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

    lines = read_csv_lines(
        path.join(project_process_protein_dir(proj), "panddainspects.csv")
    )[1:]

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
            "library": proj.library,
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


def find_refinement_log(proj_dir, res_dir):
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
            pipelineLog = path.join(
                path.dirname(path.dirname(logFile)), "fspipeline.log"
            )

    if "buster" in res_dir:
        logSearch = sorted(glob(f"{res_dir}/*BUSTER/Cycle*/*html"))
        if logSearch:
            logFile = logSearch[-1]
            pipelineLog = logSearch[-1]

    return Path(logFile).relative_to(proj_dir), Path(pipelineLog).relative_to(proj_dir)


def find_ligandfitting_log(proj_dir, res_dir):
    rhofitSearch = glob(f"{res_dir}/rhofit/results.txt")
    if rhofitSearch:
        rhofitlog = Path(rhofitSearch[0]).relative_to(proj_dir)
    else:
        rhofitlog = ""

    ligandfitSearch = glob(f"{res_dir}/ligfit/LigandFit_run*/ligand_*.log")
    if ligandfitSearch:
        ligandfitlog = Path(ligandfitSearch[0]).relative_to(proj_dir)
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
