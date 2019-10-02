from os import path
from django.conf import settings


def proposal_dir(proposal_number):
    return path.join(settings.PROPOSALS_DIR, proposal_number)


def shift_dir(proposal_number, shift):
    return path.join(proposal_dir(proposal_number), shift)


def protein_dir(proposal_number, shift, protein):
    return path.join(shift_dir(proposal_number, shift), "raw", protein)
