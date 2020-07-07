from glob import glob
from os import path
import csv
import sys

dataset, run = sys.argv[1].split("_")
proposal, shift = sys.argv[2].split("/")
protein = dataset.split("-")[0]


def get_dataset_status(proposal, shift, protein, dataset, run):
    print(dataset + "\n")
    dp_status = dict(
        autoproc="none",
        dials="none",
        edna="none",
        fastdp="none",
        xdsapp="none",
        xdsxscale="none")

    # Find XIA2/dials
    dp_dials = [f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/dials"]
    # Find XIA2/xds
    dp_xdsxscale = [
        f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/xdsxscale"]
    # Find autoPROC
    dp_ap = [f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/autoproc"]
    # Find XDSAPP
    dp_xdsapp = [f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/xdsapp"]
    # Find EDNA_proc
    dp_edna = [f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/edna"]
    # Find fastdp
    dp_fastdp = [f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/fastdp"]

    all_dp_logs = dp_dials + dp_xdsxscale + dp_ap + dp_xdsapp + dp_edna + dp_fastdp
    dp_state = [get_status_dp(x) for x in all_dp_logs]

    for entry in dp_state:
        if entry is not None:
            proc, status = entry.split("/")
            dp_status[proc] = status

    # REFINEMENT
    rf_folders = glob(f"/data/visitors/biomax/{proposal}/{shift}/fragmax/results/{dataset}_{run}/*/*/")
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
    lg_folders = glob(f"/data/visitors/biomax/{proposal}/{shift}/fragmax/results/{dataset}_{run}/*/*/*fit/")
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

    print(lg_status)
    d4 = dict(dp_status, **rf_status_simple, **lg_status_simple)

    print(d4)

    return d4


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


def update_all_status_csv(proposal, shift, protein, statusDict, dataset, run):
    allcsv = f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/allstatus.csv"

    with open(allcsv, "r") as readFile:
        csvfile = list(csv.reader(readFile))

    # Get index of the dataset to be updated
    dataset_names = [row[0] for row in csvfile if len(row) > 10]

    for row in csvfile:
        if len(row) > 10:
            if row[0] == dataset + "_" + run:
                row_to_change = csvfile.index(row)
                # Create the list with new values for process, refine, ligfit status
                # and update the csv file
                updated_value = [dataset + "_" + run] + list(statusDict.values())
                csvfile[row_to_change] = updated_value
                # write the new csv file with updated values
                with open(allcsv, "w") as writeFile:
                    writer = csv.writer(writeFile)
                    writer.writerows(csvfile)
    if f"{dataset}_{run}" not in dataset_names and \
            path.exists(f"/data/visitors/biomax/{proposal}/{shift}/fragmax/results/{dataset}_{run}"):
        updated_value = [dataset + "_" + run] + list(statusDict.values())
        csvfile.append(updated_value)
        # write the new csv file with updated values
        with open(allcsv, "w") as writeFile:
            writer = csv.writer(writeFile)
            writer.writerows(csvfile)


# Copy data from beamline auto processing to fragmax folders

statusDict = get_dataset_status(proposal, shift, protein, dataset, run)
update_all_status_csv(proposal, shift, protein, statusDict, dataset, run)
