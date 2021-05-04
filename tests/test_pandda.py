from unittest import TestCase
from fragview.pandda import Inspects, Inspect
from tests.utils import TempDirMixin


class TestInspects(TestCase, TempDirMixin):
    def setUp(self):
        self.setup_temp_dir()

    def tearDown(self):
        self.tear_down_temp_dir()

    def test_find(self):
        """
        test Inspects.find() method
        """
        method = "some_meth"
        ds01 = Inspect("DS001", method, "1", "3")
        ds04 = Inspect("DS004", method, "1", "1")
        ds09 = Inspect("DS009", method, "1", "4")
        ds12 = Inspect("DS012", method, "4", "3")

        #
        # create inspects.csv file
        #
        inspects = Inspects()
        inspects.add(ds01)
        inspects.add(ds04)
        inspects.add(ds09)
        inspects.add(ds12)
        inspects.save(self.temp_dir)

        #
        # test looking up previous and next inspects
        #

        # look-up dataset 1
        prev, next = Inspects.find(self.temp_dir, ds01)
        self.assertIsNone(prev)
        self.assertEquals(next, ds04)

        # look-up dataset 4
        prev, next = Inspects.find(self.temp_dir, ds04)
        self.assertEquals(prev, ds01)
        self.assertEquals(next, ds09)

        # look-up dataset 9
        prev, next = Inspects.find(self.temp_dir, ds09)
        self.assertEquals(prev, ds04)
        self.assertEquals(next, ds12)

        # look-up dataset 12
        prev, next = Inspects.find(self.temp_dir, ds12)
        self.assertEquals(prev, ds09)
        self.assertIsNone(next)
