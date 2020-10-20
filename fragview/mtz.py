import gemmi
from fragview.fileio import temp_decrypted

# expected Free-R-flag column labels
FREE_R_FLAG = ["FreeR_flag", "R-free-flags"]
# expected native F column labels
NATIVE_F = ["F", "FP", "F-obs", "F-obs-filtered"]
# expected Sigma(F) column labels
SIGMA_FP = ["SIGF", "SIGFP", "SIGF-obs", "SIGF-obs-filtered"]


def _get_column_labels(mtz):
    """
    try to guess the labels for Free-R-flag, native F and Sigma(F) columns
    """

    def is_label(known_label, new_label, expected_labels):
        """
        check if specified new_label against expected labels,
        and pick first match, if any
        """
        if known_label is not None:
            return known_label

        for exp_label in expected_labels:
            if new_label == exp_label:
                return exp_label

    #
    # guess column labels by looking at MTZ's labels
    # and checking if they match any of expected labels
    # for respective column type, yeah, very robust...
    #
    free_r_flag = None
    native_f = None
    sigma_fp = None

    for label in mtz.column_labels():
        free_r_flag = is_label(free_r_flag, label, FREE_R_FLAG)
        native_f = is_label(native_f, label, NATIVE_F)
        sigma_fp = is_label(sigma_fp, label, SIGMA_FP)

    res_labels = [free_r_flag, native_f, sigma_fp]
    if None in res_labels:
        raise Exception("could not determine MTZ column(s) label")

    return res_labels


def read_info(proj, mtz_file):
    """
    get high resolution and labels for Free-R-flag, native F and Sigma(F)
    columns from the specified MTZ file
    """
    with temp_decrypted(proj, mtz_file) as fpath:
        mtz = gemmi.read_mtz_file(fpath)

    return (mtz.resolution_high(), *_get_column_labels(mtz))
