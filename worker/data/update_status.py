import argparse
from glob import glob
from os import path
import csv


def get_dataset_status(project_dir, protein, dataset, run):
    print(dataset + "\n")
    dp_status = dict(
        autoproc="none",
        dials="none",
        edna="none",
        fastdp="none",
        xdsapp="none",
        xdsxscale="none")

    dataset_run = f"{dataset}_{run}"
    dset_proc_dir = path.join(project_dir, "fragmax", "process", protein, dataset, dataset_run)
    dset_results_dir = path.join(project_dir, "fragmax", "results", dataset_run)

    # Find XIA2/dials
    dp_dials = [path.join(dset_proc_dir, "dials")]

    # Find XIA2/xds
    dp_xdsxscale = [path.join(dset_proc_dir, "xdsxscale")]

    # Find autoPROC
    dp_ap = [path.join(dset_proc_dir, "autoproc")]

    # Find XDSAPP
    dp_xdsapp = [path.join(dset_proc_dir, "xdsapp")]

    # Find EDNA_proc
    dp_edna = [path.join(dset_proc_dir, "edna")]

    # Find fastdp
    dp_fastdp = [path.join(dset_proc_dir, "fastdp")]

    all_dp_logs = dp_dials + dp_xdsxscale + dp_ap + dp_xdsapp + dp_edna + dp_fastdp
    dp_state = [get_status_dp(x) for x in all_dp_logs]

    for entry in dp_state:
        if entry is not None:
            proc, status = entry.split("/")
            dp_status[proc] = status

    # REFINEMENT
    rf_folders = [x for x in glob(f"{dset_results_dir}/*/*/") if "pipedream" not in x]

    rf_state = [get_status_ref(x) for x in rf_folders]
    rf_status = dict(
        xdsapp_dimple="none",
        autoproc_dimple="none",
        dials_dimple="none",
        xdsxscale_dimple="none",
        edna_dimple="none",
        fastdp_dimple="none",
        xdsapp_fspipeline="none",
        autoproc_fspipeline="none",
        dials_fspipeline="none",
        xdsxscale_fspipeline="none",
        edna_fspipeline="none",
        fastdp_fspipeline="none",
        xdsapp_buster="none",
        autoproc_buster="none",
        dials_buster="none",
        xdsxscale_buster="none",
        edna_buster="none",
        fastdp_buster="none")

    for entry in rf_state:
        if entry is not None:
            proc, status = entry.split("/")
            rf_status[proc] = status

    a_list = ["full", "partial", "none"]
    order_rf = sorted(rf_status.items(), key=lambda pair: a_list.index(pair[1]), reverse=True)
    rf_status_simple = {k[0].split("_")[-1]: k[1] for k in order_rf}

    # LIGAND FITTING
    lg_folders = glob(f"{dset_results_dir}/*/*/*fit/")

    lg_state = [get_status_lig(x) for x in lg_folders]
    lg_status = dict(
        xdsapp_dimple_ligfit="none",
        xdsapp_dimple_rhofit="none",
        autoproc_dimple_ligfit="none",
        autoproc_dimple_rhofit="none",
        dials_dimple_ligfit="none",
        dials_dimple_rhofit="none",
        xdsxscale_dimple_ligfit="none",
        xdsxscale_dimple_rhofit="none",
        edna_dimple_ligfit="none",
        edna_dimple_rhofit="none",
        fastdp_dimple_ligfit="none",
        fastdp_dimple_rhofit="none",
        xdsapp_fspipeline_ligfit="none",
        xdsapp_fspipeline_rhofit="none",
        autoproc_fspipeline_ligfit="none",
        autoproc_fspipeline_rhofit="none",
        dials_fspipeline_ligfit="none",
        dials_fspipeline_rhofit="none",
        xdsxscale_fspipeline_ligfit="none",
        xdsxscale_fspipeline_rhofit="none",
        edna_fspipeline_ligfit="none",
        edna_fspipeline_rhofit="none",
        fastdp_fspipeline_ligfit="none",
        fastdp_fspipeline_rhofit="none",
        xdsapp_buster_ligfit="none",
        xdsapp_buster_rhofit="none",
        autoproc_buster_ligfit="none",
        autoproc_buster_rhofit="none",
        dials_buster_ligfit="none",
        dials_buster_rhofit="none",
        xdsxscale_buster_ligfit="none",
        xdsxscale_buster_rhofit="none",
        edna_buster_ligfit="none",
        edna_buster_rhofit="none",
        fastdp_buster_ligfit="none",
        fastdp_buster_rhofit="none"
    )

    for entry in lg_state:
        if entry is not None:
            proc, status = entry.split("/")
            lg_status[proc] = status

    a_list = ["full", "partial", "none"]
    order_lg = sorted(lg_status.items(), key=lambda pair: a_list.index(pair[1]), reverse=True)
    lg_status_simple = {k[0].split("_")[-1]: k[1] for k in order_lg}

    ppd_proc = glob(f"{dset_results_dir}/pipedream/process*/summary.html")
    ppd_ref = glob(f"{dset_results_dir}/pipedream/*/BUSTER_model.pdb")
    ppd_lig = glob(f"{dset_results_dir}/pipedream/*/best.pdb")

    ppd_status = get_status_pipedream(ppd_proc, ppd_ref, ppd_lig)
    d4 = dict(dp_status, **rf_status_simple, **lg_status_simple, **ppd_status)

    [print(k, ":", v) for (k, v) in d4.items()]

    return d4


