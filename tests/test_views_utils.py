import os
import stat
import unittest
import tempfile
import shutil
from os import path
from unittest.mock import patch

from fragview.views import utils


SCRIPT_BODY = "some-dummy-script"
SCRIPT_LONG_BODY = "some-dummy-long-body-script"


@patch("builtins.print")
class TestWriteScript(unittest.TestCase):
    """
    test the write_script() function
    """
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.script_path = path.join(self.temp_dir, "dummy.sh")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_func(self, print_mock):
        utils.write_script(self.script_path, SCRIPT_BODY)

        # check created files contents
        contents = open(self.script_path, "r").read()
        self.assertEqual(contents, SCRIPT_BODY)

        # check access mode
        mode = os.stat(self.script_path).st_mode
        self.assertEqual(mode,
                         # regular file
                         stat.S_IFREG |
                         # readable, writeable, executable by the owner
                         stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                         # readable and writeable by the group
                         stat.S_IRGRP | stat.S_IWGRP)

        # check the 'log' message
        print_mock.assert_called_once_with(f"writing script file {self.script_path}")

    def test_truncate(self, _):
        """
        check that when overwriting an existing script, it is
        correctly truncated
        """

        # first write a 'long' script
        utils.write_script(self.script_path, SCRIPT_LONG_BODY)
        # overwrite it with shorter script
        utils.write_script(self.script_path, SCRIPT_BODY)

        # the resulting script should only contain the 'short' contents
        contents = open(self.script_path, "r").read()
        self.assertEqual(contents, SCRIPT_BODY)
