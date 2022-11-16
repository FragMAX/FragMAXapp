from itertools import count
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from projects.database import db_session
from jobs.jobsd.nodes import (
    JobNode,
    get_job_nodes,
    get_root_nodes,
    mark_job_started,
    mark_job_finished,
)
from tests.utils import ProjectTestCase


def _node_equals(node1: JobNode, node2: JobNode) -> bool:
    #
    # check that arguments match
    #
    if len(node1.arguments) != len(node2.arguments):
        return False

    for larg, rarg in zip(node1.arguments, node2.arguments):
        if larg != rarg:
            return False

    #
    # check that previous_jobs match
    #
    if len(node1.previous_jobs) != len(node2.previous_jobs):
        return False

    node1.previous_jobs.sort(key=lambda n: n.description)
    node2.previous_jobs.sort(key=lambda n: n.description)

    for lnode, rnode in zip(node1.previous_jobs, node2.previous_jobs):
        if not _node_equals(lnode, rnode):
            return False

    #
    # all the rest of field should also match
    #
    return (
        node1.project_id == node2.project_id
        and node1.db_job_id == node2.db_job_id
        and node1.description == node2.description
        and node1.program == node2.program
        and node1.stdout == node2.stdout
        and node1.stderr == node2.stderr
        and node1.cpus == node2.cpus
        and node1.run_on == node2.run_on
    )


def _get_node_trees(num_of_trees):
    def _get_node(name, job_id, run_on):
        return JobNode(
            "42",
            str(job_id),
            name,
            f"{name}.sh",
            [],
            f"{name}.out",
            f"{name}.err",
            0,
            run_on,
        )

    def _get_one_tree(ids, num):
        leaf = _get_node(f"leaf-{num}", next(ids), "hpc")
        root = _get_node(f"root-{num}", next(ids), "local")

        root.previous_jobs = [leaf]

        return leaf, root

    def _get_trees():
        ids = count()

        for n in range(1, num_of_trees + 1):
            leaf, root = _get_one_tree(ids, n)
            yield leaf
            yield root

    return list(_get_trees())


