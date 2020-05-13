from unittest import mock
from django import test

from fragview.models import Library, Project, PendingProject, User
from tests.utils import ViewTesterMixin

PROTO = "PRTN"
LIBRARY = "JBSD"
SHIFT = "12345678"


class _ProjectTestCase(test.TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()

    def assert_field_required_error(self, response, field_name):
        """
        check that response's context contains the
          'field is required'
        error message for specifield field
        """
        form_errs = response.context["form"].errors
        self.assertIn("This field is required", form_errs[field_name].as_text())


class TestListProjects(_ProjectTestCase):
    @staticmethod
    def _save_projs(*proj_mods):
        """
        save projects models to database, return set of project IDs
        """
        ids = set()
        for proj in proj_mods:
            proj.save()
            ids.add(proj.id)

        return ids

    def test_list(self):
        lib = Library(name="JBS")
        lib.save()

        proj_ids = self._save_projs(
            Project(protein="PRT", library=lib, proposal=self.PROP1, shift="20190808"),
            Project(protein="AST", library=lib, proposal=self.PROP1, shift="20190808"))

        resp = self.client.get("/projects/")

        # check listed project by comparing IDs
        listed_proj_ids = set([p.id for p in resp.context["projects"]])
        self.assertSetEqual(proj_ids, listed_proj_ids)

        self.assert_contains_template(resp, "fragview/projects.html")


class TestEditNotFound(_ProjectTestCase):
    """
    testing getting/posting to a project edit page with invalid project ID
    """
    def setUp(self):
        super().setUp()
        lib = Library(name="JBS")
        lib.save()
        Project(protein="PRT", library=lib, proposal=self.PROP1, shift="20190808").save()

    def test_get(self):
        resp = self.client.get("/project/23/")
        self.assertEqual(404, resp.status_code)

    def test_post(self):
        resp = self.client.post(f"/project/23/", dict(action="modify"))
        self.assertEqual(404, resp.status_code)


class TestEdit(_ProjectTestCase):
    def setUp(self):
        super().setUp()

        lib = Library(name="JBS")
        lib.save()

        self.proj = Project(protein="PRT", library=lib,
                            proposal=self.PROP1, shift="20190808")
        self.proj.save()
        self.url = f"/project/{self.proj.id}/"

    def test_invalid_action(self):
        resp = self.client.post(self.url, dict(action="oranges"))

        self.assertEqual(400, resp.status_code)
        self.assertEqual(resp.content, b"unexpected action 'oranges'")

    def test_delete(self):
        resp = self.client.post(self.url, dict(action="delete"))

        # check that the project was deleted
        self.assertFalse(Project.objects.filter(id=self.proj.id).exists())

        # check that we were redirected to 'projects' page
        self.assertEqual(302, resp.status_code)
        self.assertEqual("/projects/", resp.url)

    @mock.patch("os.path.isdir")
    @mock.patch("fragview.views.projects.add_new_shifts")
    def test_new_shift(self, add_task_mock, _):
        # make sure the projects shift list is empty
        self.assertEqual("", self.proj.shift_list)

        resp = self.client.post(self.url,
                                dict(action="modify",
                                     protein=self.proj.protein,
                                     library=self.proj.library,
                                     proposal=self.proj.proposal,
                                     shift=self.proj.shift,
                                     # we'll test setting the shift list
                                     shift_list=SHIFT))

        # check that we were redirected to 'projects' page
        self.assertRedirects(resp, "/projects/")

        # check that project's shift list was stored in the DB
        proj = Project.objects.get(id=self.proj.id)
        self.assertEqual(SHIFT, proj.shift_list)

        # project should go into pending state
        pend_proj = PendingProject.objects.get(project=proj.id)
        self.assertIsNotNone(pend_proj)

        # check that 'add_new_shift' task was started
        add_task_mock.delay.assert_called_once_with(proj.id, [SHIFT])

    def test_modify_invalid(self):
        """
        try to modify project using invalid form data
        """

        # modify request with missing form fields
        resp = self.client.post(self.url, dict(action="modify"))

        self.assert_field_required_error(resp, "protein")

        # check that we are still on the 'edit project' page
        self.assertEqual(200, resp.status_code)
        self.assert_contains_template(resp, "fragview/project.html")

    def test_get_edit_page(self):
        """
        test going to the project edit page
        """
        # modify request with missing form fields
        resp = self.client.get(self.url)

        # check that we are still on the 'edit project' page
        self.assertEqual(200, resp.status_code)
        self.assert_contains_template(resp, "fragview/project.html")


class TestNew(_ProjectTestCase):
    def test_get_new_proj_page(self):
        """
        test loading 'new project' page
        """
        resp = self.client.get("/project/new")

        self.assertEqual(200, resp.status_code)
        self.assert_contains_template(resp, "fragview/project.html")

    def test_new_invalid(self):
        resp = self.client.post("/project/new")

        # check that we are still on 'new project' page
        self.assertEqual(200, resp.status_code)
        self.assert_contains_template(resp, "fragview/project.html")

        # check that we at least got error message for 'protein' field
        self.assert_field_required_error(resp, "protein")

    @mock.patch("os.path.isdir")
    @mock.patch("fragview.views.projects.setup_project_files")
    def test_create_new(self, setup_proj_mock, isdir_mock):
        def _frags(library):
            return [(frag.name, frag.smiles) for frag in library.fragment_set.all()]

        isdir_mock.return_value = True

        # create a mocked 'file-like' object
        frags_file = mock.Mock()
        frags_file.name = "JBS.csv"
        frags_file.read.return_value = "A1a,N#Cc1c(cccc1)O"

        resp = self.client.post("/project/new",
                                dict(protein=PROTO,
                                     library_name=LIBRARY,
                                     fragments_file=frags_file,
                                     proposal=self.PROP1,
                                     shift=SHIFT))

        # check that we were redirected to 'projects' page
        self.assertRedirects(resp, "/projects/")

        # check that project saved in the database looks good
        proj = Project.objects.get(protein=PROTO)
        self.assertEqual(LIBRARY, proj.library.name)
        self.assertListEqual(_frags(proj.library),
                             [("A1a", "N#Cc1c(cccc1)O")])
        self.assertEqual(self.PROP1, proj.proposal)
        self.assertEqual(SHIFT, proj.shift)

        # project should be in 'pending' state
        self.assertTrue(PendingProject.objects.filter(project=proj.id).exists())

        # check that 'set-up project files' task have been started
        setup_proj_mock.delay.assert_called_once_with(proj.id)


class TestSetCurrent(_ProjectTestCase):
    def setUp(self):
        super().setUp()
        lib = Library(name="JBS")
        lib.save()

        self.proj = Project(protein="PRT", library=lib, proposal=self.PROP1, shift="20190808")
        self.proj.save()

    def test_set(self):
        resp = self.client.post(f"/project/current/{self.proj.id}/")

        # we expected to be redirected to site's root page
        self.assertRedirects(resp, "/")

        # check that current project was stored in the DB
        usr = User.objects.get(id=self.user.id)
        self.assertEqual(usr.current_project.id, self.proj.id)

    def test_set_invalid(self):
        invalid_id = 1234
        self.assertFalse(Project.objects.filter(id=invalid_id).exists())

        # we should got '404 not found' reply
        resp = self.client.post(f"/project/current/{invalid_id}/")
        self.assertEqual(404, resp.status_code)
