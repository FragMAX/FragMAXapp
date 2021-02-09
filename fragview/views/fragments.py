import csv
import io
from django.shortcuts import render
from django.contrib import messages
from fragview.dsets import get_datasets
from fragview.projects import current_project
from fragview.models import Fragment
from fragview.projects import project_fragment_pdb, project_fragment_cif
from fragview.fileio import remove_file


def show(request):
    def _get_fragments():
        for ds in get_datasets(proj):
            if not ds.is_apo():
                yield ds.sample_name

    proj = current_project(request)

    lib = proj.library

    project_fragments = dict()
    missing_fragments = dict()
    for frag in _get_fragments():
        if lib.get_fragment(frag) is None:
            missing_fragments[frag] = frag
        else:
            project_fragments[frag] = lib.get_fragment(frag).smiles
    data_path = proj.data_path().replace("/data/visitors/", "/static/")

    if request.method == "GET":
        return render(
            request,
            "fragview/library_view.html",
            {
                "project_fragments": project_fragments,
                "missing_fragments": missing_fragments,
                "data_path": data_path,
            },
        )
    csv_file = request.FILES["fragments_file"]
    if not csv_file.name.endswith(".csv"):
        messages.error(request, "This is not a CSV file")

    data_frags = csv_file.read().decode("utf-8")
    io_string = io.StringIO(data_frags)
    updated_frags = set()
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
                    updated_frags.add(fragID)
            else:
                print("New fragment " + fragID)
                new_frag_entry = Fragment(library_id=id_db, name=fragID, smiles=smiles)
                new_frag_entry.save()
                updated_frags.add(fragID)

        else:
            messages.error(
                request,
                "The library CSV should be: fragmentID, SMILES " + "".join(column),
            )

    for fragID in updated_frags:
        # remove, if any, old PDB/CIF fragment files
        remove_file(project_fragment_pdb(proj, fragID))
        remove_file(project_fragment_cif(proj, fragID))

    return render(
        request,
        "fragview/library_view.html",
        {
            "project_fragments": project_fragments,
            "missing_fragments": missing_fragments,
            "data_path": data_path,
        },
    )
