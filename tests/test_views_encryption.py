from django import test
import base64
from fragview.models import Project, Library, EncryptionKey
from tests.utils import ViewTesterMixin

DUMMY_KEY = b"DeadBeefCafeBabe"


class TestDownloadKey(test.TestCase, ViewTesterMixin):
    """
    test download_key() view
    """
    def setUp(self):
        self.setup_client()

    def setup_proj(self, encrypted=True, key=None):
        lib = Library(name="AVT")
        lib.save()

        proj = Project(protein="PRT", library=lib,
                       proposal=self.PROP1, shift="20190808",
                       encrypted=encrypted)
        proj.save()

        if key is not None:
            EncryptionKey(project=proj, key=key).save()

    def test_unencrypted_project(self):
        """
        test downloading key for unencrypted project
        """
        self.setup_proj(encrypted=False)
        resp = self.client.get("/encryption/key/")

        # check that we got error response
        self.assertEqual(400, resp.status_code)
        self.assertEquals(b"encrypted mode disabled for current project", resp.content)

    def test_key_unknown(self):
        """
        test downloading key for an encrypted project with no key uploaded
        """
        self.setup_proj()
        resp = self.client.get("/encryption/key/")

        # check that we got error response
        self.assertEqual(400, resp.status_code)
        self.assertEquals(b"no key uploaded", resp.content)

    def test_key_exists(self):
        """
        test downloading key when project is encrypted and have key uploaded
        """
        self.setup_proj(key=DUMMY_KEY)
        resp = self.client.get("/encryption/key/")

        #
        # check that we generate a 'file download' response
        #
        self.assertEqual(200, resp.status_code)

        self.assertEquals(resp["content-type"], "application/force-download")
        self.assertEquals(resp["Content-Disposition"], 'attachment; filename="PRTAVT_key"')

        # we should get our key, base64 encoded
        self.assertEquals(base64.b64decode(resp.content), DUMMY_KEY)
