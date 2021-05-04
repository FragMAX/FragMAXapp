import csv
from typing import List, Optional, Iterable, Iterator, Tuple
import re
import json
import pandas
from pandas import Series
from pathlib import Path
from dataclasses import dataclass
from fragview.projects import Project

"""
Handle 'file scraping' for pandda runs.

Get list of generated reports, used data selections methods, etc.
"""

ANALYSIS_SUBDIR = "analyses-"


class PanddaSelectedDatasets:
    JSON_FILE_NAME = "selection.json"

    def __init__(self):
        self._selection = []

    def __iter__(self):
        for dataset, pdb in self._selection:
            yield dataset, pdb

    @staticmethod
    def _get_json_file(pandda_dir: Path) -> Path:
        return Path(pandda_dir, PanddaSelectedDatasets.JSON_FILE_NAME)

    def add(self, dataset_name: str, pdb_file: Path):
        self._selection.append([dataset_name, str(pdb_file)])

    def save(self, pandda_dir: Path):
        json_file = PanddaSelectedDatasets._get_json_file(pandda_dir)
        json_file.write_text(json.dumps(self._selection, indent=True))

    @staticmethod
    def load(pandda_dir: Path) -> "PanddaSelectedDatasets":
        json_file = PanddaSelectedDatasets._get_json_file(pandda_dir)

        obj = PanddaSelectedDatasets()
        obj._selection = json.loads(json_file.read_text())

        return obj


@dataclass
class Inspect:
    dataset: str
    method: str
    site_idx: str
    event_idx: str


class Inspects:
    FILE_NAME = "inspects.csv"

    def __init__(self):
        self._inspects = []

    @staticmethod
    def _get_csv_file(pandda_dir: Path) -> Path:
        return Path(pandda_dir, Inspects.FILE_NAME)

    def add(self, inspect: Inspect):
        self._inspects.append(inspect)

    def save(self, pandda_dir: Path):
        file = Inspects._get_csv_file(pandda_dir)
        with file.open("w", newline="") as f:
            writer = csv.writer(f)

            for inspect in self._inspects:
                writer.writerow(
                    [
                        inspect.dataset,
                        inspect.method,
                        inspect.site_idx,
                        inspect.event_idx,
                    ]
                )

    @staticmethod
    def _inspect_objs(pandda_dir: Path) -> Iterator[Inspect]:
        file = Inspects._get_csv_file(pandda_dir)
        with file.open(newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                yield Inspect(*row)

    @staticmethod
    def find(
        pandda_dir: Path, inspect: Inspect
    ) -> Tuple[Optional[Inspect], Optional[Inspect]]:
        inspects = Inspects._inspect_objs(pandda_dir)
        previous = None
        while ins := next(inspects, None):
            if ins == inspect:
                break
            previous = ins

        return previous, next(inspects, None)


class PanddaMethodReports:
    def __init__(
        self,
        report_dates: List[str],
        coot_command: str,
        selected_datasets: PanddaSelectedDatasets,
        dendrogram: List[str],
    ):
        self.report_dates = report_dates
        self.coot_command = coot_command
        self.selected_datasets = selected_datasets
        self.dendrogram = dendrogram


class _PanddaCSVParser:
    def __init__(self, csv_path: Path):
        self._data = pandas.read_csv(csv_path)

    def _get_first_row(self, dtag: str) -> Optional[Series]:
        rows = self._data.loc[self._data["dtag"] == dtag]

        if rows.empty:
            # no row with specified dtag found
            return None

        return rows.iloc[0]


class PanddaAnalyseEvents(_PanddaCSVParser):
    """
    pandda_analyse_events.csv parser
    """

    def get_first_event(self, dtag: str) -> Optional[Series]:
        return self._get_first_row(dtag)


class PanddaAllDatasetInfo(_PanddaCSVParser):
    """
    all_datasets_info.csv parser
    """

    def get_dataset(self, dtag: str) -> Optional[Series]:
        return self._get_first_row(dtag)


class PanddaAnalyseSites(_PanddaCSVParser):
    """
    pandda_analyse_sites.csv parser
    """

    # regexp that matches triplet of comma separated decimal numbers inside paranthesis
    # e.g. "(1.34, -2.44, 0.01)"
    TRIPLE_RE = re.compile(r"\(([^,_]+), *([^,_]+), *([^,_]+)\)")

    def get_native_centroids(self) -> Iterable[List[float]]:
        def parse_tripple(text):
            match = self.TRIPLE_RE.match(text)
            nums = [float(v) for v in match.groups()]
            return nums

        for val in self._data.native_centroid:
            yield parse_tripple(val)


def _analysis_date(analysis_dir: Path):
    return analysis_dir.name[len(ANALYSIS_SUBDIR) :]


def get_latest_method(project: Project) -> Optional[str]:
    """
    find the latest generated analysis folder inside pandda directories
    and return it's selection method name
    """

    latest_analysis_date = ""
    latest_analysis_path = None

    for analysis_dir in project.pandda_dir.glob(f"*/pandda/{ANALYSIS_SUBDIR}*"):
        new_date = analysis_dir.name[len(ANALYSIS_SUBDIR) :]
        if new_date > latest_analysis_date:
            latest_analysis_date = new_date
            latest_analysis_path = analysis_dir

    if latest_analysis_path is None:
        # no pandda runs found
        return None

    return latest_analysis_path.parents[1].name


def get_available_methods(project: Project):
    for method_dir in project.pandda_dir.iterdir():
        if not method_dir.is_dir():
            continue

        yield method_dir.name


def _list_method_report_dates(method_dir: Path):
    root_dir = Path(method_dir, "pandda")
    for analysis_dir in root_dir.glob(f"{ANALYSIS_SUBDIR}*"):
        analysis_html = Path(analysis_dir, "html_summaries", "pandda_analyse.html")
        if analysis_html.is_file():
            yield _analysis_date(analysis_dir)


def _get_coot_command(method_dir: Path) -> str:
    from fragview.sites import SITE

    return SITE.get_pandda_inspect_commands(method_dir)


def _get_dendrograms(method_dir):
    dendrograms = Path(method_dir, "clustered-datasets", "dendrograms")
    for png in dendrograms.glob("*.png"):
        yield png.stem


def get_analysis_dir(project: Project, method: str, date: str) -> Path:
    return Path(Path(project.pandda_dir, method, "pandda"), f"{ANALYSIS_SUBDIR}{date}")


def get_analysis_html_file(project: Project, method: str, date: str) -> Path:
    analysis_dir = get_analysis_dir(project, method, date)

    return Path(
        analysis_dir,
        "html_summaries",
        "pandda_analyse.html",
    )


def load_method_reports(project: Project, method: str) -> PanddaMethodReports:
    method_dir = Path(project.pandda_dir, method)

    report_dates = _list_method_report_dates(method_dir)
    coot_command = _get_coot_command(method_dir)
    selected = PanddaSelectedDatasets.load(method_dir)
    dendrograms = _get_dendrograms(method_dir)

    return PanddaMethodReports(list(report_dates), coot_command, selected, dendrograms)
