from pathlib import Path
from projects.database import db_session
from tests.utils import ViewTesterMixin, ProjectTestCase


class _ClusterImageTestCase(ProjectTestCase, ViewTesterMixin):
    METHOD = "test_meth"
    CLUSTER = "test_clu"
    DUMMY_PNG_DATA = b"faux_png"
    PNG_MIME = "image/png"

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def _get_png_path(self):
        return Path(
            self.project.pandda_dir,
            self.METHOD,
            "clustered-datasets",
            "dendrograms",
            f"{self.CLUSTER}.png",
        )

    def _get_url(self):
        return f"/pandda/cluster/{self.METHOD}/{self.CLUSTER}/image"


class TestClusterImagePlainText(_ClusterImageTestCase):
    @db_session
    def test_ok(self):
        """
        test fetching cluster PNG image for plain text project
        """

        png_path = self._get_png_path()
        png_path.parent.mkdir(parents=True)
        png_path.write_bytes(self.DUMMY_PNG_DATA)

        resp = self.client.get(self._get_url())
        self.assert_response_equals(resp, 200, self.DUMMY_PNG_DATA, self.PNG_MIME)

    @db_session
    def test_png_not_found(self):
        """
        test the case where specified cluster is not found
        """
        resp = self.client.get(self._get_url())

        self.assert_not_found_response(resp, "^no dendrogram image for")
