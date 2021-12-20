import base64
from unittest.mock import Mock
from django.shortcuts import reverse
from fragview.projects import get_project
from projects.database import db_session
from tests.utils import ProjectTestCase, ViewTesterMixin
from tests.project_setup import Project


DUMMY_KEY = b"DeadBeefCafeBabe"
BASE64_KEY = "RGVhZEJlZWZDYWZlQmFiZQ=="
ENCRYPTION_DISABLED = "encrypted mode disabled for current project"


def _upload_file(name, data):
    ufile = Mock()
    ufile.name = name
    ufile.read.return_value = data

    return ufile


class _EncryptionKeyTestCase(ProjectTestCase, ViewTesterMixin):
    PROJECTS = [
        # first project is encrypted
        Project(
            protein="Nsp5",
            proposal="20180453",
            encrypted=True,
            datasets=[],
            crystals=[],
            results=[],
        ),
        # second project is in plain text
        Project(
            protein="Nsp5",
            proposal="20180453",
            encrypted=False,
            datasets=[],
            crystals=[],
            results=[],
        ),
    ]

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)


class TestDownloadKey(_EncryptionKeyTestCase):
    """
    test download_key() view
    """

    @db_session
    def test_unencrypted_project(self):
        """
        test downloading key for unencrypted project
        """
        # switch 'current project' to the second, unencrypted one
        self.set_current_project(self.projects[1].id)

        # try to get encryption key
        resp = self.client.get("/encryption/key/")

        # check that we got error response
        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_key_unknown(self):
        """
        test downloading key for an encrypted project with no key uploaded
        """
        # drop the key
        self.forget_key()

        with db_session:
            resp = self.client.get("/encryption/key/")

        # check that we got error response
        self.assert_response(resp, 400, "no key uploaded")

    @db_session
    def test_key_exists(self):
        """
        test downloading key when project is encrypted and have key uploaded
        """
        resp = self.client.get("/encryption/key/")

        #
        # check that we generate a 'file download' response
        #
        self.assertEqual(200, resp.status_code)

        self.assertEquals(resp["content-type"], "application/force-download")
        self.assertEquals(
            resp["Content-Disposition"], 'attachment; filename="Nsp5_20180453_key"'
        )

        # we should get our key, base64 encoded
        self.assertEquals(base64.b64decode(resp.content), self.project.encryption_key)


class TestUploadKey(_EncryptionKeyTestCase):
    """
    test upload_key() view
    """

    URL = "/encryption/key/upload/"

    def setUp(self):
        super().setUp()
        self.upload_file = _upload_file("FooKey", BASE64_KEY)

    @db_session
    def test_not_encrypted(self):
        """
        test the case where upload key for project with encryption disabled
        """
        # switch 'current project' to the second, unencrypted one
        self.set_current_project(self.projects[1].id)

        resp = self.client.post(
            self.URL, dict(method="upload_file", key=self.upload_file)
        )
        # check that we got error message
        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    @db_session
    def test_no_key_provided(self):
        """
        test making request without providing encryption key file
        """
        self.forget_key()

        resp = self.client.post(self.URL)
        # check that we got error message
        self.assert_bad_request(resp, "no encryption key file provided")

    def test_key_uploaded(self):
        """
        test happy path for uploading encryption key
        """
        with db_session:
            resp = self.client.post(
                self.URL, dict(method="upload_file", key=self.upload_file)
            )

        with db_session:
            # check that key was saved to database,
            # we need to reload project model in a new session
            project = get_project(self.projects_db_dir, self.project.id)
            self.assertEquals(project.encryption_key, DUMMY_KEY)

            # check that we were redirected to correct view
            self.assertRedirects(resp, reverse("encryption"))


class TestForgetKey(_EncryptionKeyTestCase):
    """
    test forget_key() view
    """

    @db_session
    def test_not_encrypted(self):
        """
        test forgetting key for un-encrypted project
        """
        # switch 'current project' to the second, unencrypted one
        self.set_current_project(self.projects[1].id)

        resp = self.client.get("/encryption/key/forget/")

        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_success(self):
        with db_session:
            resp = self.client.get("/encryption/key/forget/")

        with db_session:
            # check that key was removed from the database,
            # we need to reload project model in a new session
            project = get_project(self.projects_db_dir, self.project.id)
            self.assertFalse(project.has_encryption_key())

            # check that we were redirected to correct view
            self.assertRedirects(resp, reverse("encryption"))


class TestShow(_EncryptionKeyTestCase):
    """
    test show() view
    """

    URL = reverse("encryption")

    @db_session
    def test_not_encrypted(self):
        """
        test the case where we load view for project with encryption disabled
        """
        # switch 'current project' to the second, unencrypted one
        self.set_current_project(self.projects[1].id)

        resp = self.client.get(self.URL)
        # check that we got error message
        self.assert_bad_request(resp, ENCRYPTION_DISABLED)

    def test_no_key(self):
        """
        test case when project don't have a key
        """
        self.forget_key()

        with db_session:
            resp = self.client.get(self.URL)

        self.assertEquals(resp.status_code, 200)
        self.assert_contains_template(resp, "upload_enc_key.html")

    @db_session
    def test_has_key(self):
        """
        test case when project have a key
        """
        resp = self.client.get(self.URL)

        self.assertEquals(resp.status_code, 200)
        self.assert_contains_template(resp, "encryption.html")
