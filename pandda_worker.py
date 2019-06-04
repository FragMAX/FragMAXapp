import os 
import glob
import sys
import subprocess 
import shutil
import multiprocessing 
path=sys.argv[1]
method=sys.argv[2]
acr=sys.argv[3]
fraglib=sys.argv[4]
def prepare_pandda_files(method):
    proc,ref=method.split("_")
    missing=list()
    optionsDict=dict()
    copypdb=dict()
    copymtz=dict()
    copylig=dict()
    copycif=dict()
    datasets=sorted([x.split("/")[-2] for x in glob.glob(path+"/raw/"+acr+"/*/*master.h5") if "ref-" not in x])
    refresults=sorted([x for x in glob.glob(path+"/fragmax/results/*/*/*/final*.pdb" ) if "/pandda/" not in x])
    selected=sorted([x for x in refresults if proc in x and ref in x and acr in x])
    for i in datasets:
        for j in selected:
            if i in j:
                missing.append(i)
    missing=list(set(datasets)-set(missing))
    for i in missing:
        options=list()
        for j in refresults:
            if i in j:
                options.append(j)
        if len(options)>0:
            optionsDict[i]=options
    for key,value in optionsDict.items():  
        for opt in value:             
            if "xdsapp" in opt or "dials" in opt or "autoproc" in opt:
                selected.append(opt)
                break            
    for i in selected:
        a=i.split(acr)[0]+"pandda/"+"_".join(i.split("/")[-3:-1])+"/"+i.split("/")[8]+"/final.pdb"
        copypdb[i]=a
        copymtz[i.replace(".pdb",".mtz")]=a.replace(".pdb",".mtz")
        b=i.split(acr+"-")[1].split("_")[0]
        if "Apo" not in b:
            copylig[path+"/fragmax/process/fragment/"+fraglib+"/"+b+"/"+b+".pdb"]="/".join(a.split("/")[:-1])+"/"+b+".pdb"
            copycif[path+"/fragmax/process/fragment/"+fraglib+"/"+b+"/"+b+".cif"]="/".join(a.split("/")[:-1])+"/"+b+".cif"
    for src,dst in copypdb.items():
        if not os.path.exists(dst):
            if not os.path.exists("/".join(dst.split("/")[:-1])):
                os.makedirs("/".join(dst.split("/")[:-1]))            
            shutil.copyfile(src,dst)
    for src,dst in copymtz.items():
        if not os.path.exists(dst):
            if not os.path.exists("/".join(dst.split("/")[:-1])):
                os.makedirs("/".join(dst.split("/")[:-1]))
            shutil.copyfile(src,dst)
    for src,dst in copylig.items():
        if not os.path.exists(dst):
            if not os.path.exists("/".join(dst.split("/")[:-1])):
                os.makedirs("/".join(dst.split("/")[:-1]))
            shutil.copyfile(src,dst)
    for src,dst in copycif.items():
        if not os.path.exists(dst):
            if not os.path.exists("/".join(dst.split("/")[:-1])):
                os.makedirs("/".join(dst.split("/")[:-1]))
            shutil.copyfile(src,dst)
def pandda_run(method):
    os.chdir(path+"/fragmax/results/pandda/"+method)
    command="pandda.analyse data_dirs='"+path+"/fragmax/results/pandda/"+method+"/*' cpus=32"
    subprocess.call(command, shell=True)
    if len(glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/logs/*.log"))>0:
        lastlog=sorted(glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/logs/*.log"))[-1]
        with open(lastlog,"r") as logfile:
            log=logfile.readlines()
        badDataset=dict()
        for line in log:
            if "Structure factor column"  in line:
                bd=line.split(" has ")[0].split("in dataset ")[-1]        
                bdpath=glob.glob(path+"/fragmax/results/pandda/"+method+"/"+bd+"*")
                badDataset[bd]=bdpath
            if "Failed to align dataset" in line:
                bd=line.split("Failed to align dataset ")[1].rstrip()
                bdpath=glob.glob(path+"/fragmax/results/pandda/"+method+"/"+bd+"*")
                badDataset[bd]=bdpath
        for k,v in badDataset.items():
            if len(v)>0:
                if os.path.exists(v[0]):
                    if os.path.exists(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k):
                        shutil.rmtree(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k)
                        shutil.move(v[0], path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k)
                pandda_run(method)
def fix_symlinks(method):
    linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")
    for i in linksFolder:        
        folder="/".join(i.split("/")[:-1])+"/"
        pdbs=os.listdir(folder)
        pdb=folder+sorted([x for x in pdbs if "fitted" in x])[-1]        
        shutil.move(i,i+".bak")
        shutil.copyfile(pdb,i)
def CAD_worker(mtzfile):
    stdout = subprocess.Popen('phenix.mtz.dump '+mtzfile, shell=True, stdout=subprocess.PIPE).stdout
    output = stdout.read().decode("utf-8")
    for line in output.split("\n"):
        if "Resolution range" in line:
            highres=line.split()[-1]
    if "free" in "".join(output).lower():
        for line in output.split("\n"):
            if "free" in line.lower():
                freeRflag=line.split()[0]
    else:  
        freeRflag="R-free-flags"        
    outmtz=mtzfile.split("final.mtz")[0]+"final.mtz"    
    os.chdir(mtzfile.replace("/results/","/process/").replace("final.mtz",""))       
    subprocess.call("uniqueify -f "+freeRflag+" "+mtzfile+" "+mtzfile.replace("/results/","/process/"),shell=True)
    cadCommand="""cad hklin1 """+mtzfile+ """ hklout """ +outmtz+ """ <<eof
 monitor BRIEF
 labin file 1 - 
  ALL"
 resolution file 1 999.0 """+ highres+"""
eof"""
    subprocess.call(cadCommand,shell=True)
    subprocess.call("phenix.maps "+mtzfile.replace(".mtz",".pdb")+" "+mtzfile,shell=True    )
    subprocess.call("mv -f "+mtzfile.replace("final.mtz","final_2mFo-DFc_map.ccp4 ")+" "+mtzfile.replace(".mtz",".ccp4"),shell=True)
    subprocess.call("mv -f "+mtzfile.replace("final.mtz","final_map_coeffs.mtz"    )+" "+mtzfile,shell=True)
    return mtzfile, highres, freeRflag
def run_CAD():    
    dataPaths=glob.glob(path+"/fragmax/results/pandda/"+method+"/*/final.mtz")
    for key in dataPaths:
        if not os.path.exists(key.replace("/results/","/process/").replace("final.mtz","")):
            os.makedirs(key.replace("/results/","/process/").replace("final.mtz",""))            
    nproc=multiprocessing.cpu_count()
    multiprocessing.Pool(nproc).map(CAD_worker, dataPaths)    
prepare_pandda_files(method)
run_CAD()
pandda_run(method)
fix_symlinks(method)