class TestGetJobNodes(ProjectTestCase):
    """
    test get_job_nodes()
    """

    def _setup_many_to_one_tree_jobs(self):
        def _get_leaf_jobs():
            for n in range(1, 5):
                yield db.Job(
                    jobs_set=jobs_set,
                    description=f"job{n}",
                    program=f"job{n}.sh",
                    stdout=f"stdout{n}",
                    stderr=f"stderr{n}",
                    run_on=f"hpc",
                )

        db = self.project.db
        with db_session:
            jobs_set = jobs_set = db.JobsSet(description="test")

            leaf_jobs = list(_get_leaf_jobs())

            root_job = db.Job(
                jobs_set=jobs_set,
                description="root",
                program="root.sh",
                stdout="stdout-root",
                stderr="stderr-root",
                run_on="local",
            )
            root_job.previous_jobs = leaf_jobs

        all_jobs = leaf_jobs + [root_job]
        job_ids = {j.description: j.id for j in all_jobs}

        return jobs_set.id, job_ids

    def _get_many_to_one_tree_nodes(self, job_ids):
        def _get_leaf_nodes():
            for n in range(1, 5):
                yield JobNode(
                    str(self.project.id),
                    str(job_ids[f"job{n}"]),
                    f"job{n}",
                    f"job{n}.sh",
                    [],
                    f"stdout{n}",
                    f"stderr{n}",
                    0,
                    "hpc",
                )

        leaf_nodes = list(_get_leaf_nodes())

        root_node = JobNode(
            str(self.project.id),
            str(job_ids["root"]),
            "root",
            "root.sh",
            [],
            "stdout-root",
            "stderr-root",
            0,
            "local",
        )
        root_node.previous_jobs = leaf_nodes

        all_nodes = leaf_nodes + [root_node]

        return {n.description: n for n in all_nodes}

    def test_many_to_one_tree_jobs(self):
        """
        Test the case where is a number of 'leaf' jobs that must
        complete before we can run a 'root' job.

        This tests the case of running a PanDDa jobs set.
        """
        js_id, job_ids = self._setup_many_to_one_tree_jobs()

        with patch("conf.PROJECTS_DB_DIR", self.projects_db_dir):
            nodes = get_job_nodes(self.project.id, js_id)

        # there should be 5 job nodes
        self.assertEquals(len(nodes), 5)

        #
        # check that we got the expected nodes
        #
        exp_nodes = self._get_many_to_one_tree_nodes(job_ids)
        nodes_by_desc = {n.description: n for n in nodes}

        for desc in ["job1", "job2", "job3", "job4", "root"]:
            self.assertTrue(_node_equals(exp_nodes[desc], nodes_by_desc[desc]))

    def _setup_many_two_node_tree_jobs(self, num_of_trees):
        def _get_job(name, run_on):
            return db.Job(
                jobs_set=jobs_set,
                description=name,
                program=f"{name}.sh",
                stdout=f"{name}.out",
                stderr=f"{name}.err",
                run_on=run_on,
            )

        def _get_one_tree(num):
            leaf = _get_job(f"leaf-{num}", "hpc")
            root = _get_job(f"root-{num}", "local")
            root.previous_jobs = [leaf]

            return leaf, root

        def _get_trees():
            for n in range(1, num_of_trees + 1):
                leaf, root = _get_one_tree(n)
                yield leaf
                yield root

        db = self.project.db
        with db_session:
            jobs_set = jobs_set = db.JobsSet(description="test")
            jobs = list(_get_trees())

        job_ids = job_ids = {j.description: j.id for j in jobs}

        return jobs_set.id, job_ids

    def _get_many_two_node_tree_nodes(self, job_ids, num_of_trees):
        def _get_node(name, run_on):
            return JobNode(
                str(self.project.id),
                str(job_ids[name]),
                name,
                f"{name}.sh",
                [],
                f"{name}.out",
                f"{name}.err",
                0,
                run_on,
            )

        def _get_one_tree(num):
            leaf = _get_node(f"leaf-{num}", "hpc")
            root = _get_node(f"root-{num}", "local")

            root.previous_jobs = [leaf]

            return leaf, root

        def _get_trees():
            for n in range(1, num_of_trees + 1):
                leaf, root = _get_one_tree(n)
                yield leaf
                yield root

        return {n.description: n for n in _get_trees()}

    def test_many_two_node_tree_jobs(self):
        """
        Test the case when the 'jobs set' is a set of 3 two-node graph,
        with one job depending on another.

        This tests the typical case when we process 3 datasets.
        """

        js_id, job_ids = self._setup_many_two_node_tree_jobs(3)

        with patch("conf.PROJECTS_DB_DIR", self.projects_db_dir):
            nodes = get_job_nodes(self.project.id, js_id)

        # there should be 6 job nodes
        self.assertEquals(len(nodes), 6)

        #
        # check that we got the expected nodes
        #
        exp_nodes = self._get_many_two_node_tree_nodes(job_ids, 3)
        nodes_by_desc = {n.description: n for n in nodes}

        for desc in ["leaf-1", "root-1", "leaf-2", "root-2", "leaf-3", "root-3"]:
            self.assertTrue(_node_equals(exp_nodes[desc], nodes_by_desc[desc]))

    def test_one_two_node_tree_jobs(self):
        """
        Test the case when the 'jobs set' is a simple two-node graph,
        with one job depending on another.

        This tests the typical case when we process one dataset.
        """

        js_id, job_ids = self._setup_many_two_node_tree_jobs(1)

        with patch("conf.PROJECTS_DB_DIR", self.projects_db_dir):
            nodes = get_job_nodes(self.project.id, js_id)

        # there should be 6 job nodes
        self.assertEquals(len(nodes), 2)

        #
        # check that we got the expected nodes
        #
        exp_nodes = self._get_many_two_node_tree_nodes(job_ids, 1)
        nodes_by_desc = {n.description: n for n in nodes}

        for desc in ["leaf-1", "root-1"]:
            self.assertTrue(_node_equals(exp_nodes[desc], nodes_by_desc[desc]))


class TestGetRootNodes(TestCase):
    """
    test get_root_nodes()
    """

    def test_one_tree(self):
        nodes = _get_node_trees(1)

        roots = get_root_nodes(nodes)

        # we should get one root node
        self.assertEquals(len(roots), 1)
        self.assertEquals(list(roots)[0].description, "root-1")

    def test_two_trees(self):
        nodes = _get_node_trees(2)

        roots = get_root_nodes(nodes)

        # we should get 2 root nodes
        root_descs = {r.description for r in roots}
        self.assertSetEqual(root_descs, {"root-1", "root-2"})


class TestMarkJobs(ProjectTestCase):
    """
    test mark_job_started() and mark_job_finished()
    """

    def _setup_job(self, started=False):
        db = self.project.db

        with db_session:
            jobs_set = jobs_set = db.JobsSet(description="test")
            job = db.Job(
                jobs_set=jobs_set,
                description="mark",
                program="mark.sh",
                stdout="mark.out",
                stderr="mark.err",
                run_on="hpc",
            )

            if started:
                job.started = datetime.now()

        return job.id

    def _get_node(self, job_id) -> JobNode:
        return JobNode(
            str(self.project.id),
            str(job_id),
            "mark",
            "mark.sh",
            [],
            "mark.out",
            "mark.err",
            0,
            "hpc",
        )

    def test_mark_job_started(self):
        job_id = self._setup_job()

        with patch("conf.PROJECTS_DB_DIR", self.projects_db_dir):
            mark_job_started(self._get_node(job_id))

        with db_session:
            job = self.project.db.Job.get(id=job_id)
            self.assertIsNotNone(job.started)

    def test_mark_job_finished(self):
        job_id = self._setup_job(started=True)

        with patch("conf.PROJECTS_DB_DIR", self.projects_db_dir):
            mark_job_finished(self._get_node(job_id))

        with db_session:
            job = self.project.db.Job.get(id=job_id)
            self.assertIsNotNone(job.started)
            self.assertIsNotNone(job.finished)
