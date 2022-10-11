from io import BytesIO
from unittest.mock import patch
from projects.database import db_session
from fragview.views.crystals import _CrystalInfo
from tests.project_setup import Project, Crystal, DataSet
from tests.utils import ViewTesterMixin, ProjectTestCase
from tests.library_setup import create_library, Library, Fragment

IMPORT_URL = "/crystals/import"

PROJECT = Project(
    proposal="20190242",
    protein="TRIM2",
    encrypted=False,
    crystals=[
        Crystal("TRIM2-x0000", None, None),  # Apo crystal
        Crystal("TRIM2-x0010", "VTL", "VT0"),
        Crystal("TRIM2-x0011", "VTL", "VT1"),
        Crystal("TRIM2-x0012", "VTL", "VT2"),
    ],
    datasets=[
        DataSet("TRIM2-x0010", 1),
        DataSet("TRIM2-x0011", 1),
        DataSet("TRIM2-x0011", 2),
    ],
    results=[],
)


class _CrystalsViewTester(ProjectTestCase, ViewTesterMixin):
    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)


class TestShowView(_CrystalsViewTester):
    """
    test '/crystals/new' view
    """

    PROJECTS = [PROJECT]

    @db_session
    def test_view(self):
        resp = self.client.get("/crystals")

        # check that correct template was rendered
        self.assert_contains_template(resp, "crystals.html")

        # check that we got expected crystals info list
        self.assertListEqual(
            resp.context["crystals"],
            [
                _CrystalInfo(
                    id="TRIM2-x0000",
                    datasets_num=0,
                    fragment_library=None,
                    fragment_code=None,
                ),
                _CrystalInfo(
                    id="TRIM2-x0010",
                    datasets_num=1,
                    fragment_library="VTL",
                    fragment_code="VT0",
                ),
                _CrystalInfo(
                    id="TRIM2-x0011",
                    datasets_num=2,
                    fragment_library="VTL",
                    fragment_code="VT1",
                ),
                _CrystalInfo(
                    id="TRIM2-x0012",
                    datasets_num=0,
                    fragment_library="VTL",
                    fragment_code="VT2",
                ),
            ],
        )


class TestNewView(_CrystalsViewTester):
    """
    test '/crystals/new' view
    """

    @db_session
    def test_view(self):
        """
        check that 'new crystals' template is rendered
        """
        resp = self.client.get("/crystals/new")
        self.assert_contains_template(resp, "crystals_new.html")


class TestValidateCrystalsCSV(_CrystalsViewTester):
    """
    test 'crystals CSV' validation code
    """

    PROJECTS = [PROJECT]

    def _get_crystals_csv(self, crystals: str) -> BytesIO:
        csv_text = f"SampleID,FragmentLibrary,FragmentCode\n{crystals}"
        return BytesIO(csv_text.encode())

    @db_session
    def test_valid(self):
        """
        valid CSV with correct two existing crystals
        """
        csv = self._get_crystals_csv("TRIM2-x0000,,\nTRIM2-x0010,VTL,VT0")

        with patch("fragview.views.crystals.import_crystals"):
            resp = self.client.post(
                IMPORT_URL,
                dict(method="upload_file", crystals_csv_file=csv),
            )

        self.assert_response(resp, 200, "ok")

    @db_session
    def test_apo_redefined(self):
        """
        existing Apo crystal redefined with a fragment
        """
        csv = self._get_crystals_csv("TRIM2-x0000,VTL,VT1")
        resp = self.client.post(
            IMPORT_URL,
            dict(method="upload_file", crystals_csv_file=csv),
        )
        self.assert_bad_request(
            resp, "TRIM2-x0000: Apo crystal have a fragment defined"
        )

    @db_session
    def test_fragment_redefined(self):
        """
        existing crystal have a different fragment specified
        """
        csv = self._get_crystals_csv("TRIM2-x0010,VTL,VT2")
        resp = self.client.post(
            IMPORT_URL,
            dict(method="upload_file", crystals_csv_file=csv),
        )
        self.assert_bad_request(resp, "TRIM2-x0010: unexpected fragment code VT2")

    @db_session
    def test_no_fragment(self):
        """
        existing crystal redefined as Apo crystal
        """
        csv = self._get_crystals_csv("TRIM2-x0010,,")
        resp = self.client.post(
            IMPORT_URL,
            dict(method="upload_file", crystals_csv_file=csv),
        )
        self.assert_bad_request(resp, "TRIM2-x0010: no fragment specified")

    @db_session
    def test_library_redined(self):
        """
        existing crystal have different fragment library specified
        """
        create_library(
            Library(name="NewLib", fragments=[Fragment(code="XX1", smiles="C")])
        )

        csv = self._get_crystals_csv("TRIM2-x0010,NewLib,XX1")
        resp = self.client.post(
            IMPORT_URL,
            dict(method="upload_file", crystals_csv_file=csv),
        )
        self.assert_bad_request(resp, "TRIM2-x0010: unexpected library NewLib")

    @db_session
    def test_invalid_crystals_csv(self):
        """
        a crystals CSV that is semantically incorrect
        """
        # CSV that is missing required columns
        invalid_csv = BytesIO(b"Some,Random,Things")
        resp = self.client.post(
            IMPORT_URL, dict(method="upload_file", crystals_csv_file=invalid_csv)
        )

        self.assert_bad_request(
            resp, f"Could not parse Crystals CSV.\nUnexpected columns"
        )


class TestImportView(_CrystalsViewTester):
    """
    test '/crystals/import' view
    """

    CRYSTALS_CSV = BytesIO(
        b"""SampleID,FragmentLibrary,FragmentCode
    TRIM2-x9910,VTL,VT00002
    TRIM2-x9911,VTL,VT00015
    """
    )

    LIBRARY = Library(
        name="VTL",
        fragments=[
            Fragment("VT00002", "NC(=O)C1=CC=CC(CO)=C1"),
            Fragment("VT00015", "O=C(N1CCNCC1)C1=CC=NC=C1"),
        ],
    )

    @db_session
    def test_ok(self):
        create_library(self.LIBRARY)

        #
        # make 'import crystals' request,
        # mock call to start worker task
        #
        with patch("fragview.views.crystals.import_crystals") as import_task:
            resp = self.client.post(
                IMPORT_URL,
                dict(method="upload_file", crystals_csv_file=self.CRYSTALS_CSV),
            )

        # check response
        self.assert_response(resp, 200, "ok")

        # check task start call
        import_task.delay.assert_called_once_with(
            str(self.project.id),
            [
                {
                    "SampleID": "TRIM2-x9910",
                    "FragmentLibrary": "VTL",
                    "FragmentCode": "VT00002",
                },
                {
                    "SampleID": "TRIM2-x9911",
                    "FragmentLibrary": "VTL",
                    "FragmentCode": "VT00015",
                },
            ],
        )

        # check that project is marked as 'pending'
        usr_proj = self.get_user_project(self.project)
        self.assertTrue(usr_proj.is_pending())

    @db_session
    def test_bad_method(self):
        """
        test doing non-post request to the view
        """
        resp = self.client.get(IMPORT_URL)
        self.assert_bad_request(resp, "expected POST request")

    @db_session
    def test_invalid_post(self):
        """
        test case where invalid POST request is made
        """
        # post request without 'crystals CSV' file provided
        resp = self.client.post(IMPORT_URL, dict(foo="bar"))
        self.assert_bad_request(resp, ".*This field is required")
