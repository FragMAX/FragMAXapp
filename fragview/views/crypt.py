from pathlib import Path
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from fragview.models import AccessToken
from fragview.fileio import is_relative_to
from fragview.projects import Project, get_project
from fragview.encryption import decrypt, encrypt, CryptoErr


class InvalidRequest(Exception):
    def error_message(self):
        return self.args[0]


class Args:
    def __init__(self):
        self.operation = None
        self.filepath = None
        self.project = None
        self.file = None


def _validate_auth_token(auth_token) -> Project:
    try:
        tok = AccessToken.get_from_base64(auth_token)
    except AccessToken.ParseError:
        raise InvalidRequest("error parsing auth token")
    except AccessToken.DoesNotExist:
        raise InvalidRequest("invalid auth token")

    return get_project(settings.PROJECTS_DB_DIR, tok.project_id)


def _validate_file_path(proj: Project, filepath: str) -> Path:
    """
    we only allow access to files inside project's FragMAX directory
    """
    if filepath is None:
        raise InvalidRequest("no 'filepath' specified")

    fpath = Path(filepath).resolve()

    if not is_relative_to(fpath, proj.project_dir):
        raise InvalidRequest(f"invalid file path '{filepath}'")

    return fpath


def _get_request_args(request):
    if request.method != "POST":
        raise InvalidRequest("only POST requests supported")

    post = request.POST

    args = Args()

    #
    # validate 'auth' token
    #
    auth_token = post.get("auth")
    if auth_token is None:
        raise InvalidRequest("no 'auth' token provided")
    args.project = _validate_auth_token(auth_token)

    #
    # validate 'operation' argument
    #
    args.operation = post.get("operation")
    if args.operation is None:
        raise InvalidRequest("no 'operation' specified")

    if args.operation not in ["read", "write"]:
        raise InvalidRequest(f"unexpected operation '{args.operation}'")

    #
    # validate 'filepath' argument
    #
    args.filepath = _validate_file_path(args.project, post.get("filepath"))

    #
    # if 'write' operation, check that an uploaded file is provided
    #
    if args.operation == "write":
        args.file = request.FILES.get("file")
        if args.file is None:
            raise InvalidRequest("no file data provided")

    return args


def _get_key(project: Project):
    if project.encryption_key is None:
        raise InvalidRequest("project's encryption key is missing")

    return project.encryption_key


def _read_file(key, filepath: Path):
    if not filepath.is_file():
        raise InvalidRequest(f"{filepath}: no such file")

    try:
        plaintext = decrypt(key, filepath)
    except CryptoErr as e:
        print(f"error decrypting {filepath}: {e.error_message()}")
        raise InvalidRequest("cryptology error")

    return HttpResponse(plaintext,
                        content_type="application/octet-stream")


def _write_file(key: bytes, filepath: Path, file):
    filepath.parent.mkdir(exist_ok=True)
    encrypt(key, file, filepath)

    return HttpResponse("vtalibov4president")


@csrf_exempt
def index(request):
    try:
        args = _get_request_args(request)
        key = _get_key(args.project)

        if args.operation == "read":
            return _read_file(key, args.filepath)
        elif args.operation == "write":
            return _write_file(key, args.filepath, args.file)
    except InvalidRequest as e:
        return HttpResponseBadRequest(e.error_message())

    assert False  # this should not happen
