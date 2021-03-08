from django.test import TestCase
from fragview.models import Project, Library, Fragment
from fragview.views.ligfit import get_fragment_smiles


class TestGetFragmentSmiles(TestCase):
    """
    test that we can parse out fragment ID (and fetch correct SMILES)
    from different styles of dataset names
    """

    def setup_project(self, protein, library, frags):
        lib = Library(name=library)
        lib.save()

        for frag, smiles in frags.items():
            Fragment(library=lib, name=frag, smiles=smiles).save()

        proj = Project(
            protein=protein, library=lib, proposal="20180201", shift="20190808",
        )
        proj.save()

        return proj

    def test_hCAII(self):
        proj = self.setup_project(
            "hCAII", "FMLv03", {"E02b2": "CE02b2", "A01a": "CA01a"}
        )

        frag_id, smiles = get_fragment_smiles(proj, "hCAII-E02b2_2")
        self.assertEqual(frag_id, "E02b2")
        self.assertEqual(smiles, "CE02b2")

        frag_id, smiles = get_fragment_smiles(proj, "hCAII-FMLv03-A01a_1")
        self.assertEqual(frag_id, "A01a")
        self.assertEqual(smiles, "CA01a")

    def test_ARwoDMSO(self):
        proj = self.setup_project("ARwoDMSO", "F2XEntry", {"A07a": "CA07a"})

        frag_id, smiles = get_fragment_smiles(proj, "ARwoDMSO-F2XEntry-A07a_1")
        self.assertEqual(frag_id, "A07a")
        self.assertEqual(smiles, "CA07a")

    def test_FF(self):
        proj = self.setup_project("FF", "F2XEntry", {"F02a": "CF02a"})

        frag_id, smiles = get_fragment_smiles(proj, "FF-F2XEntry-F02a_1")
        self.assertEqual(frag_id, "F02a")
        self.assertEqual(smiles, "CF02a")
