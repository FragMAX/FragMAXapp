from unittest import TestCase
from jobs.messages import Job
from jobs.jobsd.job_graphs import JobNode, get_root_jobs, get_job_nodes_trees


def equal_job_nodes_sets(set0, set1) -> bool:
    """
    compare two sets of JobNode 'semantically', returns
    true of they are.

    The JobNodes are considered equal if they wraps Jobs with
    the same names.
    """

    sets_len = len(set0)
    if sets_len != len(set1):
        # sets contain different number of elements
        return False

    found_nodes = 0

    #
    # count how many nodes from set0 are
    # also present in set1
    #
    for node0 in set0:
        for node1 in set1:
            if node0.job.name == node1.job.name:
                found_nodes += 1
                continue

    # sets are equals if all elements from set0 are found in set1
    return sets_len == found_nodes


class TestGetJobNodesTrees(TestCase):
    """
    test get_job_nodes_trees() function
    """

    def setUp(self):
        self.job_dicts = []
        self.job_objs = []
        self.job_nodes = set()
        for n in range(3):
            job = dict(
                id=f"{n}",
                project_id="2",
                name=f"job{n}",
                program=f"prog{n}",
                arguments=[],
                run_on="local",
                stdout=f"stdout{n}",
                stderr=f"stderr{n}",
            )
            job_obj = Job.from_dict(job)
            self.job_dicts.append(job)
            self.job_objs.append(job_obj)
            self.job_nodes.add(JobNode(job_obj, "local"))

    def test_no_dependencies(self):
        """
        check the case where jobs have no 'run_after' dependencies
        """
        job_nodes = get_job_nodes_trees("2", self.job_dicts)

        # check the results
        self.assertTrue(equal_job_nodes_sets(job_nodes, self.job_nodes))

    def test_tree(self):
        """
        check the case where job should be run after two other
        jobs are finished
        """

        self.job_dicts[0]["run_after"] = ["1", "2"]

        job_nodes = get_job_nodes_trees("2", self.job_dicts)

        self.assertTrue(equal_job_nodes_sets(job_nodes, self.job_nodes))

        #
        # check 'run_after' dependencies
        #

        # index job nodes by job names
        nodes = {n.job.name: n for n in job_nodes}

        # 'job0' node shoud be run after 'job1' and 'job2'
        self.assertSetEqual(
            set(nodes["job0"].run_after), {nodes["job1"], nodes["job2"]}
        )
        # 'job1' and 'job2' should not have any 'run after' dependencies
        self.assertListEqual(nodes["job1"].run_after, [])
        self.assertListEqual(nodes["job2"].run_after, [])


class TestGetRootJobs(TestCase):
    """
    test get_root_jobs() function
    """

    def setUp(self):
        self.jobs = []
        self.nodes = []
        for n in range(6):
            job = Job(
                f"{n}", "3", f"job{n}", f"prog{n}", [], f"stdout{n}", f"stderr{n}"
            )
            node = JobNode(job, run_on="local")

            self.jobs.append(job)
            self.nodes.append(node)

    def test_flat(self):
        """
        test getting roots from a graph where there are no 'run_after' dependencies,
        i.e. all nodes are roots
        """
        roots = get_root_jobs({self.nodes[2], self.nodes[1], self.nodes[0]})
        self.assertSetEqual(roots, {self.nodes[0], self.nodes[1], self.nodes[2]})

    def test_one_tree(self):
        """
        test getting roots from a graphs which is a single 3 level tree,
        i.e. the graph have one node that is a root
        """
        # build the 3 level tree of job nodes
        parent = self.nodes[0]
        child = self.nodes[1]
        grandkids = [self.nodes[2], self.nodes[3]]

        parent.set_run_after([child])
        child.set_run_after(grandkids)

        # check that we get correct root
        roots = get_root_jobs({parent, child, *grandkids})
        self.assertSetEqual(roots, {parent})

    def test_two_trees(self):
        """
        test the case where the graphs is two separate trees,
        that is, we should get 2 different root nodes
        """
        #
        # first tree, with 2 levels
        #
        root0 = self.nodes[0]
        leafs = [self.nodes[1], self.nodes[2]]

        root0.set_run_after(leafs)

        #
        # second tree, with 3 levels
        #
        root1 = self.nodes[3]
        branch = self.nodes[4]
        leaf = self.nodes[5]

        root1.set_run_after([branch])
        branch.set_run_after([leaf])

        # check that we get correct root
        roots = get_root_jobs({root0, *leafs, root1, branch, leaf})
        self.assertSetEqual(roots, {root0, root1})
