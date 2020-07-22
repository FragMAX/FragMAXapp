import os
import csv
import sys
import subprocess
import shutil
from glob import glob
from ast import literal_eval

# CLI Arguments
path = sys.argv[1]
protein = sys.argv[2]
options = sys.argv[3]
options = literal_eval(options)
method = options["method"]


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def dataset_exists(dataset_list):
    datasets = dataset_list.split(",")

    existing_datasets = [dataset for dataset in datasets if os.path.exists(path + "/" + dataset)]
    return ",".join(existing_datasets)


def ground_state_entries(options):
    # process user input and find models for ground state
    if any([options["useApos"], options["useSelected"]]):
        apo_datasets = ",".join([x.split("/")[-1] for x in
                                 glob(path + "/*Apo*")])

        dtsfilter = options['dtsfilter']
        user_defined_gs = dtsfilter.split(":")[-1]
        if all([options["useApos"], options["useSelected"]]):
            total_ground_datasets = user_defined_gs + "," + apo_datasets
            total_ground_datasets = dataset_exists(total_ground_datasets)
            ground_state_parameter = "ground_state_datasets='" + total_ground_datasets + "'"
        elif options["useApos"]:
            total_ground_datasets = apo_datasets
            total_ground_datasets = dataset_exists(total_ground_datasets)
            ground_state_parameter = "ground_state_datasets='" + total_ground_datasets + "'"
        elif options["useSelected"]:
            total_ground_datasets = user_defined_gs
            total_ground_datasets = dataset_exists(total_ground_datasets)
            ground_state_parameter = "ground_state_datasets='" + total_ground_datasets + "'"

        if total_ground_datasets.count(",") < (options["min_datasets"] - 1):
            ground_state_parameter = ""
            print("---FragMAXapp Log---")
            print("Not enough datasets to build ground state model from selection")
            print("ignoring declared apo datasets for this run")
        else:
            ground_state_parameter = "ground_state_datasets='" + total_ground_datasets + "'"
    else:
        ground_state_parameter = ""
    return ground_state_parameter


def find_bad_dataset(lastlog, options):
    with open(lastlog, "r") as logfile:
        log = logfile.readlines()
    badDataset = dict()
    for line in log:
        if "Structure factor column" in line:
            bd = line.split(" has ")[0].split("in dataset ")[-1]
            bdpath = glob(path + "/" + bd + "*")
            badDataset[bd] = bdpath
            options["rerun_state"] = True

        if "Failed to align dataset" in line:
            bd = line.split("Failed to align dataset ")[1].rstrip()
            bdpath = glob(path + "/" + bd + "*")
            badDataset[bd] = bdpath
            options["rerun_state"] = True
    if badDataset:
        print("---FragMAXapp Log---")
        print("Removed datasets with issues")
        print(badDataset)
    for dataset_path in badDataset.values():
        if os.path.exists(dataset_path[0]):
            shutil.rmtree(dataset_path[0])

    return badDataset


def pandda_run(method, options):
    ground_state_parameter = ground_state_entries(options)

    os.chdir(path)

    command = "pandda.analyse data_dirs='" + path + "/*' " + \
              ground_state_parameter + " " + options["customPanDDA"] + \
              "min_build_datasets=" + str(options["min_datasets"]) + " cpus=" + str(options["nproc"])

    subprocess.call(command, shell=True)

    logs = glob(path + "/pandda/logs/*.log")
    if len(logs) > 0:
        lastlog = sorted(logs)[-1]
        with open(lastlog, "r") as logfile:
            log = logfile.readlines()

        badDataset = find_bad_dataset(lastlog, options)

        for k, v in badDataset.items():
            if all([v, options["initpass"]]):
                if os.path.exists(v[0]):
                    shutil.rmtree(v[0])
                    if os.path.exists(path + "/fragmax/process/pandda/ignored_datasets/" + options["method"] + "/" + k):
                        shutil.rmtree(path + "/fragmax/process/pandda/ignored_datasets/" + options["method"] + "/" + k)
                pandda_run(method, options)


pandda_run(method, options)
