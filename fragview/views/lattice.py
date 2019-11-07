from glob import glob
import time
from os import path
import subprocess
from django.shortcuts import render
from fragview.projects import current_project, project_shift_dirs


def reciprocal(request):
    proj = current_project(request)
    dataset = str(request.GET.get('dataHeader'))

    flatlist = [
        y for x in
        [
            glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/{dataset}/dials/DEFAULT/NATIVE/*/index/2_SWEEP*")
            for shift_dir in project_shift_dirs(proj)
        ]
        for y in x]

    state = "new"
    if flatlist != []:
        rlpdir = "/".join(flatlist[0].split("/")[:-1])
        if path.exists(rlpdir + "/rlp.json"):
            rlpdir = "/".join(flatlist[0].split("/")[:-1])
            rlp = rlpdir + "/rlp.json"
            state = "none"
        else:
            cmd = \
                'echo "module load DIALS;cd ' + rlpdir + \
                '; dials.export 2_SWEEP1_datablock.json 2_SWEEP1_strong.pickle format=json" | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(cmd, shell=True)
            rlp = rlpdir + "/rlp.json"
    else:
        rlp = "none2"
    if dataset in rlp:
        timer = 0
        while not path.exists(rlp):
            if timer == 20:
                break
            time.sleep(1)
            timer += 1

    rlp = rlp.replace("/data/visitors/", "/static/")

    return render(
        request,
        "fragview/reciprocal_lattice.html",
        {
            "dataset": dataset, "rlp": rlp, "state": state
        })
