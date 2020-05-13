from django import urls
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from fragview.projects import current_project
from fragview.models import Project, EncryptionKey


ENCRYPTION_DISABLED_MSG = "encrypted mode disabled for current project"


class CryptoKeyError(Exception):
    def error_message(self):
        return self.args[0]


def _get_key(request):
    proj = current_project(request)

    if not proj.encrypted:
        raise CryptoKeyError(ENCRYPTION_DISABLED_MSG)

    try:
        return proj.encryptionkey
    except Project.encryptionkey.RelatedObjectDoesNotExist:
        raise CryptoKeyError("no key uploaded")


def _redirect_to_encryption():
    return redirect(urls.reverse("encryption"))


def download_key(request):
    try:
        key = _get_key(request)
    except CryptoKeyError as e:
        return HttpResponseBadRequest(e.error_message())

    b64_key = key.as_base64()
    key_filename = f"{key.project.protein}{key.project.library.name}_key"

    response = HttpResponse(b64_key, content_type="application/force-download")
    response["Content-Disposition"] = f"attachment; filename=\"{key_filename}\""

    return response


def upload_key(request):
    proj = current_project(request)
    if not proj.encrypted:
        return HttpResponseBadRequest(ENCRYPTION_DISABLED_MSG)

    key_file = request.FILES.get("key")
    if key_file is None:
        return HttpResponseBadRequest("no encryption key file provided")

    # TODO what happens if the key is already uploaded?

    # TODO give BadRequest response if
    #  1) invalid base64 content
    #  2) decoded key != 16 bytes

    key = EncryptionKey.from_base64(proj, key_file.file.read())
    key.save()

    return _redirect_to_encryption()


def forget_key(request):
    try:
        key = _get_key(request)
    except CryptoKeyError as e:
        return HttpResponseBadRequest(e.error_message())

    key.delete()

    return _redirect_to_encryption()


def show(request):
    proj = current_project(request)

    if not proj.encrypted:
        return HttpResponseBadRequest(ENCRYPTION_DISABLED_MSG)

    if proj.has_encryption_key():
        # encryption key currently uploaded
        template = "fragview/encryption.html"
    else:
        # key needs to be uploaded
        template = "fragview/upload_enc_key.html"

    return render(request, template)
