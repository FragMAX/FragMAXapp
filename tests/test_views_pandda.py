import io
import json
from typing import Optional
from zipfile import ZipFile
from shutil import copyfile
from pathlib import Path
from unittest import TestCase
from projects.database import db_session
from fragview.views.pandda import _dir_to_tools_combo
from fragview.tools import Tool
from tests.utils import ViewTesterMixin, ProjectTestCase, data_file_path


def _make_combo_dir(
    pandda_dir: Path,
    proc: Tool,
    refine: Tool,
    create_results=True,
    results_data: Optional[str] = None,
):
    pandda_dir.mkdir(exist_ok=True)
    combo_dir = Path(pandda_dir, f"{proc.get_name()}-{refine.get_name()}")
    combo_dir.mkdir()

    result_dir = Path(combo_dir, "result")

    if create_results:
        file = Path(result_dir, "results.json")
        file.parent.mkdir()
        if results_data is not None:
            file.write_text(results_data)
        else:
            src = data_file_path("pandda_results.json")
            copyfile(src, file)

    return result_dir


def _make_unknown_tools_combo_dir(pandda_dir: Path):
    """
    create a pandda run directory, that appear correct,
    except the proc and refine tools are unknown
    """
    pandda_dir.mkdir(exist_ok=True)
    combo_dir = Path(pandda_dir, f"foo-bar")
    combo_dir.mkdir()

    file = Path(combo_dir, "result", "results.json")
    file.parent.mkdir()
    file.touch()


class TestDirToToolsCombo(TestCase):
    """
    test pandda._dir_to_tools_combo() function
    """

    def test_ok(self):
        combo = _dir_to_tools_combo(Path("xds-dimple"))
        self.assertEqual(combo.proc, "xds")
        self.assertEqual(combo.refine, "dimple")
        self.assertEqual(combo.ui_label, "XIA2/XDS - DIMPLE")

    def test_no_dash(self):
        self.assertIsNone(_dir_to_tools_combo(Path("nodash")))

    def test_unknown_tool(self):
        self.assertIsNone(_dir_to_tools_combo(Path("edna-unknown")))


class TestResultsView(ViewTesterMixin, ProjectTestCase):
    """
    test /pandda/results/ view
    """

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def create_pandda_results(self):
        pandda_dir = self.project.pandda_dir

        _make_combo_dir(pandda_dir, Tool.AUTOPROC, Tool.DIMPLE)
        _make_combo_dir(pandda_dir, Tool.XDS, Tool.DIMPLE)

        # 'failed' pandda run
        _make_combo_dir(pandda_dir, Tool.EDNA, Tool.DIMPLE, create_results=False)

        # make a special combo dir with unknown tool names
        _make_unknown_tools_combo_dir(pandda_dir)

        # random file in the pandda directory
        Path(pandda_dir, "some_file").touch()

    @db_session
    def test_no_results(self):
        resp = self.client.get("/pandda/results/")
        self.assert_response(resp, 200, "ok")

        # check that correct template was rendered
        self.assert_contains_template(resp, "pandda_results.html")
        # the results combo should be empty
        self.assertListEqual(resp.context["result_combos"], [])

    @db_session
    def test_got_results(self):
        self.create_pandda_results()

        resp = self.client.get("/pandda/results/")
        self.assert_response(resp, 200, "ok")

        # check that correct template was rendered
        self.assert_contains_template(resp, "pandda_results.html")

        result_combos = {f"{t.ui_label}" for t in resp.context["result_combos"]}
        self.assertSetEqual(result_combos, {"autoPROC - DIMPLE", "XIA2/XDS - DIMPLE"})


class TestEventsView(ViewTesterMixin, ProjectTestCase):
    """
    test /pandda/events/<proc>/<refine> view
    """

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def test_no_pandda_dir(self):
        resp = self.client.get("/pandda/events/edna/dimple")
        self.assert_response(resp, 500, "Error reading data.*")

    def test_unparsable_result_json(self):
        _make_combo_dir(
            self.project.pandda_dir,
            Tool.XDS,
            Tool.DIMPLE,
            results_data="not-proper-json",
        )
        resp = self.client.get("/pandda/events/xds/dimple")
        self.assert_response(resp, 500, "Error parsing.*")

    def test_invalid_shema_result_json(self):
        _make_combo_dir(
            self.project.pandda_dir, Tool.XDS, Tool.DIMPLE, results_data='{"foo": 1}'
        )
        resp = self.client.get("/pandda/events/xds/dimple")
        self.assert_response(resp, 500, "Unexpected json schema.*")

    def test_ok(self):
        _make_combo_dir(self.project.pandda_dir, Tool.XDS, Tool.DIMPLE)
        resp = self.client.get("/pandda/events/xds/dimple")
        self.assert_response(resp, 200, ".*")

        #
        # transform returned event to a set of tuples,
        # so it's easier to compare
        #
        data = json.loads(resp.content.decode())
        events = set()
        for event in data["events"]:
            events.add(
                (
                    event["dtag"],
                    event["event_num"],
                    event["event_fraction"],
                    event["bdc"],
                    event["z_peak"],
                    event["z_mean"],
                    event["cluster_size"],
                    event["map_uncertainty"],
                )
            )

        # check that we got expected events
        self.assertSetEqual(
            events,
            {
                ("Gal8N-x0009_3", 1, 0.34, 0.66, 4.012, 3.205, 171, 0.287),
                ("Gal8N-x0010_3", 1, 0.43, 0.57, 3.857, 3.008, 146, 0.22),
                ("Gal8N-x0010_3", 2, 0.33, 0.67, 3.718, 3.072, 251, 0.22),
            },
        )


class TestDownloadView(ViewTesterMixin, ProjectTestCase):
    """
    test /pandda/download/<proc>/<refine> view
    """

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def test_not_found(self):
        resp = self.client.get("/pandda/download/edna/dimple")
        self.assert_not_found_response(resp, "no results found.*")

    @db_session
    def test_ok(self):
        """
        test the happy path of downloading a PanDDA run file archive
        """
        #
        # set-up PanDDA run results directory
        #
        result_dir = _make_combo_dir(self.project.pandda_dir, Tool.XDS, Tool.DIMPLE)
        # add some extra dummy files
        Path(result_dir, "pandda.log").write_text("dummy log")
        graphs_dir = Path(result_dir, "analysis", "dataset_graphs")
        graphs_dir.mkdir(parents=True)
        Path(graphs_dir, "foobar.png").touch()

        #
        # download PanDDA archive for the run
        #
        resp = self.client.get("/pandda/download/xds/dimple")

        self.assertEquals(resp.status_code, 200)
        self.assertTrue(resp.streaming)

        #
        # check that downloaded zip-archive seems to be OK
        #
        zip_data = io.BytesIO(b"".join(resp.streaming_content))
        with ZipFile(zip_data) as zf:
            # testzip returns None if zip file is OK
            self.assertIsNone(zf.testzip())
            file_names = set(zf.namelist())
            self.assertSetEqual(
                file_names,
                {
                    "Nsp5-xds-dimple/results.json",
                    "Nsp5-xds-dimple/pandda.log",
                    "Nsp5-xds-dimple/analysis/dataset_graphs/foobar.png",
                },
            )
