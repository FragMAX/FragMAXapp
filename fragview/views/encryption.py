import base64
from django import urls
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from fragview.projects import current_project, Project


ENCRYPTION_DISABLED_MSG = "encrypted mode disabled for current project"


class CryptoKeyError(Exception):
    def error_message(self):
        return self.args[0]


def _get_key(project: Project) -> str:
    """
    get project's encryption key in BASE64 format

    raises CryptoKeyError if encryption key is not uploaded
    or of project is not encrypted
    """
    if not project.encrypted:
        raise CryptoKeyError(ENCRYPTION_DISABLED_MSG)

    if not project.has_encryption_key():
        raise CryptoKeyError("no key uploaded")

    return base64.b64encode(project.encryption_key).decode()


def _redirect_to_encryption():
    return redirect(urls.reverse("encryption"))


def download_key(request):
    project = current_project(request)

    try:
        key = _get_key(project)
    except CryptoKeyError as e:
        return HttpResponseBadRequest(e.error_message())

    key_filename = f"{project.protein}_{project.proposal}_key"

    response = HttpResponse(key, content_type="application/force-download")
    response["Content-Disposition"] = f'attachment; filename="{key_filename}"'

    return response


def upload_key(request):
    project = current_project(request)
    if not project.encrypted:
        return HttpResponseBadRequest(ENCRYPTION_DISABLED_MSG)

    key_file = request.FILES.get("key")
    if key_file is None:
        return HttpResponseBadRequest("no encryption key file provided")

    # TODO give BadRequest response if
    #  1) invalid base64 content
    #  2) decoded key != 16 bytes

    key = base64.b64decode(key_file.file.read())
    project.encryption_key = key

    return _redirect_to_encryption()


def forget_key(request):
    project = current_project(request)
    if not project.encrypted:
        return HttpResponseBadRequest(ENCRYPTION_DISABLED_MSG)

    project.forget_key()

    return _redirect_to_encryption()


def show(request):
    proj = current_project(request)

    if not proj.encrypted:
        return HttpResponseBadRequest(ENCRYPTION_DISABLED_MSG)

    if proj.has_encryption_key():
        # encryption key currently uploaded
        template = "encryption.html"
    else:
        # key needs to be uploaded
        template = "upload_enc_key.html"

    return render(request, template)
