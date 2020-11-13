from django.http import Http404, HttpResponse
from fragview.projects import (
    current_project,
    project_fragments_dir,
    project_fragment_pdb,
)
from fragview import smiles, fileio
from worker.fragments import smiles_to_pdb


def _get_fragment_model(proj, fragment):
    frag = proj.library.get_fragment(fragment)
    if frag is None:
        raise Http404(f"no '{fragment}' fragment in {proj.library.name} library")

    return frag


def svg(request, fragment):
    proj = current_project(request)

    if proj.protein in fragment:
        fragment = fragment.split("-")[-1].split("_")[0]

    frag = _get_fragment_model(proj, fragment)

    return HttpResponse(smiles.to_svg(frag.smiles), content_type="image/svg+xml")


def pdb(request, fragment):
    proj = current_project(request)

    frag = _get_fragment_model(proj, fragment)
    smiles_to_pdb.delay(frag.smiles, project_fragments_dir(proj), frag.name).wait()
    pdb_data = fileio.read_proj_file(proj, project_fragment_pdb(proj, frag.name))

    return HttpResponse(pdb_data, content_type="application/octet-stream")
