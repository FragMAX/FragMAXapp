from typing import List
from pathlib import Path


def get_ligand_restrains_commands(smiles: str, output: Path) -> List[str]:
    return [f"acedrg -i '{smiles}' -o {output}"]
