import re
import pypdb
from os import path
from django import urls
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from projects.database import commit, TransactionIntegrityError
from fragview.fileio import open_proj_file
from fragview.projects import (
    current_project,
    project_syslog_path,
    project_script,
    Project,
)
from fragview.views.utils import download_http_response, get_pdb_by_id
from fragview.sites import SITE
from fragview.versions import PHENIX_MOD
from jobs.client import JobsSet


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
    return render(request, "pdbs.html")


def _is_valid_pdb_filename(filename):
    m = re.match(VALID_PDB_FNAME_REGEXP, filename, re.IGNORECASE)
    return m is not None


def _add_pdb_entry(project: Project, filename, pdb_id=None):
    """
    add 'PDB model' entry for specified project to the database
    """
    if not _is_valid_pdb_filename(filename):
        raise PDBAddError("Invalid PDB filename, only letters and number are allowed.")

    args = dict(filename=filename)
    if pdb_id is not None:
        args["pdb_id"] = pdb_id

    try:
        pdb = project.db.PDB(**args)
        commit()
    except TransactionIntegrityError:
        # here we assume that 'unique PDB filename per project' constrain is violated,
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


def _save_pdb(project: Project, pdb_id, filename, pdb_data):
    name = path.splitext(filename)[0]
    nohet_filename = f"{name}_noHETATM.pdb"
    noanisou_filename = f"{name}_noANISOU.pdb"
    nohetanisou_filename = f"{name}_noANISOU_noHETATM.pdb"
    txc_filename = f"{name}_txc.pdb"

    orig_pdb = _add_pdb_entry(project, filename, pdb_id)
    nohet_pdb = _add_pdb_entry(project, nohet_filename, pdb_id)
    noanisou_pdb = _add_pdb_entry(project, noanisou_filename, pdb_id)
    nohetnoanisou_pdb = _add_pdb_entry(project, nohetanisou_filename, pdb_id)

    # write original pdb file 'as-is' to models folder
    with open_proj_file(project, project.get_pdb_file(orig_pdb)) as dest:
        dest.write(pdb_data)

    # filter out all non-ATOM entries from pdb and write it as *_noHETATM.pdb
    with open_proj_file(project, project.get_pdb_file(nohetnoanisou_pdb)) as dest:
        for line in pdb_data.splitlines(keepends=True):
            if not line.startswith(b"HETATM") or not line.startswith(b"ANISOU"):
                dest.write(line)

    with open_proj_file(project, project.get_pdb_file(nohet_pdb)) as dest:
        for line in pdb_data.splitlines(keepends=True):
            if not line.startswith(b"HETATM"):
                dest.write(line)

    with open_proj_file(project, project.get_pdb_file(noanisou_pdb)) as dest:
        for line in pdb_data.splitlines(keepends=True):
            if not line.startswith(b"ANISOU"):
                dest.write(line)

    n_chains = pdb_chains(pdb_data.splitlines(keepends=True))

    if n_chains > 1:
        txc_pdb = _add_pdb_entry(project, txc_filename, pdb_id)

        input_pdb_name = path.join(project.models_dir, f"{name}.pdb")

        jobs = JobsSet("phenix ensembler")
        batch = SITE.get_hpc_runner().new_batch_file(
            "phenix ensembler",
            project_script(project, "phenix_ensembler.sh"),
            project_syslog_path(project, "phenix_ensembler_%j.out"),
            project_syslog_path(project, "phenix_ensembler_%j.err"),
        )
        batch.load_modules(["gopresto", PHENIX_MOD])
        batch.add_commands(
            f"cd {project.models_dir}",
            f"phenix.ensembler {input_pdb_name} trim=TRUE output.location='{project.models_dir}'",
            f"mv {project.models_dir}/ensemble_merged.pdb {project.get_pdb_file(txc_pdb)}",
        )
        batch.save()
        jobs.add_job(batch)
        jobs.submit()


#
# This function is wrapped into a DB session, with an implicit transaction.
#
# Ff we fail to write the PDB file to disk, the new
# PDB entries will not be committed to the database.
#
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
    return render(request, "pdb_add.html")


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


def _delete_pdb(project: Project, pdb):
    project.get_pdb_file(pdb).unlink()
    pdb.delete()


def edit(request, id):
    """
    GET request shows the 'PDB info' page
    POST request will delete the PDB
    """
    project = current_project(request)
    pdb = get_pdb_by_id(project, id)

    if request.method == "POST":
        _delete_pdb(project, pdb)
        return redirect(urls.reverse("manage_pdbs"))

    return render(request, "pdb.html", {"pdb": pdb})


def get(request, id):
    project = current_project(request)
    pdb = get_pdb_by_id(project, id)

    return download_http_response(str(project.get_pdb_file(pdb)))


def pdb_chains(pdb_lines):
    chains = {}
    for pdb_line in pdb_lines:
        line = pdb_line.decode("UTF-8").rstrip("\n")
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
