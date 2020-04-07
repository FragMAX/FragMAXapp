from django.urls import reverse
from django.test import TestCase
from tests.utils import ViewTesterMixin
from fragview.models import Fragment
from xml.etree import ElementTree


class TestSvg(TestCase, ViewTesterMixin):
    """
    test the view that generates SVG graphics for a fragment
    """
    def setUp(self):
        self.setup_client()
        self.setup_project()

    def _assert_svg(self, svg_xml):
        """
        smoke test to check that provided svg_xml is valid SVG image
        """
        # check that it seems to be valid XML
        root = ElementTree.fromstring(svg_xml)

        # check that root element is 'SVG'
        self.assertEqual(root.tag[-3:], "svg")

    def test_frag_not_found(self):
        """
        test the case when fragment is not found
        """
        resp = self.client.get(reverse("fragment_svg", args=("None",)))
        self.assertEqual(404, resp.status_code)

    def test_frag_svg(self):
        """
        check that we can generate valid SVG for a simple fragment
        """
        frag = Fragment(library=self.lib, name="F1", smiles="C")
        frag.save()

        resp = self.client.get(reverse("fragment_svg", args=(frag.name,)))

        self.assertEqual(200, resp.status_code)
        self.assertEqual(resp["Content-Type"], "image/svg+xml")
        self._assert_svg(resp.content)
