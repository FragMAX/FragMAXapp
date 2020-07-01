from os import path
import shutil
from pathlib import Path
from fragview.projects import proposal_dir, project_process_protein_dir
from fragview.fileio import makedirs


def copy_collection_metadata_files(proj, meta_files):
    def _sample_shift_name(meta_file_path):
        path_parts = Path(meta_file_path).parts
        samle = path_parts[prop_dir_depth + 4][4:-2]

        return path_parts[prop_dir_depth + 3], f"{samle}.xml"

    prop_dir = proposal_dir(proj.proposal)
    prop_dir_depth = len(Path(prop_dir).parts)
    proto_dir = project_process_protein_dir(proj)

    for mfile in meta_files:
        sample_dir, sample_filename = _sample_shift_name(mfile)

        dest_dir = path.join(proto_dir, sample_dir)
        dest_file = path.join(dest_dir, sample_filename)

        makedirs(dest_dir)
        shutil.copyfile(mfile, dest_file)
