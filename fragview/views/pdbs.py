import os
import re
import pypdb
from os import path
from django import urls
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.db import transaction
from django.db.utils import IntegrityError
from fragview.fileio import open_proj_file
from fragview.models import PDB
from fragview.projects import current_project
from fragview import hpc


#
# PDB files uploaded by the user must match this regexp,
# to prevent weird issues, as we use the filename to derive paths.
#
# Let's be restrictive for now.
# Only alphanumeric characters allowed and '.pdb' is the only allowed
# file extension.
#
VALID_PDB_FNAME_REGEXP = r"^([a-z0-9_])+\.pdb$"


class PDBAddError(Exception):
    def error_message(self):
        return self.args[0]


def list(request):
    """
    protein models list page, aka 'manage pdbs' page
    """
    proj = current_project(request)
    return render(request, "fragview/pdbs.html", {"pdbs": PDB.project_pdbs(proj)})


def _is_valid_pdb_filename(filename):
    m = re.match(VALID_PDB_FNAME_REGEXP, filename, re.IGNORECASE)
    return m is not None


def _add_pdb_entry(project, filename, pdb_id=None):
    """
    add 'PDB model' entry for specified project to the database
    """
    if not _is_valid_pdb_filename(filename):
        raise PDBAddError("Invalid PDB filename, only letters and number are allowed.")

    args = dict(project=project, filename=filename)
    if pdb_id is not None:
        args["pdb_id"] = pdb_id

    try:
        pdb = PDB(**args)
        pdb.save()
    except IntegrityError:
        # here we assume that 'unique filename per project' constrain is violated,
        # as we don't have any other constrains for the PDB table
        raise PDBAddError(f"Model file '{filename}' already exists in the project.")

    return pdb


def _fetch_from_rcsb(pdb_id):
    pdb_data = pypdb.get_pdb_file(pdb_id, filetype="pdb")
    if pdb_data is None:
        raise PDBAddError(f"no PDB with ID '{pdb_id}' found")

    return pdb_data.encode()


def _assemble_chunks(upload_file):
    data = b""
    for chunk in upload_file.chunks():
        data += chunk

    return data


def _save_pdb(proj, pdb_id, filename, pdb_data):
    name = path.splitext(filename)[0]
    nohet_filename = f"{name}_noHETATM.pdb"
    nohet_filename = f"{name}_noANISOU.pdb"
    nohet_filename = f"{name}_noANISOU_noHETATM.pdb"
    txc_filename = f"{name}_txc.pdb"

    orig_pdb = _add_pdb_entry(proj, filename, pdb_id)
    nohet_pdb = _add_pdb_entry(proj, nohet_filename, pdb_id)
    noanisou_pdb = _add_pdb_entry(proj, nohet_filename, pdb_id)
    nohetnoanisou_pdb = _add_pdb_entry(proj, nohet_filename, pdb_id)

    # write original pdb file 'as-is' to models folder
    with open_proj_file(proj, orig_pdb.file_path()) as dest:
        dest.write(pdb_data)

    # filter out all non-ATOM entries from pdb and write it as *_noHETATM.pdb
    with open_proj_file(proj, nohetnoanisou_pdb.file_path()) as dest:
        for line in pdb_data.splitlines(keepends=True):
            if not line.startswith(b"HETATM") or not line.startswith(b"ANISOU"):
                dest.write(line)

    with open_proj_file(proj, nohet_pdb.file_path()) as dest:
        for line in pdb_data.splitlines(keepends=True):
            if not line.startswith(b"HETATM"):
                dest.write(line)

    with open_proj_file(proj, noanisou_pdb.file_path()) as dest:
        for line in pdb_data.splitlines(keepends=True):
            if not line.startswith(b"ANISOU"):
                dest.write(line)

    if pdb_chains(pdb_data.splitlines(keepends=True)) > 1:
        txc_pdb = _add_pdb_entry(proj, txc_filename, pdb_id)
        script_dir = path.join(proj.data_path(), "fragmax", "scripts")
        script = path.join(script_dir, f"phenix_ensembler.sh")
        models_path = f"{proj.data_path()}/fragmax/models"
        input_pdb_name = f"{models_path}/{name}"
        with open(script, "w") as outfile:
            outfile.write("#!/bin/bash\n")
            outfile.write("#!/bin/bash\n")
            outfile.write("module purge\n")
            outfile.write("module load gopresto Phenix\n")
            outfile.write(f"cd {models_path}\n")
            outfile.write(
                f"phenix.ensembler {input_pdb_name} trim=TRUE output.location='{proj.data_path()}/fragmax/models/'\n"
            )
            outfile.write(f"mv {models_path}/ensemble_merged.pdb {txc_pdb.file_path()}\n")
        hpc.run_sbatch(script)


#
# Wrap the database operation of adding a new PDB entry into
# a transaction.
#
# This way if we fail to write the PDB file to disk, the new
# PDB entry will not be commited to the database.
#
@transaction.atomic
def _process_add_request(request):
    proj = current_project(request)
    method = request.POST["method"]

    try:
        if method == "upload_file":
            uploaded = request.FILES["pdb"]
            data = _assemble_chunks(uploaded)
            filename = uploaded.name
            pdb_id = None
        else:
            assert method == "fetch_online"
            pdb_id = request.POST["pdb_id"]
            data = _fetch_from_rcsb(pdb_id)
            filename = f"{pdb_id}.pdb"

        _save_pdb(proj, pdb_id, filename, data)

    except FileNotFoundError as e:
        raise PDBAddError(f"Internal error saving PDB file\n{e}")


def add(request):
    """
    the 'add new PDB' page
    """
    return render(request, "fragview/add_pdb.html")


def new(request):
    """
    adds new PDB to the project

    this route processes the 'add PDB' form submission
    """
    try:
        _process_add_request(request)
        return HttpResponse("looking good")
    except PDBAddError as err:
        return HttpResponseBadRequest(err.error_message())


def _delete_pdb(pdb):
    os.remove(pdb.file_path())
    pdb.delete()


def edit(request, id):
    """
    GET request shows the 'PDB info' page
    POST request will delete the PDB
    """
    pdb = get_object_or_404(PDB, pk=id)

    if request.method == "POST":
        _delete_pdb(pdb)
        return redirect(urls.reverse("manage_pdbs"))

    return render(request, "fragview/pdb.html", {"pdb": pdb})


def pdb_chains(pdb_lines):
    chains = {}
    for pdb_line in pdb_lines:
        line = pdb_line.rstrip("\n")
        if line[0:4] == "ATOM":
            chain = line[21:22]
            if chain not in chains:
                chains[chain] = {}
                chains[chain]["min"] = int(line[22:26])
                chains[chain]["max"] = int(line[22:26])
            else:
                if int(line[22:26]) < chains[chain]["min"]:
                    chains[chain]["min"] = int(line[22:26])
                if int(line[22:26]) > chains[chain]["max"]:
                    chains[chain]["max"] = int(line[22:26])
    return len(chains)
