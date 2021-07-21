from unittest.mock import Mock
from fragview import projects
from fragview.models import User
from tests.utils import ProjectTestCase

TEST_PROPS_DIR = "/test/data"


class TestCurrentProject(ProjectTestCase):
    """
    test projects.current_project()
    """

    OTHER_PROPOSAL = "20209988"

    def setUp(self):
        super().setUp()

        user_project = self.get_user_project(self.project)
        self.user = User(current_project=user_project)
        self.user.save()

    def _setup_request_mock(self, user_proposals):
        request = Mock()
        request.user = self.user
        request.session = dict(proposals=user_proposals)

        return request

    def test_current_project(self):
        """
        test the case were we successfully can get current project
        """
        request = self._setup_request_mock(self.proposals)

        cur_proj = projects.current_project(request)
        self.assertEqual(self.project.id, cur_proj.id)

    def test_current_project_no_access(self):
        """
        test the case when user is not a part of it's current
        project's proposal
        """
        request = self._setup_request_mock([self.OTHER_PROPOSAL])

        self.assertIsNone(projects.current_project(request))
