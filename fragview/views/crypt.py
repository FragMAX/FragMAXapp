import os
from os import path
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from fragview.models import AccessToken
from fragview.encryption import decrypt, encrypt, CryptoErr
from fragview.projects import project_fragmax_dir


class InvalidRequest(Exception):
    def error_message(self):
        return self.args[0]


class Args:
    def __init__(self):
        self.operation = None
        self.filepath = None
        self.project = None
        self.file = None


def _validate_auth_token(auth_token):
    try:
        tok = AccessToken.get_from_base64(auth_token)
    except AccessToken.ParseError:
        raise InvalidRequest("error parsing auth token")
    except AccessToken.DoesNotExist:
        raise InvalidRequest("invalid auth token")

    return tok.project


def _validate_file_path(proj, filepath):
    """
    we only allow access to files inside project's FragMAX directory
    """
    abs_path = path.abspath(filepath)
    fragmax_dir = project_fragmax_dir(proj)

    if not abs_path.startswith(fragmax_dir):
        raise InvalidRequest(f"invalid file path '{filepath}'")


def _get_request_args(request):
    if request.method != "POST":
        raise InvalidRequest("only POST request supported")

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
    args.filepath = post.get("filepath")
    if args.filepath is None:
        raise InvalidRequest("no 'filepath' specified")
    _validate_file_path(args.project, args.filepath)

    #
    # if 'write' operation, check that an uploaded file is provided
    #
    if args.operation == "write":
        args.file = request.FILES.get("file")
        if args.file is None:
            raise InvalidRequest("no file data provided")

    return args


def _get_key(proj):
    encryption_key = proj.encryption_key
    if encryption_key is None:
        raise InvalidRequest("project's encryption key is missing")

    return proj.encryptionkey.key


def _read_file(key, filepath):
    if not path.isfile(filepath):
        raise InvalidRequest(f"{filepath}: no such file")

    try:
        plaintext = decrypt(key, filepath)
    except CryptoErr as e:
        print(f"error decrypting {filepath}: {e.error_message()}")
        raise InvalidRequest("cryptology error")

    return HttpResponse(plaintext,
                        content_type="application/octet-stream")


def _write_file(key, filepath, file):
    os.makedirs(path.dirname(filepath), exist_ok=True)
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