def get_status_pipedream(proc, ref, lig):
    ppd = {"pipedreamproc": "",
           "pipedreamref": "",
           "pipedreamlig": ""}
    if proc:
        logfile = proc[0]
        if path.exists(f"{logfile}"):
            if path.exists(f"{logfile}"):
                with open(f"{logfile}", "r", encoding="utf-8") as r:
                    log = r.read()
                if '<div class="errorheader">ERROR</d>' in log:
                    ppd["pipedreamproc"] = "partial"
                else:
                    ppd["pipedreamproc"] = "full"
        else:
            ppd["pipedreamproc"] = "none"

    if ref:
        pdb_file = ref[0]
        if path.exists(f"{pdb_file}"):
            with open(f"{pdb_file}", "r", encoding="utf-8") as r:
                log = r.read()
            if '<div class="errorheader">ERROR</d>' in log:
                ppd["pipedreamref"] = "partial"
            else:
                ppd["pipedreamref"] = "full"
    else:
        ppd["pipedreamref"] = "none"

    if lig:
        rhofit_file = lig[0]
        if path.exists(f"{rhofit_file}"):
            with open(f"{rhofit_file}", "r", encoding="utf-8") as r:
                log = r.read()
            if '<div class="errorheader">ERROR</d>' in log:
                ppd["pipedreamlig"] = "partial"
            else:
                ppd["pipedreamlig"] = "full"
    else:
        ppd["pipedreamlig"] = "none"
    return ppd


def get_status_dp(logfile):
    if "dials" in logfile or "xdsxscale" in logfile:
        if path.exists(f"{logfile}/xia2.txt"):
            with open(f"{logfile}/xia2.txt", "r", encoding="utf-8") as r:
                log = r.read()
            if "Status: normal termination" in log or 'Scaled reflections (' in log:
                return logfile.split("fragmax")[-1].split("/")[-1] + "/full"
            else:
                return logfile.split("fragmax")[-1].split("/")[-1] + "/partial"
        else:
            return logfile.split("fragmax")[-1].split("/")[-1] + "/none"

    if "autoproc" in logfile:
        if path.exists(f"{logfile}"):
            if path.exists(f"{logfile}/summary.html"):
                with open(f"{logfile}/summary.html", "r", encoding="utf-8") as r:
                    log = r.read()
                if '<div class="errorheader">ERROR</d>' in log:
                    return logfile.split("fragmax")[-1].split("/")[-1] + "/partial"
                else:
                    return logfile.split("fragmax")[-1].split("/")[-1] + "/full"
        else:
            return logfile.split("fragmax")[-1].split("/")[-1] + "/none"

    if "xdsapp" in logfile:
        if glob(f"{logfile}/*mtz"):
            return logfile.split("fragmax")[-1].split("/")[-1] + "/full"
        elif glob(f"{logfile}/*LP"):
            for LPfile in glob(f"{logfile}/*LP"):
                with open(LPfile, "r", encoding="utf-8") as r:
                    log = r.read()
                if "!!! ERROR" in log:
                    return logfile.split("fragmax")[-1].split("/")[-1] + "/partial"
                else:
                    return logfile.split("fragmax")[-1].split("/")[-1] + "/none"
        else:
            return logfile.split("fragmax")[-1].split("/")[-1] + "/none"

    if "edna" in logfile:

        if glob(f"{logfile}/*.mtz"):
            return logfile.split("fragmax")[-1].split("/")[-1] + "/full"
        elif glob(f"{logfile}/*"):
            return logfile.split("fragmax")[-1].split("/")[-1] + "/partial"
        else:
            return logfile.split("fragmax")[-1].split("/")[-1] + "/none"

    if "fastdp" in logfile:
        if glob(f"{logfile}/*.mtz"):
            return logfile.split("fragmax")[-1].split("/")[-1] + "/full"
        elif glob(f"{logfile}/*"):
            return logfile.split("fragmax")[-1].split("/")[-1] + "/partial"
        else:
            return logfile.split("fragmax")[-1].split("/")[-1] + "/none"


