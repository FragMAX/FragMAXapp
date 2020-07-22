from fragview import tokens
from fragview.projects import project_script, project_fragmax_dir
from django.conf import settings


def crypt_cmd(proj):
    if not proj.encrypted:
        return ""

    crypt_files = project_script(proj, "crypt_files.sh")
    token = tokens.get_valid_token(proj)
    return f"CRYPT_CMD='{crypt_files} {settings.CRYPT_URL} {token.as_base64()}'\n"


def fetch_file(proj, src_file, dest_file):
    if not proj.encrypted:
        return f"cp {src_file} {dest_file}"

    return f"$CRYPT_CMD fetch {src_file} {dest_file}"


def fetch_dir(proj, src, dest):
    if not proj.encrypted:
        return f"cp -vr {src}/* {dest}"

    return f"$CRYPT_CMD fetch_dir {src} {dest}"


def upload_dir(proj, src_dir, res_dir):
    if proj.encrypted:
        return f"$CRYPT_CMD upload_dir {src_dir} {res_dir}\n"

    # project is in unencrypted mode
    if not res_dir.startswith(project_fragmax_dir(proj)):
        # refuse to do any 'rm -rf' outside of project's fragmax directory
        raise Exception(f"{res_dir} outside of project directory")

    return f"rsync -r {src_dir}/* {res_dir}\n"
