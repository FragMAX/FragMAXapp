import os
from glob import glob
import sys
import subprocess
import shutil
from ast import literal_eval

# CLI Arguments
path = sys.argv[1]
protein = sys.argv[2]
options = sys.argv[3]
options = literal_eval(options)
#
proposal = path.split("/")[4]
method = options["method"]


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def dataset_exists(dataset_list, options):
    datasets = dataset_list.split(",")
    existing_datasets = [dataset for dataset in datasets if os.path.exists(path + "/fragmax/results/pandda/" +
                                                                           protein + "/" + options["method"] +
                                                                           "/" + dataset)]
    return ",".join(existing_datasets)


def ground_state_entries(options):
    # process user input and find models for ground state
    if any([options["useApos"], options["useSelected"]]):
        apo_datasets = ",".join([x.split("/")[-1] for x in
                                 glob(path + "/fragmax/results/pandda/" + protein + "/" +
                                      options["method"] + "/*Apo*")])
        dtsfilter = options['dtsfilter']
        user_defined_gs = dtsfilter.split(":")[-1]
        if all([options["useApos"], options["useSelected"]]):
            total_ground_datasets = user_defined_gs + "," + apo_datasets
            total_ground_datasets = dataset_exists(total_ground_datasets, options)
            ground_state_parameter = "ground_state_datasets='" + total_ground_datasets + "'"
        elif options["useApos"]:
            total_ground_datasets = apo_datasets
            total_ground_datasets = dataset_exists(total_ground_datasets, options)
            ground_state_parameter = "ground_state_datasets='" + total_ground_datasets + "'"
        elif options["useSelected"]:
            total_ground_datasets = user_defined_gs
            total_ground_datasets = dataset_exists(total_ground_datasets, options)
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
            bdpath = glob(path + "/fragmax/results/pandda/" + protein + "/" + options["method"] + "/" + bd + "*")
            badDataset[bd] = bdpath
            options["rerun_state"] = True
        if "Failed to align dataset" in line:
            bd = line.split("Failed to align dataset ")[1].rstrip()
            bdpath = glob(path + "/fragmax/results/pandda/" + protein + "/" + options["method"] + "/" + bd + "*")
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

    os.chdir(path + "/fragmax/results/pandda/" + protein + "/" + method)

    command = "pandda.analyse data_dirs='" + path + "/fragmax/results/pandda/" + protein + "/" + options["method"] + \
              "/*' " + ground_state_parameter + " cpus=16 "
    print(command)
    subprocess.call(command, shell=True)
    if len(glob(path + "/fragmax/results/pandda/" + protein + "/" + options["method"] + "/pandda/logs/*.log")) > 0:

        lastlog = sorted(glob(path + "/fragmax/results/pandda/" + protein + "/" + options["method"] + "/pandda/logs"
                                                                                                      "/*.log"))[-1]

        with open(lastlog, "r") as logfile:
            log = logfile.readlines()

        badDataset = find_bad_dataset(lastlog, options)
        if options["rerun_state"]:
            pandda_run(method, options)

        for line in log:
            if "Writing PanDDA End-of-Analysis Summary" in line and \
                    all([options["reprocessZmap"], options["initpass"]]):
                with open(
                        path + "/fragmax/results/pandda/" + protein + "/" +
                        options["method"] + "/pandda/analyses/pandda_analyse_events.csv", "r") as readFile:
                    events = csv.reader(readFile)
                    events = [x for x in events][1:]
                noZmap = [x[0] for x in events]
                alldts = [x.split("/")[-1] for x in
                          glob(path + "/fragmax/results/pandda/" + protein + "/" + options["method"] + "/" + protein +
                               "*")]
                newGroundStates = ",".join(list(set(alldts) - set(noZmap)))
                options["useSelected"] = newGroundStates
                options["initpass"] = False
                pandda_run(method, options)

        for k, v in badDataset.items():
            if all([v, options["initpass"]]):
                if os.path.exists(v[0]):
                    shutil.rmtree(v[0])
                    if os.path.exists(path + "/fragmax/process/pandda/ignored_datasets/" + options["method"] + "/" + k):
                        shutil.rmtree(path + "/fragmax/process/pandda/ignored_datasets/" + options["method"] + "/" + k)
                # pandda_run(method, options)
                print("I used to run pandda again here")


pandda_run(method, options)
