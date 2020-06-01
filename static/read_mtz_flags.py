#!/mxn/groups/biomax/wmxsoft/ccp4-fragmax/ccp4-7.0/bin/ccp4-python
from __future__ import print_function
from iotbx.reflection_file_reader import any_reflection_file
from sys import argv


mtz = argv[1]

hkl_in = any_reflection_file(file_name=mtz)

miller_arrays = hkl_in.as_miller_arrays()

for ma in miller_arrays[::-1]:
    flags = ma.info()
    if "SIGF" in str(flags):
        F_SIGF_flags = flags
r_free_flags = miller_arrays[1].info()
# F_SIGF_flags=miller_arrays[2].info()

print(r_free_flags, F_SIGF_flags)
