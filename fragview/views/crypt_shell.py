from pathlib import Path
from fragview import tokens
from fragview.projects import project_script, project_fragmax_dir
from django.conf import settings


def crypt_cmd(proj):
    if not proj.encrypted:
        return ""

    crypt_files = project_script(proj, "crypt_files.sh")
    token = tokens.get_valid_token(proj)
    return f"CRYPT_CMD='{crypt_files} {settings.CRYPT_URL} {token.as_base64()}'"


def fetch_file(proj, src_file, dest_file):
    if not proj.encrypted:
        return f"cp {src_file} {dest_file}"

    return f"$CRYPT_CMD fetch {src_file} {dest_file}"


def upload_dir(proj, res_dir):
    cmd = "rm $WORK_DIR/model.pdb\n"

    if proj.encrypted:
        cmd += f"$CRYPT_CMD upload_dir $WORK_DIR {res_dir}\n"
        return cmd

    # project is in unencrypted mode
    if not res_dir.startswith(project_fragmax_dir(proj)):
        # refuse to do any 'rm -rf' outside of project's fragmax directory
        raise Exception(f"{res_dir} outside of project directory")

    parent_dir = Path(res_dir).parent

    cmd += f"rm -rf {res_dir}\n" + \
           f"mkdir -p {parent_dir}\n" + \
           f"cp -r $WORK_DIR {res_dir}\n"

    return cmd
