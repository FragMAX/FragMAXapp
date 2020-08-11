from os import path
import unittest
from fragview import auth
from django import test
from fragview.models import Project, Library


def identity(func):
    return func


class WorkerTaskTester(unittest.TestCase):
    def assert_locking(self, red_lock_mock, lock_id):
        """
        make assertions that a RedLock with specified id was acquired and released
        """
        red_lock_mock.assert_called_once_with(lock_id)

        lock = red_lock_mock.return_value
        lock.acquire.assert_called_once_with()
        lock.release.assert_called_once_with()


class ViewTesterMixin:
    """
    Utility mixin, that provides method to setup authenticated HTTP client
    """
    PROP1 = "20180201"
    PROP2 = "20170223"

    def setup_client(self):
        """
        setup test HTTP client which is logged in with a user 'dummy'
        that have access to PROP1 and PROP2 proposals
        """
        self.user = auth.ISPyBBackend()._get_user_obj("dummy")
        self.client = test.Client()
        self.client.force_login(user=self.user)

        session = self.client.session
        session["proposals"] = [self.PROP1, self.PROP2]
        session.save()

    def setup_project(self, encrypted=False):
        self.lib = Library(name="JBS")
        self.lib.save()

        self.proj = Project(protein="PRT", library=self.lib, proposal=self.PROP1,
                            shift="20190808", encrypted=encrypted)
        self.proj.save()

    def assert_contains_template(self, response, template_name):
        """
        assert that the response rendering involved using the specified template
        """
        templ_names = [t.name for t in response.templates]
        self.assertIn(template_name, templ_names)

    def assert_bad_request(self, response, error_msg):
        self.assertEquals(response.status_code, 400)
        self.assertRegex(response.content.decode(), error_msg)


def data_file_path(file_name):
    """
    return absolute path specified file in tests 'data' directory
    """
    return path.join(path.dirname(__file__), "data", file_name)


def xs_data_path(num):
    return data_file_path(f"xs_data{num}.xml")
