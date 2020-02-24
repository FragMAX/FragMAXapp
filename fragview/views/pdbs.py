import os
import re
import pypdb
from django import urls
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.utils import IntegrityError
from fragview.models import PDB
from fragview.projects import current_project

#
# PDB files uploaded by the user must match this regexp,
# to prevent wierd issues, as we use the filename to derive paths.
#
# Let's be restrictive for now.
# Only alphanumeric characters allowed and '.pdb' is the only allowed
# file extension.
#
VALID_PDB_FNAME_REGEXP = r"^([a-z0-9])+\.pdb$"


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


def _store_uploaded_pdb(proj, pdb_file):
    # record new PDB model in the database
    pdb = _add_pdb_entry(proj, pdb_file.name)

    # save the file to fragmax project's models directory
    with open(pdb.file_path(), "wb") as dest:
        for chunk in pdb_file.chunks():
            dest.write(chunk)


def _fetch_from_rcsb(proj, pdb_id):
    pdb_data = pypdb.get_pdb_file(pdb_id, filetype="pdb")
    if pdb_data is None:
        raise PDBAddError(f"no PDB with ID '{pdb_id}' found")

    # record new PDB model in the database
    pdb = _add_pdb_entry(proj, f"{pdb_id}.pdb", pdb_id)

    # save the file to fragmax project's models directory
    with open(pdb.file_path(), "wb") as dest:
        dest.write(pdb_data.encode())


def _process_add_request(request):
    proj = current_project(request)
    method = request.POST["method"]

    if method == "upload_file":
        _store_uploaded_pdb(proj, request.FILES["pdb"])
        return

    assert method == "fetch_online"
    _fetch_from_rcsb(proj, request.POST["pdb_id"])


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
