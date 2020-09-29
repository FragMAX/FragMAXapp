import base64
from unittest.mock import Mock
from django import test
from django.shortcuts import reverse
from fragview.models import Project, Library, EncryptionKey
from tests.utils import ViewTesterMixin

DUMMY_KEY = b"DeadBeefCafeBabe"
BASE64_KEY = "RGVhZEJlZWZDYWZlQmFiZQ=="
ENCRYPTION_DISABLED = "encrypted mode disabled for current project"


def _setup_proj(encrypted=True, key=None):
    lib = Library(name="AVT")
    lib.save()

    proj = Project(
        protein="PRT",
        library=lib,
        proposal=ViewTesterMixin.PROP1,
        shift="20190808",
        encrypted=encrypted,
    )
    proj.save()

    if key is not None:
        EncryptionKey(project=proj, key=key).save()

    return proj


def _upload_file(name, data):
    ufile = Mock()
    ufile.name = name
    ufile.read.return_value = data

    return ufile


class TestDownloadKey(test.TestCase, ViewTesterMixin):
    """
    test download_key() view
    """

    def setUp(self):
        self.setup_client()

    def test_unencrypted_project(self):
        """
        test downloading key for unencrypted project
        """
        _setup_proj(encrypted=False)
        resp = self.client.get("/encryption/key/")

        # check that we got error response
        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_key_unknown(self):
        """
        test downloading key for an encrypted project with no key uploaded
        """
        _setup_proj()
        resp = self.client.get("/encryption/key/")

        # check that we got error response
        self.assertEqual(400, resp.status_code)
        self.assertEquals(b"no key uploaded", resp.content)

    def test_key_exists(self):
        """
        test downloading key when project is encrypted and have key uploaded
        """
        _setup_proj(key=DUMMY_KEY)
        resp = self.client.get("/encryption/key/")

        #
        # check that we generate a 'file download' response
        #
        self.assertEqual(200, resp.status_code)

        self.assertEquals(resp["content-type"], "application/force-download")
        self.assertEquals(
            resp["Content-Disposition"], 'attachment; filename="PRTAVT_key"'
        )

        # we should get our key, base64 encoded
        self.assertEquals(base64.b64decode(resp.content), DUMMY_KEY)


class TestUploadKey(test.TestCase, ViewTesterMixin):
    """
    test upload_key() view
    """

    URL = "/encryption/key/upload/"

    def setUp(self):
        self.setup_client()
        self.upload_file = _upload_file("FooKey", BASE64_KEY)

    def test_not_encrypted(self):
        """
        test the case where upload key for project with encryption disabled
        """
        _setup_proj(encrypted=False)

        resp = self.client.post(
            self.URL, dict(method="upload_file", key=self.upload_file)
        )
        # check that we got error message
        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_no_key_provided(self):
        """
        test making request without providing encryption key file
        """
        _setup_proj(encrypted=True)

        resp = self.client.post(self.URL)
        # check that we got error message
        self.assert_bad_request(resp, "no encryption key file provided")

    def test_key_uploaded(self):
        """
        test happy path for uploading encryption key
        """
        proj = _setup_proj(encrypted=True)

        resp = self.client.post(
            self.URL, dict(method="upload_file", key=self.upload_file)
        )

        # check that key was save to database
        enc_key = Project.get(proj.id).encryption_key
        self.assertEquals(enc_key.key, DUMMY_KEY)

        # check that we were redirected to correct view
        self.assertRedirects(resp, reverse("encryption"))


class TestForgetKey(test.TestCase, ViewTesterMixin):
    """
    test forget_key() view
    """

    def setUp(self):
        self.setup_client()

    def test_not_encrypted(self):
        """
        test forgetting key for un-encrypted project
        """
        _setup_proj(encrypted=False)

        resp = self.client.get("/encryption/key/forget/")

        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_no_key(self):
        """
        test forgetting key for project which current have no key uploaded
        """
        _setup_proj(encrypted=True, key=None)

        resp = self.client.get("/encryption/key/forget/")

        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.content, b"no key uploaded")

    def test_success(self):
        proj = _setup_proj(encrypted=True, key=DUMMY_KEY)

        resp = self.client.get("/encryption/key/forget/")

        # check that key was removed from the database
        self.assertFalse(Project.get(proj.id).has_encryption_key())
        # check that we were redirected to correct view
        self.assertRedirects(resp, reverse("encryption"))


class TestShow(test.TestCase, ViewTesterMixin):
    """
    test show() view
    """

    URL = reverse("encryption")

    def setUp(self):
        self.setup_client()

    def test_not_encrypted(self):
        """
        test the case where we load view for project with encryption disabled
        """
        _setup_proj(encrypted=False)

        resp = self.client.get(self.URL)
        # check that we got error message
        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_no_key(self):
        """
        test case when project don't have a key
        """
        _setup_proj(encrypted=True)

        resp = self.client.get(self.URL)

        self.assertEquals(resp.status_code, 200)
        self.assert_contains_template(resp, "fragview/upload_enc_key.html")

    def test_has_key(self):
        """
        test case when project have a key
        """
        _setup_proj(encrypted=True, key=DUMMY_KEY)

        resp = self.client.get(self.URL)

        self.assertEquals(resp.status_code, 200)
        self.assert_contains_template(resp, "fragview/encryption.html")
