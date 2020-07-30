from os import path
from django.shortcuts import render
from django.contrib import messages
from fragview.sites import SITE
from fragview.projects import current_project
from fragview.models import Fragment
from fragview import hpc
from fragview.projects import project_raw_master_h5_files
from ast import literal_eval
from time import sleep
import csv
import io


def project_details(request):
    return render(request, "fragview/project_details.html")


def library_view(request):
    proj = current_project(request)

    lib = proj.library
    fragments = sorted(
        [
            path.basename(x).split("-")[-1].split("_")[0]
            for x in list(project_raw_master_h5_files(proj))
            if "Apo" not in x
        ]
    )

    project_fragments = dict()
    missing_fragments = dict()
    for frag in fragments:
        if lib.get_fragment(frag) is None:
            missing_fragments[frag] = frag
        else:
            project_fragments[frag] = lib.get_fragment(frag).smiles
    data_path = proj.data_path().replace("/data/visitors/", "/static/")

    if request.method == "GET":
        return render(
            request,
            "fragview/library_view.html",
            {"project_fragments": project_fragments, "missing_fragments": missing_fragments, "data_path": data_path},
        )
    csv_file = request.FILES["fragments_file"]
    if not csv_file.name.endswith(".csv"):
        messages.error(request, "This is not a CSV file")

    data_frags = csv_file.read().decode("utf-8")
    io_string = io.StringIO(data_frags)
    updated_frags = dict()
    id_db = lib.id
    for column in csv.reader(io_string, delimiter=","):
        if len(column) == 2:
            fragID, smiles = column
            if lib.get_fragment(fragID) is not None:
                if lib.get_fragment(fragID).smiles == smiles:
                    print("No change")
                else:
                    print("Updated fragmet " + fragID)
                    frag_db_id = lib.get_fragment(fragID).id
                    lib.get_fragment(fragID).smiles = smiles
                    print(lib.get_fragment(fragID).smiles)
                    f = Fragment.objects.get(id=frag_db_id)
                    f.smiles = smiles
                    f.save()
                    print(lib.get_fragment(fragID).smiles)
                    updated_frags[fragID] = smiles
            else:
                print("New fragment " + fragID)
                new_frag_entry = Fragment(library_id=id_db, name=fragID, smiles=smiles)
                new_frag_entry.save()
                updated_frags[fragID] = smiles

        else:
            messages.error(request, "The library CSV should be: fragmentID, SMILES " + "".join(column))
    if updated_frags:
        script_dir = path.join(proj.data_path(), "fragmax", "scripts")
        script = path.join(script_dir, f"elbow.sh")
        with open(script, "w") as outfile:
            outfile.write("#!/bin/bash\n")
            outfile.write("#!/bin/bash\n")
            outfile.write("module purge\n")
            outfile.write("module load gopresto Phenix\n")
            for fragID, smiles in updated_frags.items():
                outfile.write(f"cd {proj.data_path()}/fragmax/fragments/\n")
                outfile.write(f"phenix.elbow --smiles='{smiles}' --output={fragID}\n")
        hpc.run_sbatch(script)
    sleep(5)
    return render(
        request,
        "fragview/library_view.html",
        {"project_fragments": project_fragments, "missing_fragments": missing_fragments, "data_path": data_path},
    )


def download_options(request):
    return render(request, "fragview/download_options.html")


def testfunc(request):
    return render(request, "fragview/testpage.html", {"files": "results"})


def ugly(request):
    return render(request, "fragview/ugly.html")


def log_viewer(request):
    logFile = request.GET["logFile"]
    downloadPath = f"/static/biomax{logFile[len(SITE.PROPOSALS_DIR):]}"
    if path.exists(logFile):
        if path.splitext(logFile)[-1] == ".json" and "pandda" in logFile:
            filetype = "json"
            with open(logFile, "r", encoding="utf-8") as r:
                init_log = literal_eval(r.read())
            log = "<table>\n"
            for k, v in sorted(init_log.items()):
                log += f"<tr><td>{k}</td><td> {v}</td></tr>\n"
            log += "</table>"
        else:
            filetype = "txt"
            with open(logFile, "r", encoding="utf-8") as r:
                log = r.read()
    else:
        filetype = ""
        log = ""
    return render(
        request,
        "fragview/log_viewer.html",
        {"log": log, "dataset": logFile, "downloadPath": downloadPath, "filetype": filetype},
    )


def perc2float(v):
    return str("{:.3f}".format(float(v.replace("%", "")) / 100.0))
