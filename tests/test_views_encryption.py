from django import test
import base64
from django.shortcuts import reverse
from fragview.models import Project, Library, EncryptionKey
from tests.utils import ViewTesterMixin

DUMMY_KEY = b"DeadBeefCafeBabe"


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
        self.assertEqual(400, resp.status_code)
        self.assertEquals(b"encrypted mode disabled for current project", resp.content)

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

        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.content, b"encrypted mode disabled for current project")

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
