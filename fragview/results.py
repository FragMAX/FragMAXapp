# TODO: remove this module?
import csv
from typing import Dict, List
from pathlib import Path
from fragview.projects import project_results_file
from fragview.fileio import read_csv_lines

HEADER = [
    "usracr",
    "pdbout",
    "dif_map",
    "nat_map",
    "spg",
    "resolution",
    "ISa",
    "r_work",
    "r_free",
    "bonds",
    "angles",
    "a",
    "b",
    "c",
    "alpha",
    "beta",
    "gamma",
    "blist",
    "dataset",
    "pipeline",
    "rhofitscore",
    "ligfitscore",
    "ligblob",
    "modelscore",
]


def _load_results(project) -> Dict[str, List]:
    results_file = Path(project_results_file(project))
    results: Dict[str, List] = {}

    if not results_file.is_file():
        return results

    for line in read_csv_lines(results_file):
        name, *vals = line
        results[name] = vals

    # remove header row, if present
    header_key = HEADER[0]
    if header_key in results:
        del results[header_key]

    return results


def _write_results(project, results: Dict[str, List]):
    with open(project_results_file(project), "w") as f:
        writer = csv.writer(f)

        # write header
        writer.writerow(HEADER)

        for name, vals in results.items():
            writer.writerow([name, *vals])


# TODO: remove me
def update_dataset_results(project, dataset: str, refine_tool: str, updated_results):
    """
    NOTE: we assume the 'write results.csv' lock is held
    """
    results = _load_results(project)

    for res in updated_results:
        proc_tool, *vals, rhofit_score, ligfit_score, ligblob = res
        pipeline = f"{proc_tool}_{refine_tool}"
        results[f"{dataset}_{pipeline}"] = (
            # include 'dummy.pdb' as a hack for now,
            # to allow results view to to differentiate between
            # pipedream results and results from other tools
            # (results view assumes that no PDB listed -> pipedream result)
            ["dummy.pdb"]
            + vals
            + [dataset, pipeline, rhofit_score, ligfit_score, ligblob, ""]
        )

    _write_results(project, results)
