from typing import Set
from fragview.models import User, Library, UserProject, PendingProject
from django.test import TestCase
from tests.utils import ProjectTestCase
from tests.project_setup import Project


class TestUserProject(TestCase):
    ERR_MSG = "dummy error msg"

    def setUp(self):
        self.project = UserProject.create_new("MID2", "20201122")
        self.assertTrue(self.project.is_pending())

    def test_set_ready(self):
        """
        test setting pending project into 'ready' state
        """
        self.project.set_ready()
        self.assertFalse(self.project.is_pending())

    def test_set_failed(self):
        """
        test setting error on a pending project
        """

        # set error on the project
        self.project.set_failed(self.ERR_MSG)

        # should still be pending
        self.assertTrue(self.project.is_pending())

        # check that error message was set in the database
        pend_proj = PendingProject.objects.get(project=self.project.id)
        self.assertIsNotNone(pend_proj)
        self.assertEqual(pend_proj.error_message, self.ERR_MSG)


class TestLibrary(ProjectTestCase):
    PROJECTS = [
        Project(
            protein="Nsp5",
            proposal="20180453",
            datasets=[],
            crystals=[],
            results=[],
        ),
        Project(
            protein="MID2",
            proposal="20180453",
            datasets=[],
            crystals=[],
            results=[],
        ),
    ]

    def setUp(self):
        super().setUp()

        lib = Library(name="public")
        lib.save()

        lib = Library(name="private", project_id=self.project.id)
        lib.save()

    def _assert_libs(self, libs, expected_names: Set[str]):
        got_names = {lib.name for lib in libs}
        self.assertSetEqual(got_names, expected_names)

    def test_get_all(self):
        # for first project, we should get all libraries
        libs = Library.get_all(self.project)
        self._assert_libs(libs, {"public", "private"})

        # for second project, we should only get 'public' library
        libs = Library.get_all(self.projects[1])
        self._assert_libs(libs, {"public"})

    def test_get_by_name(self):
        #
        # for first project we should be able to get both libs
        #
        lib = Library.get_by_name(self.project, "public")
        self.assertEqual(lib.name, "public")

        lib = Library.get_by_name(self.project, "private")
        self.assertEqual(lib.name, "private")

        #
        # for second project, we should only be able to get
        # the 'public' library
        #
        lib = Library.get_by_name(self.projects[1], "public")
        self.assertEqual(lib.name, "public")

        with self.assertRaises(Library.DoesNotExist):
            Library.get_by_name(self.projects[1], "private")


class TestUser(ProjectTestCase):
    USERNAME = "muser"

    def setUp(self):
        super().setUp()

        self.user_project = UserProject.get(self.projects[0].id)
        self.user = User(username=self.USERNAME)
        self.user.save()

    def test_set_current_project(self):
        """
        test User.set_current_project
        """
        # new user should not have a current_project set initially
        self.assertIsNone(self.user.current_project)

        # set the current project for the user
        self.user.set_current_project(self.user_project)

        #
        # reload user from the database and check it's current project
        #
        rl_usr = User.objects.get(username=self.USERNAME)
        self.assertEqual(rl_usr.current_project.id, self.user_project.id)

    def test_get_current_project_none(self):
        """
        no current project set for the user, and user does not have
        access to any other projects
        """
        self.assertIsNone(self.user.get_current_project(["20160101"]))

    def test_get_current_project_explicit(self):
        """
        get explicitly set current project
        :return:
        """
        self.user.set_current_project(self.user_project)

        proj = self.user.get_current_project(self.proposals)
        self.assertEqual(proj.id, self.user_project.id)

    def test_get_current_project_implicitly(self):
        """
        user have not set current_project, but have access to one of the projects
        """

        # make sure no explicit current project is set
        self.assertIsNone(self.user.current_project)

        proj = self.user.get_current_project(self.proposals)
        self.assertEqual(proj.id, self.user_project.id)
