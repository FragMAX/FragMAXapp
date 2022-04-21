import json
from pandas import read_csv
from projects.database import db_session
from tests.utils import ViewTesterMixin, ProjectTestCase
from tests.library_setup import create_library, Library, Fragment
from io import BytesIO


class _LibrariesViewTester(ProjectTestCase, ViewTesterMixin):
    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

        self.fraglib1 = create_library(
            Library(
                name="kiwis",
                fragments=[
                    Fragment(code="XX1", smiles="OC(=O)CN1CCCCCC1=O"),
                    Fragment(code="XX2", smiles="CC(=O)NC1CCNCC1"),
                    Fragment(code="XX3", smiles="NC1=NC=C(Cl)C=N1"),
                ],
            )
        )

        create_library(
            Library(name="orange", fragments=[Fragment(code="OR002", smiles="C")])
        )


class TestShowView(_LibrariesViewTester):
    @db_session
    def test_view(self):
        resp = self.client.get("/libraries/show")
        self.assert_contains_template(resp, "libraries.html")

        # check that libraries included seem resonable
        libs = resp.context["libraries"]
        lib_names = {lib.name for lib in libs}
        self.assertSetEqual(lib_names, {"kiwis", "orange"})


class TestAsJson(_LibrariesViewTester):
    @db_session
    def test_ok(self):
        resp = self.client.get(f"/libraries/{self.fraglib1.id}/json")

        # check headers
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp["content-type"], "application/json")

        # check that we got correct json
        lib = json.loads(resp.content)
        self.assertDictEqual(
            lib,
            {
                "fragments": [
                    {"code": "XX1", "smiles": "OC(=O)CN1CCCCCC1=O", "id": 1},
                    {"code": "XX2", "smiles": "CC(=O)NC1CCNCC1", "id": 2},
                    {"code": "XX3", "smiles": "NC1=NC=C(Cl)C=N1", "id": 3},
                ]
            },
        )

    def test_unknown_lib(self):
        resp = self.client.get("/libraries/9876/json")

        self.assert_not_found_response(
            resp, "fragment library with id '9876' not found"
        )


class TestAsCSV(_LibrariesViewTester):
    @db_session
    def test_ok(self):
        resp = self.client.get(f"/libraries/{self.fraglib1.id}/csv")

        # check headers
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp["content-type"], "text/csv")
        self.assertEquals(resp["content-disposition"], "attachment; filename=kiwis.csv")

        # check that CSV looks ok
        lib = read_csv(BytesIO(resp.content))
        self.assertDictEqual(
            lib.to_dict(),
            {
                "# Fragments Library 'kiwis'": {
                    "FragmentCode": "SMILES",
                    "XX1": "OC(=O)CN1CCCCCC1=O",
                    "XX2": "CC(=O)NC1CCNCC1",
                    "XX3": "NC1=NC=C(Cl)C=N1",
                }
            },
        )

    def test_unknown_lib(self):
        resp = self.client.get("/libraries/9876/csv")

        self.assert_not_found_response(
            resp, "fragment library with id '9876' not found"
        )
