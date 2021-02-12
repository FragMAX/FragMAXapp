import re

SBATCH_REPLY = re.compile(r"^Submitted batch job (\d+)")


def parse_sbatch_reply(reply):
    for line in reply.splitlines():
        match = SBATCH_REPLY.match(line)
        if match is not None:
            return match.groups()[0]

    # could not find expected 'Submitted...' reply line
    # TODO: think about the exception we should raise
    raise ValueError(f"sbatch_reply, can't parse '{reply}'")


SACCT_HEADER_REXP = re.compile(r"\s*JobID\s.+State.+")
SACCT_SEPARATOR_REXP = re.compile(r"(?:-+\s*)+.*")
SACCT_STATUS_LINE = re.compile(
    r"^(\d+)\s.*(COMPLETED|RUNNING|PENDING|CANCELLED|FAILED).*"
)


def parse_sacct_reply(reply):
    def as_lines(output):
        for line in output.splitlines():
            yield line

    def valid_header(lines):
        if SACCT_HEADER_REXP.fullmatch(next(lines)) is None:
            return False

        if SACCT_SEPARATOR_REXP.fullmatch(next(lines)) is None:
            return False

        return True

    def parse_status_line(line):
        match = SACCT_STATUS_LINE.fullmatch(line)
        if match is None:
            return

        return match.groups()

    lines = as_lines(reply)
    if not valid_header(lines):
        # TODO think about exceptions
        raise ValueError("unpossible to parse")

    for line in lines:
        res = parse_status_line(line)
        if res is not None:
            yield res
