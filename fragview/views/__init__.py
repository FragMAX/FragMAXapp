from django.shortcuts import render
from fragview.projects import current_project
from fragview.projects import project_script
from fragview.projects import project_xml_files
from .utils import scrsplit

import os
import subprocess
import time
import threading
import xmltodict


#############################################

def ligfit_datasets(request):
    userInput=str(request.GET.get("submitligProc"))
    proj=current_project(request)
    empty,rhofitSW,ligfitSW,ligandfile,fitprocess,scanchirals,customligfit,ligfromname,filters=userInput.split(";;")
    useRhoFit="False"
    useLigFit="False"

    if "true" in rhofitSW:
        useRhoFit="True"
    if "true" in ligfitSW:
        useLigFit="True"

    t1 = threading.Thread(target=autoLigandFit, args=(request, useLigFit, useRhoFit, proj.library, filters))
    t1.daemon = True
    t1.start()
    return render(request,'fragview/ligfit_datasets.html', {'allproc': "<br>".join(userInput.split(";;"))})

def dataproc_datasets(request):
    proj = current_project(request)

    allprc  = str(request.GET.get("submitallProc"))
    dtprc   = str(request.GET.get("submitdtProc"))
    if allprc!="None":
        userinputs=allprc.split(";;")
        dpSW=list()
        dpSW.append("xdsapp")    if ("true" in userinputs[3]) else False
        dpSW.append("xdsxscale") if ("true" in userinputs[2]) else False
        dpSW.append("dials")     if ("true" in userinputs[1]) else False
        dpSW.append("autoproc")  if ("true" in userinputs[4]) else False
        if dpSW==[]:
            dpSW=[""]

        rfSW=list()
        rfSW.append("dimple")     if ("true" in userinputs[12]) else False
        rfSW.append("fspipeline") if ("true" in userinputs[13]) else False
        rfSW.append("buster")     if ("true" in userinputs[14]) else False
        if rfSW==[]:
            rfSW=[""]

        lfSW=list()
        lfSW.append("rhofit") if ("true" in userinputs[19]) else False
        lfSW.append("ligfit") if ("true" in userinputs[20]) else False
        if lfSW==[]:
            lfSW=[""]

        PDBID=userinputs[18].split(":")[-1]

        spg=userinputs[5].split(":")[-1]
        pnodes=10
        shell_script = project_script(proj, "processALL.sh")
        with open(shell_script, "w") as outp:
            outp.write("""#!/bin/bash \n"""
                    """#!/bin/bash \n"""
                    """#SBATCH -t 99:55:00 \n"""
                    """#SBATCH -J FragMAX \n"""
                    """#SBATCH --exclusive \n"""
                    """#SBATCH -N1 \n"""
                    """#SBATCH --cpus-per-task=40 \n"""
                    """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/analysis_workflow_%j_out.txt \n"""
                    """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/analysis_workflow_%j_err.txt \n"""
                    """module purge \n"""
                    """module load DIALS CCP4 autoPROC BUSTER XDSAPP PyMOL \n"""
                    """python """ + project_script(proj, "processALL.py") + """ '""" + proj.data_path() + """' '""" + \
                       proj.library + """' '""" + PDBID+"""' '""" + spg+"""' $1 $2 '""" + ",".join(dpSW) + \
                       """' '""" + ",".join(rfSW) + """' '""" + ",".join(lfSW) + """' \n""")
        for node in range(pnodes):
            command ='echo "module purge | module load CCP4 autoPROC DIALS XDSAPP | sbatch ' + \
                     shell_script + " "+str(node)+" "+str(pnodes)+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)
            time.sleep(0.2)
        return render(request,'fragview/testpage.html', {
            'dpSW': "<br>".join(dpSW),
            'rfSW': "<br>".join(rfSW),
            'lfSW': "<br>".join(lfSW),
            "pdb":PDBID,
            "sym":spg
            })
    if dtprc!="None":
        dtprc_inp=dtprc.split(";")
        usedials=dtprc_inp[1].split(":")[-1]
        usexdsxscale=dtprc_inp[2].split(":")[-1]
        usexdsapp=dtprc_inp[3].split(":")[-1]
        useautproc=dtprc_inp[4].split(":")[-1]
        spacegroup=dtprc_inp[5].split(":")[-1]
        cellparam=dtprc_inp[6].split(":")[-1]
        friedel=dtprc_inp[7].split(":")[-1]
        datarange=dtprc_inp[8].split(":")[-1]
        rescutoff=dtprc_inp[9].split(":")[-1]
        cccutoff=dtprc_inp[10].split(":")[-1]
        isigicutoff=dtprc_inp[11].split(":")[-1]
        filters=dtprc_inp[-1].split(":")[-1]
        sbatch_script_list=list()
        nodes=3
        if filters!="ALL":
            nodes=1
        if usexdsapp=="true":
            t = threading.Thread(target=run_xdsapp, args=(proj, nodes, filters))
            t.daemon = True
            t.start()
        if usedials=="true":
            t = threading.Thread(target=run_dials, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        if useautproc=="true":
            t = threading.Thread(target=run_autoproc, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        if usexdsxscale=="true":
            t = threading.Thread(target=run_xdsxscale, args=(proj, nodes, filters))
            t.daemon = True
            t.start()

        return render(request,'fragview/dataproc_datasets.html', {'allproc': "Jobs submitted using "+str(nodes)+" per method"})



    return render(request,'fragview/dataproc_datasets.html', {'allproc': ""})

##############################################


def run_xdsapp(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J XDSAPP\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/xdsapp_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/xdsapp_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDSAPP\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]

        script="cd "+outdir+"/xdsapp\n"
        script+='xdsapp --cmd --dir='+outdir+'/xdsapp -j 8 -c 5 -i '+h5master+' --delphi=10 --fried=True --range=1\ '+nImg+' \n\n'
        scriptList.append(script)
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        os.makedirs(outdir+"/xdsapp",mode=0o760, exist_ok=True)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]
    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsapp_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        command ='echo "module purge | module load CCP4 XDSAPP DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
        print(f"running command '{command}'")

def run_autoproc(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J autoPROC\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/autoproc_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/autoproc_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load CCP4 autoPROC\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        script="cd "+outdir+"\n"
        script+='''process -h5 '''+h5master+''' -noANO autoPROC_Img2Xds_UseXdsPlugins_DectrisHdf5="durin-plugin" autoPROC_XdsKeyword_LIB=\$EBROOTNEGGIA/lib/dectris-neggia.so autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=5 autoPROC_XdsKeyword_DATA_RANGE=1\ '''+nImg+''' autoPROC_XdsKeyword_SPOT_RANGE=1\ '''+nImg+''' -d '''+outdir+'''/autoproc\n\n'''
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]

    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"autoproc_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)
        command ='echo "module purge | module load CCP4 autoPROC DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_xdsxscale(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""


    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J xdsxscale\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH --mem-per-cpu=2000\n"""
    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/xdsxscale_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/xdsxscale_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load PReSTO\n\n"""

    scriptList=list()

    with open(project_script(proj, "filter.txt"), "w") as inp:
        inp.write(filters)

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        os.makedirs(outdir+"/xdsxscale",mode=0o760, exist_ok=True)


        script="cd "+outdir+"/xdsxscale \n"
        script+="xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true  nproc=40 image="+h5master+":1:"+nImg+" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n\n"
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]


    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"xdsxscale_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        command ='echo "module purge | module load CCP4 XDSAPP DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_dials(proj, nodes, filters):
    if "filters:" in filters:
        filters=filters.split(":")[-1]

    if filters=="ALL":
        filters=""

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J DIALS\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n"""
    header+= """#SBATCH --mem-per-cpu=2000\n"""

    header+= """#SBATCH -o """ + proj.data_path() + """/fragmax/logs/dials_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """ + proj.data_path() + """/fragmax/logs/dials_fragmax_%j_err.txt\n"""
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDS DIALS\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in xml_files:
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
        os.makedirs(outdir+"/dials",mode=0o760, exist_ok=True)


        script="cd "+outdir+"/dials \n"
        script+="xia2 goniometer.axes=0,1,0 pipeline=dials failover=true  nproc=40 image="+h5master+":1:"+nImg+" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n\n"
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]


    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)

        script = project_script(proj, f"dials_fragmax_part{num}.sh")
        with open(script, "w") as outfile:
            outfile.write(chunk)

        command ='echo "module purge | module load CCP4 XDSAPP DIALS | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)


