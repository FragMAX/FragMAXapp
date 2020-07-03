import unittest
from unittest.mock import Mock
from os import path
from tempfile import TemporaryDirectory
from fragview import encryption
from fragview.fileio import open_proj_file, read_proj_file, read_text_lines


FILE_NAME = "some.log"
DUMMY_DATA = b"""
Preheat oven to 425 degrees F. Whisk pumpkin, sweetened condensed milk,
eggs, spices and salt in medium bowl until smooth. Pour into crust.
Bake 15 minutes."""


def _read_file(file_path):
    with open(file_path, "rb") as f:
        return f.read()


def _write_file(file_path):
    with open(file_path, "wb") as f:
        f.write(DUMMY_DATA)


def _expected_lines():
    return DUMMY_DATA.decode().split("\n")


class _IOTester(unittest.TestCase):
    def setUp(self):
        self.proj = Mock()
        self.proj.encrypted = self.ENCRYPTED

        if self.ENCRYPTED:
            self.key = encryption.generate_key()
            self.proj.encryptionkey.key = self.key

        self.temp_dir = TemporaryDirectory()

        self.file_path = path.join(self.temp_dir.name, FILE_NAME)

    def tearDown(self):
        self.temp_dir.cleanup()


class EncryptedTest(_IOTester):
    """
    test file I/O utility functions on a encrypted project
    """
    ENCRYPTED = True

    def test_open_proj_file(self):
        """
        test open_proj_file() on encrypted project
        """
        with open_proj_file(self.proj, self.file_path) as f:
            f.write(DUMMY_DATA)

        # check that it was correctly written, encrypted
        data = encryption.decrypt(self.key, self.file_path)
        self.assertEqual(data, DUMMY_DATA)

    def test_read_proj_file(self):
        """
        test open_proj_file() on encrypted project
        """
        # write test file
        with encryption.EncryptedFile(self.key, self.file_path) as f:
            f.write(DUMMY_DATA)

        # check that encrypted file is decrypted correctly
        data = read_proj_file(self.proj, self.file_path)
        self.assertEqual(data, DUMMY_DATA)

    def test_read_text_lines(self):
        """
        test read_text_lines() on encrypted project
        """
        # write test file
        with encryption.EncryptedFile(self.key, self.file_path) as f:
            f.write(DUMMY_DATA)

        # read file's lines
        lines = read_text_lines(self.proj, self.file_path)

        # check that we get expected lines
        self.assertListEqual(list(lines), _expected_lines())


class PlaintextTest(_IOTester):
    """
    test file I/O utility functions on a un-encrypted (plaintext) project
    """
    ENCRYPTED = False

    def test_open_proj_file(self):
        """
        test open_proj_file() on un-encrypted project
        """
        with open_proj_file(self.proj, self.file_path) as f:
            f.write(DUMMY_DATA)

        # check that it was correctly written, unencrypted
        self.assertEqual(_read_file(self.file_path), DUMMY_DATA)

    def test_read_proj_file(self):
        """
        test read_proj_file() on un-encrypted project
        """
        # write test file
        _write_file(self.file_path)

        # check that plaintext file is read correctly
        data = read_proj_file(self.proj, self.file_path)
        self.assertEqual(data, DUMMY_DATA)

    def test_read_text_lines(self):
        """
        test read_text_lines() on un-encrypted project
        """
        # write test file
        _write_file(self.file_path)

        # read file's lines
        lines = read_text_lines(self.proj, self.file_path)

        # check that we get expected lines
        self.assertListEqual(list(lines), _expected_lines())