def get_status_ref(folder):
    if path.exists(f"{folder}final.pdb"):
        return "_".join(folder.split("fragmax")[-1].split("/")[3:5]).lower() + "/full"
    elif glob(f"{folder}*"):
        return "_".join(folder.split("fragmax")[-1].split("/")[3:5]).lower() + "/partial"
    else:
        return "_".join(folder.split("fragmax")[-1].split("/")[3:5]).lower() + "/none"


def get_status_lig(folder):
    if "ligfit" in folder:
        if glob(f"{folder}LigandFit_run*/*final.pdb"):
            return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/full"
        elif glob(f"{folder}LigandFit_run*"):
            return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/partial"
        else:
            return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/none"
    elif "rhofit" in folder:
        if glob(f"{folder}*.pdb"):
            return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/full"
        elif glob(f"{folder}*"):
            return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/partial"
        else:
            return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/none"
    else:
        return "_".join(folder.split("fragmax")[-1].split("/")[3:6]).lower() + "/none"


def update_all_status_csv(project_dir, protein, dataset, run, statusDict):
    def _write_csv():
        with open(allcsv, "w") as writeFile:
            writer = csv.writer(writeFile)
            writer.writerows(csvfile)

    allcsv = path.join(project_dir, "fragmax", "process", protein, "allstatus.csv")

    dataset_run = f"{dataset}_{run}"

    with open(allcsv, "r") as readFile:
        csvfile = list(csv.reader(readFile))
    csvfile = [x for x in csvfile if len(x) == 15]

    # Get index of the dataset to be updated
    dataset_names = [row[0] for row in csvfile if len(row) > 10]

    for row in csvfile:
        if len(row) > 10:
            if row[0] == dataset_run:
                row_to_change = csvfile.index(row)
                # Create the list with new values for process, refine, ligfit status
                # and update the csv file
                updated_value = [dataset + "_" + run] + list(statusDict.values())
                csvfile[row_to_change] = updated_value
                # write the new csv file with updated values
                _write_csv()

    dset_dir = path.join(project_dir, "fragmax", "process", protein, dataset, dataset_run)
    if f"{dataset}_{run}" not in dataset_names and path.exists(dset_dir):
        updated_value = [dataset + "_" + run] + list(statusDict.values())
        csvfile.append(updated_value)
        print(updated_value)
        # write the new csv file with updated values
        _write_csv()


def parse_args():
    parser = argparse.ArgumentParser(description="update datasets status")
    parser.add_argument("project_dir")
    parser.add_argument("dataset")
    parser.add_argument("run")

    args = parser.parse_args()
    protein = args.dataset.split("-")[0]

    return args.project_dir, protein, args.dataset, args.run


def main():
    project_dir, protein, dataset, run = parse_args()
    status = get_dataset_status(project_dir, protein, dataset, run)
    update_all_status_csv(project_dir, protein, dataset, run, status)


main()
