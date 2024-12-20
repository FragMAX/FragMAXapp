import os
import stat
import unittest
from unittest.mock import Mock, patch
from os import path
from tempfile import TemporaryDirectory
from tests.utils import TempDirMixin
from fragview.fileio import (
    open_proj_file,
    read_proj_file,
    read_text_lines,
    write_script,
)

FILE_NAME = "some.file"
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


class TestIO(unittest.TestCase):
    """
    test file I/O utility functions
    """

    def setUp(self):
        self.proj = Mock()
        self.proj.data_path.return_value = "/"

        self.temp_dir = TemporaryDirectory()

        self.file_path = path.join(self.temp_dir.name, FILE_NAME)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_open_proj_file(self):
        """
        test open_proj_file()
        """
        with open_proj_file(self.proj, self.file_path) as f:
            f.write(DUMMY_DATA)

        # check that it was correctly written
        self.assertEqual(_read_file(self.file_path), DUMMY_DATA)

    def test_read_proj_file(self):
        """
        test read_proj_file()
        """
        # write test file
        _write_file(self.file_path)

        # check that the file is read correctly
        data = read_proj_file(self.file_path)
        self.assertEqual(data, DUMMY_DATA)

    def test_read_text_lines(self):
        """
        test read_text_lines()
        """
        # write test file
        _write_file(self.file_path)

        # read file's lines
        lines = read_text_lines(self.proj, self.file_path)

        # check that we get expected lines
        self.assertListEqual(list(lines), _expected_lines())


@patch("builtins.print")
class TestWriteScript(unittest.TestCase, TempDirMixin):
    """
    test the write_script() function
    """

    SCRIPT_BODY = "some-dummy-script"
    SCRIPT_LONG_BODY = "some-dummy-long-body-script"

    def setUp(self):
        self.setup_temp_dir()
        self.script_path = path.join(self.temp_dir, "dummy.sh")

    def tearDown(self):
        self.tear_down_temp_dir()

    def test_func(self, print_mock):
        write_script(self.script_path, self.SCRIPT_BODY)

        # check created files contents
        contents = open(self.script_path, "r").read()
        self.assertEqual(contents, self.SCRIPT_BODY)

        # check access mode
        mode = os.stat(self.script_path).st_mode
        self.assertEqual(
            mode,
            # regular file
            stat.S_IFREG |
            # readable, writeable, executable by the owner
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
            # readable and writeable by the group
            stat.S_IRGRP | stat.S_IWGRP,
        )

        # check the 'log' message
        print_mock.assert_called_once_with(f"writing script file {self.script_path}")

    def test_truncate(self, _):
        """
        check that when overwriting an existing script, it is
        correctly truncated
        """

        # first write a 'long' script
        write_script(self.script_path, self.SCRIPT_LONG_BODY)
        # overwrite it with shorter script
        write_script(self.script_path, self.SCRIPT_BODY)

        # the resulting script should only contain the 'short' contents
        contents = open(self.script_path, "r").read()
        self.assertEqual(contents, self.SCRIPT_BODY)
