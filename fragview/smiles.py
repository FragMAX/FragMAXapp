from rdkit import Chem
from rdkit.Chem import Draw, AllChem

SVG_WIDTTH = 320
SVG_HEIGHT = 320


def parse(smiles):
    return Chem.MolFromSmiles(smiles)


def to_svg(smiles):
    mol = parse(smiles)

    AllChem.Compute2DCoords(mol)
    mc_mol = Draw.rdMolDraw2D.PrepareMolForDrawing(mol, kekulize=True)

    Drawer = Draw.rdMolDraw2D.MolDraw2DSVG(SVG_WIDTTH, SVG_HEIGHT)
    Drawer.drawOptions().clearBackground = False  # make the SVG transparent
    Drawer.DrawMolecule(mc_mol)
    Drawer.FinishDrawing()

    return Drawer.GetDrawingText()
