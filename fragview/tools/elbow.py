from typing import List
from pathlib import Path


def get_ligand_restrains_commands(smiles: str, output: Path) -> List[str]:
    return [f"phenix.elbow --smiles='{smiles}' --output={output}"]
