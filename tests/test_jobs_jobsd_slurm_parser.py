from unittest import TestCase
from jobs.jobsd.slurm_parser import parse_sbatch_reply, parse_sacct_reply


SACCT_REPLY = """       JobID    JobName  Partition    Account  AllocCPUS      State ExitCode
------------ ---------- ---------- ---------- ---------- ---------- --------
144270            DIALS        all      staff         40    RUNNING      0:0
144270.batch      batch                 staff         40    RUNNING      0:0
144270.exte+     extern                 staff         40    RUNNING      0:0
144271            DIALS        all      staff         40    RUNNING      0:0
144271.batch      batch                 staff         40    RUNNING      0:0
144271.exte+     extern                 staff         40    RUNNING      0:0
144272            DIALS        all      staff          0    PENDING      0:0
144272.batch      batch                 staff         40    RUNNING      0:0
144272.exte+     extern                 staff         40    RUNNING      0:0
144273            DIALS        all      staff         40 CANCELLED+      0:0
144273.batch      batch                 staff         40    RUNNING      0:0
144273.exte+     extern                 staff         40    RUNNING      0:0
"""


class TestParseSbatchReply(TestCase):
    """
    test parse_sbatch_reply() function
    """

    def test_ok(self):
        job_id = parse_sbatch_reply("Submitted batch job 144262\n")
        self.assertEquals(job_id, "144262")


class TestParseSacctReply(TestCase):
    """
    parse_sacct_reply() function
    """

    def test_ok(self):
        jobs_status = parse_sacct_reply(SACCT_REPLY)
        self.assertListEqual(
            list(jobs_status),
            [
                ("144270", "RUNNING"),
                ("144271", "RUNNING"),
                ("144272", "PENDING"),
                ("144273", "CANCELLED"),
            ],
        )
