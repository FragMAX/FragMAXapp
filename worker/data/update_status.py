from glob import glob
import csv
import sys


def get_dataset_status(proposal, shift, protein, dataset, run):
    dps1 = glob(
        f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/*/*mtz")
    dps2 = glob(
        f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/{dataset}/{dataset}_{run}/*/*/*mtz")
    dps3 = glob(f"/data/visitors/biomax/{proposal}/{shift}/process/{protein}/{dataset}/*/*/results/*mtz*")
    dp_full = set(
        [x.split("/")[11] for x in dps1 + dps2] + [x.split("/")[10].replace("EDNA_proc", "edna") for x in dps3 if
                                                   "autoPROC" not in x])

    dp_status = dict(
        autoproc="none",
        dials="none",
        edna="none",
        fastdp="none",
        xdsapp="none",
        xdsxscale="none")

    for proc in dp_full:
        dp_status[proc] = "full"

    rf_full = set([x.split("/")[10] for x in glob(
        f"/data/visitors/biomax/{proposal}/{shift}/fragmax/results/{dataset}_{run}/*/*/final.pdb")])

    rf_status = dict(
        dimple="none",
        fspipeline="none",
        buster="none")

    for ref in rf_full:
        rf_status[ref] = "full"

    lg_full = set([x.split("/")[11] for x in glob(
        f"/data/visitors/biomax/{proposal}/{shift}/fragmax/results/{dataset}_{run}/*/*/ligfit/*/*.pdb") + glob(
        f"/data/visitors/biomax/{proposal}/{shift}/fragmax/results/{dataset}_{run}/*/*/rhofit/*.pdb")])
    lg_status = {"rhofit": "none",
                 "ligfit": "none"}
    for lig in lg_full:
        lg_status[lig] = "full"

    d4 = dict(dp_status, **rf_status)
    d4.update(lg_status)

    return d4


def update_all_status_csv(proposal, shift, protein, statusDict, dataset, run):
    allcsv = f"/data/visitors/biomax/{proposal}/{shift}/fragmax/process/{protein}/allstatus.csv"

    with open(allcsv, "r") as readFile:
        csvfile = list(csv.reader(readFile))

    # Get index of the dataset to be updated
    for row in csvfile:
        if row[0] == dataset + "_" + run:
            row_to_change = csvfile.index(row)
            print(row_to_change)
            # Create the list with new values for process, refine, ligfit status
            # and update the csv file
            updated_value = [dataset + "_" + run] + list(statusDict.values())
            csvfile[row_to_change] = updated_value
            print(updated_value)
            # write the new csv file with updated values
            with open(allcsv, "w") as writeFile:
                writer = csv.writer(writeFile)
                writer.writerows(csvfile)


# Copy data from beamline auto processing to fragmax folders
dataset, run = sys.argv[1].split("_")
proposal, shift = sys.argv[2].split("/")
protein = dataset.split("-")[0]
statusDict = get_dataset_status(proposal, shift, protein, dataset, run)
update_all_status_csv(proposal, shift, protein, statusDict, dataset, run)
