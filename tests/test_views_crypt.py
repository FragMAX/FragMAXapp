import shutil
import tempfile
from unittest.mock import Mock, patch
from os import path
from django import test
from tests.utils import ViewTesterMixin
from fragview import tokens, encryption
from fragview.fileio import makedirs
from fragview.models import EncryptionKey
from fragview.encryption import decrypt, EncryptedFile
from fragview.projects import project_model_file


class _CryptViewTesterMixin(ViewTesterMixin):
    PDB_FILE = "dummy.pdb"
    PDB_DATA = b"Grunne-Tree-VAX"

    def setup_crypto(self):
        self.setup_client()
        self.setup_project(encrypted=True)

        self.token = tokens.get_valid_token(self.proj)

        # create a mocked 'file-like' object
        pdb_file = Mock()
        pdb_file.name = self.PDB_FILE
        pdb_file.read.return_value = self.PDB_DATA

        self.pdb_file = pdb_file

        key = EncryptionKey(key=encryption.generate_key(), project=self.proj)
        key.save()


class TestReadWrite(test.TestCase, _CryptViewTesterMixin):
    def setUp(self):
        self.setup_crypto()

        self.temp_dir = tempfile.mkdtemp()
        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = self.temp_dir
            self.pdb_path = project_model_file(self.proj, self.PDB_FILE)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_write(self):
        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = self.temp_dir

            resp = self.client.post(
                f"/crypt/",
                dict(
                    auth=self.token.as_base64(),
                    filepath=self.pdb_path,
                    file=self.pdb_file,
                    operation="write",
                ),
            )

        # we should get OK reply
        self.assertEqual(resp.status_code, 200)

        # check that file was written encrypted
        self.assertEqual(
            decrypt(self.proj.encryptionkey.key, self.pdb_path), self.PDB_DATA
        )

    def test_read(self):
        #
        # write encrypted file inside 'fragmax' directory
        #
        makedirs(path.dirname(self.pdb_path))
        with EncryptedFile(self.proj.encryptionkey.key, self.pdb_path) as f:
            f.write(self.PDB_DATA)

        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = self.temp_dir

            resp = self.client.post(
                f"/crypt/",
                dict(
                    auth=self.token.as_base64(),
                    filepath=self.pdb_path,
                    operation="read",
                ),
            )

        # we should get OK reply
        self.assertEqual(resp.status_code, 200)

        # check that we got expected plaintext content
        self.assertEqual(resp.content, self.PDB_DATA)

    def test_error_decrypting(self):
        makedirs(path.dirname(self.pdb_path))
        with open(self.pdb_path, "w") as f:
            f.write("invalid")

        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = self.temp_dir

            resp = self.client.post(
                f"/crypt/",
                dict(
                    auth=self.token.as_base64(),
                    filepath=self.pdb_path,
                    operation="read",
                ),
            )

            self.assert_bad_request(resp, "cryptology error")


class TestInvalidReqs(test.TestCase, _CryptViewTesterMixin):
    def setUp(self):
        self.setup_crypto()
        self.pdb_path = project_model_file(self.proj, self.PDB_FILE)

    def test_invalid_method(self):
        resp = self.client.get(f"/crypt/")

        self.assert_bad_request(resp, "only POST requests supported")

    def test_invalid_operation(self):
        resp = self.client.post(
            f"/crypt/",
            dict(
                auth=self.token.as_base64(),
                filepath=self.pdb_path,
                file=self.pdb_file,
                operation="invalid",
            ),
        )

        self.assert_bad_request(resp, "unexpected operation 'invalid'")

    def test_no_auth_token(self):
        resp = self.client.post(
            f"/crypt/", dict(filepath=self.pdb_path, operation="read")
        )

        self.assert_bad_request(resp, "no 'auth' token provided")

    def test_invalid_base64_auth_token(self):
        """
        request with unparsable (invalid base64 string) auth token
        """
        resp = self.client.post(
            f"/crypt/",
            dict(auth=b"this-is-not-ase64", filepath=self.pdb_path, operation="read"),
        )

        self.assert_bad_request(resp, "error parsing auth token")

    def test_file_not_found(self):
        # the file we are reading, should not exist
        self.assertFalse(path.isfile(self.pdb_path))

        resp = self.client.post(
            f"/crypt/",
            dict(auth=self.token.as_base64(), filepath=self.pdb_path, operation="read"),
        )

        self.assert_bad_request(resp, f"{self.pdb_path}: no such file")

    def test_no_encryption_key(self):
        # drop the key
        self.proj.encryptionkey.delete()

        resp = self.client.post(
            f"/crypt/",
            dict(auth=self.token.as_base64(), filepath=self.pdb_path, operation="read"),
        )

        self.assert_bad_request(resp, "project's encryption key is missing")

    def test_invalid_auth_token(self):
        resp = self.client.post(
            f"/crypt/",
            dict(auth="dGFnbmVsbA==", filepath=self.pdb_path, operation="read"),
        )

        self.assert_bad_request(resp, "invalid auth token")

    def test_no_operation(self):
        resp = self.client.post(
            f"/crypt/",
            dict(
                auth=self.token.as_base64(), filepath=self.pdb_path, file=self.pdb_file
            ),
        )

        self.assert_bad_request(resp, "no 'operation' specified")

    def test_no_filepath(self):
        resp = self.client.post(
            f"/crypt/",
            dict(auth=self.token.as_base64(), operation="read", file=self.pdb_file),
        )

        self.assert_bad_request(resp, "no 'filepath' specified")

    def test_invalid_filepath(self):
        resp = self.client.post(
            f"/crypt/",
            dict(
                auth=self.token.as_base64(),
                filepath="foo",
                file=self.pdb_file,
                operation="write",
            ),
        )

        self.assert_bad_request(resp, "invalid file path 'foo'")

    def test_no_file(self):
        resp = self.client.post(
            f"/crypt/",
            dict(
                auth=self.token.as_base64(), filepath=self.pdb_path, operation="write"
            ),
        )

        self.assert_bad_request(resp, "no file data provided")
