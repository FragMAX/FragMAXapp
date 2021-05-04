from django.http import HttpResponse
from fragview import smiles
from fragview.views.utils import get_fragment_by_id


def svg(_, fragment_id: str):
    fragment = get_fragment_by_id(fragment_id)
    return HttpResponse(smiles.to_svg(fragment.smiles), content_type="image/svg+xml")