def autoLigandFit(request, useLigFit,useRhoFit,fraglib,filters):
    #proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions(request)
    proj = current_project(request)

    if "filters:" in filters:
        filters=filters.split(":")[-1]
    if filters=="ALL":
        filters=""
    with open(proj.data_path()+"/fragmax/scripts/autoligand.py","w") as writeFile:
        writeFile.write('''import multiprocessing\n'''
                '''import time\n'''
                '''import subprocess\n'''
                '''import sys\n'''
                '''import glob\n'''
                '''import os\n'''
                '''path="'''+proj.data_path()+'''"\n'''
                '''fraglib="'''+proj.library+'''"\n'''
                '''acr="'''+proj.protein+'''"\n'''
                '''shiftList="'''+proj.shift_list+'''"\n'''
                '''fitmethod=sys.argv[4]\n'''
                '''pdbList=list()\n'''
                '''shiftList=shiftList.split(",")\n'''
                '''for s in shiftList:\n'''
                '''    p="/data/visitors/biomax/'''+proj.proposal+'''/"+s\n'''
                '''    pdbList+=glob.glob(p+"/fragmax/results/"+acr+"*/*/*/final.pdb")\n'''
                '''pdbList=[x for x in pdbList if "Apo" not in x and "'''+filters+'''" in x]\n'''
                '''cifList=list()\n'''
                '''mtzList=[x.replace(".pdb",".mtz") for x in pdbList]\n'''
                '''outListR=[x.replace("final.pdb","rhofit/") for x in pdbList]\n'''
                '''outListP=[x.replace("final.pdb","ligfit/") for x in pdbList]\n'''
                '''for i in pdbList:\n'''
                '''    fragID=i.split("/")[8].split("-")[-1].split("_")[0]\n'''
                '''    cifList.append(path+"/fragmax/process/fragment/"+fraglib+"/"+fragID+"/"+fragID+".cif")\n'''
                '''inpdataR=list()\n'''
                '''inpdataP=list()\n'''
                '''for a,b,c,d in zip(cifList,mtzList,pdbList,outListR):\n'''
                '''    inpdataR.append([a,b,c,d])\n'''
                '''for a,b,c,d in zip(cifList,mtzList,pdbList,outListP):\n'''
                '''    inpdataP.append([a,b,c,d])\n'''
                '''def fit_worker((cif, mtz, pdb, out)):\n'''
                '''    if fitmethod=="rhofit":\n'''
                '''        if os.path.exists(out):\n'''
                '''            os.system("rm -rf "+out)\n'''
                '''        command="rhofit -l %s -m %s -p %s -d %s" %(cif, mtz, pdb, out)\n'''
                '''        subprocess.call(command, shell=True) \n'''
                '''    if fitmethod=="ligfit":\n'''
                '''        out="/".join(out.split("/")[:-1])\n'''
                '''        if not os.path.exists(out):\n'''
                '''            os.makedirs(out)\n'''
                '''            command="cd %s && phenix.ligandfit data=%s model=%s ligand=%s fill=True clean_up=True" %(out,mtz, pdb, cif)    \n'''
                '''            subprocess.call(command, shell=True) \n'''
                '''def mp_handler():\n'''
                '''    p = multiprocessing.Pool(48)\n'''
                '''    if fitmethod=="ligfit":\n'''
                '''        p.map(fit_worker, inpdataP)\n'''
                '''    if fitmethod=="rhofit":\n'''
                '''        p.map(fit_worker, inpdataR)\n'''
                '''if __name__ == '__main__':\n'''
                '''    mp_handler()\n''')





    script=proj.data_path()+"/fragmax/scripts/autoligand.sh"
    if "True" in useRhoFit:
        with open(proj.data_path()+"/fragmax/scripts/autoligand.sh","w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                    '''#!/bin/bash\n'''
                    '''#SBATCH -t 99:55:00\n'''
                    '''#SBATCH -J autoRhofit\n'''
                    '''#SBATCH --exclusive\n'''
                    '''#SBATCH -N1\n'''
                    '''#SBATCH --cpus-per-task=48\n'''
                    '''#SBATCH -o '''+proj.data_path()+'''/fragmax/logs/auto_rhofit_%j_out.txt\n'''
                    '''#SBATCH -e '''+proj.data_path()+'''/fragmax/logs/auto_rhofit_%j_err.txt\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+proj.data_path()+'''/fragmax/scripts/autoligand.py '''+proj.data_path()+''' '''+proj.library+''' '''+proj.protein+''' rhofit\n''')
        command ='echo "module purge | module load BUSTER CCP4 | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
    if "True" in useLigFit:
        with open(proj.data_path()+"/fragmax/scripts/autoligand.sh","w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                    '''#!/bin/bash\n'''
                    '''#SBATCH -t 3:00:00\n'''
                    '''#SBATCH -J autoLigfit\n'''
                    '''#SBATCH --exclusive\n'''
                    '''#SBATCH -N1\n'''
                    '''#SBATCH --cpus-per-task=48\n'''
                    '''#SBATCH -o '''+proj.data_path()+'''/fragmax/logs/auto_ligfit_%j_out.txt\n'''
                    '''#SBATCH -e '''+proj.data_path()+'''/fragmax/logs/auto_ligfit_%j_err.txt\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+proj.data_path()+'''/fragmax/scripts/autoligand.py '''+proj.data_path()+''' '''+proj.library+''' '''+proj.protein+''' ligfit\n''')
        command ='echo "module purge | module load CCP4 Phenix | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)


def split_b(target,ini,end):
    return target.split(ini)[-1].split(end)[0]
