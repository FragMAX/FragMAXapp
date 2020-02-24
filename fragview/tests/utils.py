from fragview import auth
from django import test


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

    def assert_contains_template(self, response, template_name):
        """
        assert that the response rendering involved using the specified template
        """
        templ_names = [t.name for t in response.templates]
        self.assertIn(template_name, templ_names)
