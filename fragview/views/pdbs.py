from typing import Optional
import re
import pypdb
from gemmi import read_pdb_string
from django import urls
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from fragview.fileio import open_proj_file
from fragview.views.wrap import PDBInfo
from fragview.projects import current_project, Project
from fragview.space_groups import space_group_to_db_format
from fragview.views.utils import download_http_response, get_pdb_by_id


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


def _get_pdbs(project: Project):
    for pdb in project.get_pdbs():
        yield PDBInfo(pdb)


def list(request):
    """
    protein models list page, aka 'manage pdbs' page
    """
    project = current_project(request)
    return render(request, "pdbs.html", {"pdbs": _get_pdbs(project)})


def _is_valid_pdb_filename(filename):
    m = re.match(VALID_PDB_FNAME_REGEXP, filename, re.IGNORECASE)
    return m is not None


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


def _save_pdb(project: Project, pdb_id: Optional[str], filename: str, pdb_data: bytes):
    if not _is_valid_pdb_filename(filename):
        raise PDBAddError("Invalid PDB filename, only letters and number are allowed.")

    if project.get_pdb(filename=filename) is not None:
        raise PDBAddError(f"Model file '{filename}' already exists in the project.")

    #
    # parse the PDB file
    #
    pdb = read_pdb_string(str(pdb_data.decode()))

    space_group = pdb.find_spacegroup()

    if space_group is None:
        raise PDBAddError(f"Failed to read space group from '{filename}' file.\n")

    #
    # add the PDB to the database
    #
    args = dict(
        filename=filename,
        space_group=space_group_to_db_format(space_group),
        unit_cell_a=pdb.cell.a,
        unit_cell_b=pdb.cell.b,
        unit_cell_c=pdb.cell.c,
        unit_cell_alpha=pdb.cell.alpha,
        unit_cell_beta=pdb.cell.beta,
        unit_cell_gamma=pdb.cell.gamma,
    )
    if pdb_id is not None:
        args["pdb_id"] = pdb_id

    project.db.PDB(**args)

    #
    # store the PDB file itself in project's models folder
    #
    with open_proj_file(project, project.get_pdb_path(filename)) as dest:
        dest.write(pdb_data)

    return


#
# This function is wrapped into a DB session, with an implicit transaction.
#
# If we fail to write the PDB file to disk, the new
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
