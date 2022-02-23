from typing import List
from pathlib import Path


def get_ligand_restrains_commands(smiles: str, output: Path) -> List[str]:
    return [
        f"rm -f {output}.cif {output}.pdb",
        f"grade '{smiles}' -ocif {output}.cif -opdb {output}.pdb -nomogul",
    ]
