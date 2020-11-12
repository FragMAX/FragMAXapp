from pathlib import Path
from django.shortcuts import HttpResponse

COMMIT_FILE = "commit"


def _commit_file():
    root_dir = Path(__file__).parent.parent.parent

    return Path(root_dir, COMMIT_FILE)


def _commit_desc():
    commit_file = _commit_file()
    if not commit_file.is_file():
        return "unspecified"

    return commit_file.read_text()


def show(_):
    return HttpResponse(_commit_desc(), content_type="text/plain")
