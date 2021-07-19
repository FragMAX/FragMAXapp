import unittest
from django import test
from fragview.sites import SITE
from fragview.models import User, Project, Library


PROPOSAL = "20200912"
SHIFT = "87654321"
SHIFT_1 = "99999990"
SHIFT_2 = "88888880"


class TestUser(test.TestCase):
    USERNAME = "muser"
    OTHER_PROP = "20150000"

    def setUp(self):
        self.user = User(username=self.USERNAME)
        self.user.save()

        lib = Library(name="hepp")
        lib.save()

        self.project = Project(proposal=PROPOSAL, library=lib)
        self.project.save()

    def test_set_current_project(self):
        """
        test User.set_current_project
        """
        # new user should not have a current_project set initially
        self.assertIsNone(self.user.current_project)

        # set the current project for the user
        self.user.set_current_project(self.project)

        #
        # reload user from the database and check it's current project
        #
        rl_usr = User.objects.get(username=self.USERNAME)
        self.assertEqual(rl_usr.current_project.id, self.project.id)

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
        self.user.set_current_project(self.project)

        proj = self.user.get_current_project([PROPOSAL])
        self.assertEqual(proj.id, self.project.id)

    def test_get_current_project_implicitly(self):
        """
        user have not set current_project, but have access to one of the projects
        """

        # make sure no explicit current project is set
        self.assertIsNone(self.user.current_project)

        proj = self.user.get_current_project([PROPOSAL])
        self.assertEqual(proj.id, self.project.id)

    def test_get_current_project_no_access(self):
        """
        current project set to a project that user does not have access to
        """
        self.user.set_current_project(self.project)

        proj = self.user.get_current_project([self.OTHER_PROP])
        self.assertIsNone(proj)


class TestProject(test.TestCase):
    def test_icon_num(self):
        """
        test Project.icon_num() method
        """

        lib = Library(name="REW")
        lib.save()
        proj1 = Project(library=lib)
        proj1.save()
        proj2 = Project(library=lib)
        proj2.save()

        # check that project icon number's are in [0..PROJ_ICONS_NUMBER) range
        self.assertLessEqual(0, proj1.icon_num())
        self.assertGreater(Project.PROJ_ICONS_NUMBER, proj1.icon_num())

        self.assertLessEqual(0, proj2.icon_num())
        self.assertGreater(Project.PROJ_ICONS_NUMBER, proj2.icon_num())

        # check that two project, created right after each other,
        # have unique icon numbers
        self.assertNotEqual(proj2.icon_num(), proj1.icon_num())

    def test_data_path(self):
        """
        test Project.data_path() method
        """
        dpath = Project(proposal=PROPOSAL, shift=SHIFT).data_path()

        #
        # smoke test the data path
        #

        # should start with the configured 'proposals dir
        self.assertTrue(dpath.startswith(SITE.RAW_DATA_DIR))

        # proposal and main shift should be parts in the data path
        self.assertIn(PROPOSAL, dpath)
        self.assertIn(SHIFT, dpath)


class TestProjectShifts(unittest.TestCase):
    """
    test Project.shifts() method
    """

    def test_only_main_shift(self):
        proj = Project(shift=SHIFT)

        self.assertListEqual(proj.shifts(), [SHIFT])

    def test_one_extra_shift(self):
        proj = Project(shift=SHIFT, shift_list=f"{SHIFT_1}")

        self.assertListEqual(sorted(proj.shifts()), [SHIFT, SHIFT_1])

    def test_two_extra_shift(self):
        proj = Project(shift=SHIFT, shift_list=f"{SHIFT_1},{SHIFT_2}")

        self.assertListEqual(sorted(proj.shifts()),
                             [SHIFT, SHIFT_2, SHIFT_1])

    def test_main_and_extra_same(self):
        proj = Project(shift=SHIFT, shift_list=f"{SHIFT}")

        self.assertListEqual(proj.shifts(), [SHIFT])

    def test_main_in_extra(self):
        proj = Project(shift=SHIFT, shift_list=f"{SHIFT},{SHIFT_1}")

        self.assertListEqual(sorted(proj.shifts()), [SHIFT, SHIFT_1])
