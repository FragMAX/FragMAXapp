from pathlib import Path
from fragview.fileio import read_text_lines


def _get_xscale_logs(logs_dir: Path):
    return sorted(logs_dir.glob("*XSCALE.LP"), reverse=True)


def scrape_logs(project, logs_dir: Path):
    isa = ""

    for log in _get_xscale_logs(logs_dir):
        log_lines = list(read_text_lines(project, log))
        for n, line in enumerate(log_lines):
            if "ISa" in line:
                if log_lines[n + 1].split():
                    isa = log_lines[n + 1].split()[-2]
                    if isa == "b":
                        isa = ""

    return isa
