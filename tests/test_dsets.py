from unittest import TestCase
from fragview.dsets import (
    parse_master_h5_path,
    DataSet,
    DataSetStatus,
)


class TestParseMasterH5Path(TestCase):
    """
    test parse_master_h5_path() function
    """

    def _check(self, file_path, expected_sample, expected_run):
        sample, run = parse_master_h5_path(file_path)
        self.assertEqual(sample, expected_sample)
        self.assertEqual(run, expected_run)

    def test_func(self):
        self._check(
            "/data/visitors/biomax/20200593/20210223/raw/Nsp10/Nsp10-RGD201024/Nsp10-RGD201024_2_master.h5",
            "Nsp10-RGD201024",
            "2",
        )

        self._check(
            "/data/visitors/biomax/20200593/20201106/raw/Nsp10/Nsp10-VT00191/Nsp10-VT00191_1_master.h5",
            "Nsp10-VT00191",
            "1",
        )

        self._check(
            "/data/visitors/biomax/20200593/20200628/raw/Nsp10/Nsp10-361_4e_2_s11/Nsp10-361_4e_2_s11_1_master.h5",
            "Nsp10-361_4e_2_s11",
            "1",
        )


class TestDataSet(TestCase):
    """
    test DataSet class
    """

    def _create_data_set(self, sample_name):
        return DataSet(
            "img_prefix",
            sample_name,
            "/dummy/path",
            "Nsp5",
            "1",
            "900",
            "1.70",
            "/some/snap.jpeg",
            DataSetStatus(),
        )

    def test_is_apo(self):
        """
        check DataSet.is_apo() method
        """
        data_set = self._create_data_set("apo2")
        self.assertTrue(data_set.is_apo())

        data_set = self._create_data_set("Apo42")
        self.assertTrue(data_set.is_apo())

        data_set = self._create_data_set("SBX17106")
        self.assertFalse(data_set.is_apo())
