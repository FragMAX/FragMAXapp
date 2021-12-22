from fragview.models import User, UserProject, PendingProject
from django.test import TestCase
from tests.utils import ProjectTestCase


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
