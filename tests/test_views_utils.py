import os
import stat
import unittest
import tempfile
import shutil
from os import path
from unittest.mock import patch

from fragview.views import utils


SCRIPT_BODY = "some-dummy-script"


class TestWriteScript(unittest.TestCase):
    """
    test the write_script() function
    """
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("builtins.print")
    def test_func(self, print_mock):
        script_path = path.join(self.temp_dir, "dummy.sh")

        utils.write_script(script_path, SCRIPT_BODY)

        # check created files contents
        contents = open(script_path, "r").read()
        self.assertEqual(contents, SCRIPT_BODY)

        # check access mode
        mode = os.stat(script_path).st_mode
        self.assertEqual(mode,
                         # regular file
                         stat.S_IFREG |
                         # readable, writeable, executable by the owner
                         stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                         # readable and writeable by the group
                         stat.S_IRGRP | stat.S_IWGRP)

        # check the 'log' message
        print_mock.assert_called_once_with(f"writing script file {script_path}")
