import csv
from fragview import smiles
from fragview.models import Library, Fragment


class FraglibError(Exception):
    def error_message(self):
        return self.args[0]


def save_new_library(lib_name, fragments):
    lib = Library(name=lib_name)
    lib.save()

    for frag_name, smiles_exp in fragments:
        Fragment(library=lib, name=frag_name, smiles=smiles_exp).save()

    return lib


def update_current_library(lib_name, fragments):
    lib = lib_name

    for frag_name, smiles_exp in fragments:
        Fragment(library=lib, name=frag_name, smiles=smiles_exp).save()

    return lib


def _parse_csv(csv_reader):
    fragmens = []
    for row in csv_reader:
        num_cells = len(row)

        if num_cells == 0:
            # skip empty line in CSV
            continue

        if num_cells != 2:
            raise FraglibError(f"unexpected number of cells on a row, expecting 2, got {len(row)}")

        fragname, smiles_exp = row

        if smiles.parse(smiles_exp) is None:
            raise FraglibError(f"invalid SMILES '{smiles_exp}' for fragment '{fragname}'")

        # looks good
        fragmens.append((fragname, smiles_exp))

    return fragmens


def parse_uploaded_file(uploaded_file):
    def _uploaded_lines(uploaded_file):
        """
        split up uploaded file into lines, so we can
        parse django UploadedFile with a call to csv.reader()
        """
        for chunk in uploaded_file.chunks():
            for line in chunk.decode().splitlines():
                yield line

    return _parse_csv(csv.reader(_uploaded_lines(uploaded_file)))
