from pathlib import Path


def get_ligand_restrains_commands(smiles: str, output: Path) -> list[str]:
    return [f"acedrg --smi='{smiles}' --out={output}"]
