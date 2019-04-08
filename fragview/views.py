from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from django.utils import timezone
from .models import Post
from .forms import PostForm
from difflib import SequenceMatcher

import glob
import os
import random
import natsort
import shutil
import pyfastcopy
import subprocess
import h5py
import itertools
from time import sleep
import threading
import pypdb
import ast
import sys 
from subprocess import Popen, PIPE






################################
#User specific data
#Changing this parameters for different projects based on user credentials
#acr="hCAII"
#proposal="20180489"
#shift="20190127"


setfile="/mxn/home/guslim/Projects/webapp/static/projectSettings/.settings"

def project_definitions():
    proposal = ""
    shift    = ""
    acronym  = ""
    proposal_type = ""
    with open(setfile,"r") as inp:
        prjset=inp.readlines()[0]

    proposal = prjset.split(";")[1].split(":")[-1]
    shift    = prjset.split(";")[2].split(":")[-1]    
    acronym  = prjset.split(";")[3].split(":")[-1]    
    proposal_type = prjset.split(";")[4].split(":")[-1].replace("\n","") 


    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
    static_datapath="/static/biomax/"+proposal+"/"+shift
    panddaprocessed="/fragmax/results/pandda/pandda/processed_datasets/"
    fraglib="F2XEntry"

    

    
    return proposal, shift, acronym, proposal_type, path, subpath, static_datapath,panddaprocessed,fraglib


proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

if len(proposal)<7 or len(shift)<7 or len(acr)<2 or len(proposal_type)<5:
    acr="ProteinaseK"
    proposal="20180479"
    shift="20190323"
    proposal_type="visitors"
    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
    static_datapath="/static/biomax/"+proposal+"/"+shift
    panddaprocessed="/fragmax/results/pandda/pandda/processed_datasets/"

################################

def index(request):
    return render(request, "fragview/index.html")

def process_all(request):
    return render(request, "fragview/process_all.html",{"acronym":acr})

def settings(request):
    allprc  = str(request.GET.get("updatedefinitions"))
    status = "not updated"
    if ";" in allprc:  
    
        with open(setfile,"w") as outsettings:
            outsettings.write(allprc)
        status="updated"
    else:
        status="No update"
    return render(request, "fragview/settings.html",{"upd":status})

def pipedream(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()   

    datasetPathList=glob.glob(path+"/raw/"+acr+"/*/*master.h5")
    datasetPathList=natsort.natsorted(datasetPathList)
    datasetNameList= [i.split("/")[-1].replace("_master.h5","") for i in datasetPathList]
    datasetList=zip(datasetPathList,datasetNameList)
    return render(request, "fragview/pipedream.html",{"data":datasetList})

def pipedream_results(request):

    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()   

    #resync=str(request.GET.get("resync"))
    #if "resyncresults" in resync:
    #    resultSummary()
    #if not os.path.exists(path+"/fragmax/process/generalrefsum.csv"):
    #    resultSummary()
    #try:
    #    with open(path+"/fragmax/process/generalrefsum.csv","r") as inp:
    #        a=inp.readlines()
    #    return render_to_response('fragview/results.html', {'files': a})
    #except:
    #    return render_to_response('fragview/results_notready.html')

    return render(request, "fragview/pipedream_results.html")

def submit_pipedream(request):

    #Function definitions
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    ppdCMD=str(request.GET.get("ppdform"))
    empty,input_data, ap_spacegroup, ap_cellparam,ap_staraniso,ap_xbeamcent,ap_ybeamcent,ap_datarange,ap_rescutoff,ap_highreslim,ap_maxrpim,ap_mincomplet,ap_cchalfcut,ap_isigicut,ap_custompar,b_userPDBfile,b_userPDBcode,b_userMTZfile,b_refinemode,b_MRthreshold,b_chainsgroup,b_bruteforcetf,b_reslimits,b_angularrf,b_sideaiderefit,b_sideaiderebuild,b_pepflip,b_custompar,rho_ligandsmiles,rho_ligandcode,rho_ligandfromname,rho_copiestosearch,rho_keepH,rho_allclusters,rho_xclusters,rho_postrefine,rho_occuprefine,rho_fittingproc,rho_scanchirals,rho_custompar,extras = ppdCMD.split(";;")

    #variables init
    ligand="none"
    ppdoutdir="none"
    ppd="INITVALUE"
    userPDB="NoPDB"
    pdbchains="A"
    userPDBpath=""
    #Select one dataset or entire project
    if "alldatasets" not in input_data:
        input_data=input_data.replace("input_data:","")
        ppdoutdir=input_data.replace("/raw/","/fragmax/process/pipedream/").replace("_master.h5","")
        os.makedirs("/".join(ppdoutdir.split("/")[:-1]),exist_ok=True)
        if os.path.exists(ppdoutdir):
            try:
                int(ppdoutdir[-1])
            except ValueError:
                run="1"
            else:
                run=str(int(ppdoutdir[-1])+1)
            

            ppdoutdir=ppdoutdir+"_run"+run
        
        if len(b_userPDBcode.replace("b_userPDBcode:",""))==4:
            userPDB=b_userPDBcode.replace("b_userPDBcode:","")
            userPDBpath=path+"/fragmax/process/"+userPDB+".pdb"
            
            ## Download and prepare PDB file - remove waters and HETATM
            with open(userPDBpath,"w") as pdb:
               pdb.write(pypdb.get_pdb_file(userPDB, filetype='pdb'))
            
            preparePDB="pdb_selchain -"+pdbchains+" "+userPDBpath+" | pdb_delhetatm | pdb_tidy > "+userPDBpath.replace(".pdb","_tidy.pdb")
            subprocess.call(preparePDB,shell=True)

        #STARANISO setting    
        if "true" in ap_staraniso:
            useANISO=" -useaniso"
        else:
            useANISO=""
        
        #BUSTER refinement mode
        if "thorough" in b_refinemode:
            refineMode=" -thorough"
        elif "quick" in b_refinemode:
            refineMode=" -quick"
        else:
            refineMode=" "

        #PDB_REDO options
        pdbREDO=""
        if "true" in b_sideaiderefit:
            pdbREDO+=" -remediate"
            refineMode=" -thorough"
        if "true" in b_sideaiderebuild:
            if "remediate" not in pdbREDO:
                pdbREDO+=" -remediate"
            pdbREDO+=" -sidechainrebuild"
        if "true" in b_pepflip:
            pdbREDO+=" -runpepflip"

        #Rhofit ligand
        if "true" in rho_ligandfromname:
            ligand = input_data.split("/")[-1][:-12].replace(acr+"-","")
        elif "false" in rho_ligandfromname:
            if len(rho_ligandcode)>15:
                ligand=rho_ligandcode.replace("rho_ligandcode:","")
            elif len(rho_ligandsmiles)>17:
                ligand=rho_ligandsmiles.replace("rho_ligandsmiles:","")
        lib=""
        try:
            int(ligand[-2])
        except ValueError:
            lib=ligand[:-2]
        else:
            lib=ligand[:-3]
        rhofitINPUT=" -rhofit "+path+"/fragmax/process/fragment/"+lib+"/"+ligand+"/"+ligand+".cif"
        
        #### Create symlink of fragment library to user project folder (/fragmax/process/fragment/lib)
        os.makedirs(path+"/fragmax/process/fragment/", exist_ok=True)
        if os.path.lexists(path+"/fragmax/process/fragment/"+lib):
            os.remove(path+"/fragmax/process/fragment/"+lib)
        os.symlink("/data/staff/biomax/fragmax/fragment/"+lib+"/",path+"/fragmax/process/fragment/"+lib)


        #Keep Hydrogen RhoFit
        keepH=""
        if "true" in rho_keepH:
            keepH=" -keepH"

        #Cluster to search for ligands
        clusterSearch=""
        ncluster="1"
        if len(rho_allclusters)>16:
            if "true" in rho_allclusters.split(":")[-1].lower(): 
                clusterSearch=" -allclusters"
            else:
                ncluster=rho_xclusters.split(":")[-1]
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            clusterSearch=" -xcluster "+ncluster

        #Search mode for RhoFit
        if "thorough" in rho_fittingproc:
            fitrefineMode=" -rhothorough"
        elif "quick" in rho_fittingproc:
            fitrefineMode=" -rhoquick"
        else:
            fitrefineMode=" "
        #Post refine for RhoFit
        if "thorough" in rho_postrefine:
            postrefineMode=" -postthorough"
        elif "standard" in rho_postrefine:
            postrefineMode=" -postref"
        elif "quick" in rho_postrefine:
            postrefineMode=" -postquick"
        else:
            postrefineMode=" "
        
        scanChirals=""
        if "false" in rho_scanchirals:
            scanChirals=" -nochirals"
        
        occRef=""
        if "false" in rho_occuprefine:
            occRef=" -nooccref"
        
        singlePipedreamOut=""
        singlePipedreamOut+= """#!/bin/bash\n"""
        singlePipedreamOut+= """#!/bin/bash\n"""
        singlePipedreamOut+= """#SBATCH -t 99:55:00\n"""
        singlePipedreamOut+= """#SBATCH -J pipedream\n"""
        singlePipedreamOut+= """#SBATCH --exclusive\n"""
        singlePipedreamOut+= """#SBATCH -N1\n"""
        singlePipedreamOut+= """#SBATCH --cpus-per-task=48\n"""
        singlePipedreamOut+= """#SBATCH --mem=220000\n""" 
        singlePipedreamOut+= """#SBATCH -o """+path+"""/fragmax/logs/pipedream_"""+ligand+"""_%j.out\n"""
        singlePipedreamOut+= """#SBATCH -e """+path+"""/fragmax/logs/pipedream_"""+ligand+"""_%j.err\n"""    
        singlePipedreamOut+= """module purge\n"""
        singlePipedreamOut+= """module load autoPROC BUSTER\n\n"""
        
        chdir="cd "+"/".join(ppdoutdir.split("/")[:-1])
        ppd="pipedream -h5 "+input_data+" -d "+ppdoutdir+" -xyzin "+userPDBpath+rhofitINPUT+useANISO+refineMode+pdbREDO+keepH+clusterSearch+fitrefineMode+postrefineMode+scanChirals+occRef+" -nofreeref -nthreads -1 -v"
        
        singlePipedreamOut+=chdir+"\n"
        singlePipedreamOut+=ppd

        with open(path+"/fragmax/scripts/pipedream_"+ligand+".sh","w") as ppdsh:
            ppdsh.write(singlePipedreamOut)

        script=path+"/fragmax/scripts/pipedream_"+ligand+".sh"
        command ='echo "module purge | module load autoPROC BUSTER | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

    if "alldatasets" in input_data:
        ppddatasetList=glob.glob(path+"/raw/"+acr+"/*/*master.h5")
        ppdoutdirList=[x.replace("/raw/","/fragmax/process/pipedream/").replace("_master.h5","") for x in ppddatasetList]
        
        for i in ppdoutdirList:
            os.makedirs("/".join(i.split("/")[:-1]),exist_ok=True)

            if os.path.exists(ppdoutdir):
                try:
                    int(ppdoutdir[-1])
                except ValueError:
                    run="1"
                else:
                    run=str(int(ppdoutdir[-1])+1)
                shutil.copytree(i,i+"_run"+run)
            
        
        if len(b_userPDBcode.replace("b_userPDBcode:",""))==4:
            userPDB=b_userPDBcode.replace("b_userPDBcode:","")
            userPDBpath=path+"/fragmax/process/"+userPDB+".pdb"
            
            ## Download and prepare PDB file - remove waters and HETATM
            with open(userPDBpath,"w") as pdb:
               pdb.write(pypdb.get_pdb_file(userPDB, filetype='pdb'))
            
            preparePDB="pdb_selchain -"+pdbchains+" "+userPDBpath+" | pdb_delhetatm | pdb_tidy > "+userPDBpath.replace(".pdb","_tidy.pdb")
            subprocess.call(preparePDB,shell=True)

        #STARANISO setting    
        if "true" in ap_staraniso:
            useANISO=" -useaniso"
        else:
            useANISO=""
        
        #BUSTER refinement mode
        if "thorough" in b_refinemode:
            refineMode=" -thorough"
        elif "quick" in b_refinemode:
            refineMode=" -quick"
        else:
            refineMode=" "

        #PDB_REDO options
        pdbREDO=""
        if "true" in b_sideaiderefit:
            pdbREDO+=" -remediate"
            refineMode=" -thorough"
        if "true" in b_sideaiderebuild:
            if "remediate" not in pdbREDO:
                pdbREDO+=" -remediate"
            pdbREDO+=" -sidechainrebuild"
        if "true" in b_pepflip:
            pdbREDO+=" -runpepflip"

        #Rhofit ligand
        
        
        lib=rho_ligandcode.replace("rho_ligandcode:","")
                
        
        #### Create symlink of fragment library to user project folder (/fragmax/process/fragment/lib)
        os.makedirs(path+"/fragmax/process/fragment/", exist_ok=True)
        if os.path.lexists(path+"/fragmax/process/fragment/"+lib):
            try:
                os.remove(path+"/fragmax/process/fragment/"+lib)
            except:
                pass
            else:
                os.symlink("/data/staff/biomax/fragmax/fragment/"+lib+"/",path+"/fragmax/process/fragment/"+lib)
        else:
            os.symlink("/data/staff/biomax/fragmax/fragment/"+lib+"/",path+"/fragmax/process/fragment/"+lib)


        #Keep Hydrogen RhoFit
        keepH=""
        if "true" in rho_keepH:
            keepH=" -keepH"

        #Cluster to search for ligands
        clusterSearch=""
        if len(rho_allclusters)>16:
            if "true" in rho_allclusters.split(":")[-1].lower(): 
                clusterSearch=" -allclusters"
            else:
                ncluster=rho_xclusters.split(":")[-1]
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            clusterSearch=" -xcluster "+ncluster

        #Search mode for RhoFit
        if "thorough" in rho_fittingproc:
            fitrefineMode=" -rhothorough"
        elif "quick" in rho_fittingproc:
            fitrefineMode=" -rhoquick"
        else:
            fitrefineMode=" "
        #Post refine for RhoFit
        if "thorough" in rho_postrefine:
            postrefineMode=" -postthorough"
        elif "standard" in rho_postrefine:
            postrefineMode=" -postref"
        elif "quick" in rho_postrefine:
            postrefineMode=" -postquick"
        else:
            postrefineMode=" "
        
        scanChirals=""
        if "false" in rho_scanchirals:
            scanChirals=" -nochirals"
        
        occRef=""
        if "false" in rho_occuprefine:
            occRef=" -nooccref"
        
        allPipedreamOut=""
        allPipedreamOut+= """#!/bin/bash\n"""
        allPipedreamOut+= """#!/bin/bash\n"""
        allPipedreamOut+= """#SBATCH -t 99:55:00\n"""
        allPipedreamOut+= """#SBATCH -J pipedream\n"""
        allPipedreamOut+= """#SBATCH --exclusive\n"""
        allPipedreamOut+= """#SBATCH -N1\n"""
        allPipedreamOut+= """#SBATCH --cpus-per-task=48\n"""
        allPipedreamOut+= """#SBATCH --mem=220000\n""" 
        allPipedreamOut+= """#SBATCH -o """+path+"""/fragmax/logs/pipedream_allDatasets_%j.out\n"""
        allPipedreamOut+= """#SBATCH -e """+path+"""/fragmax/logs/pipedream_allDatasets_%j.err\n"""    
        allPipedreamOut+= """module purge\n"""
        allPipedreamOut+= """module load autoPROC BUSTER\n\n"""
        
        for ppddata,ppdout in zip(ppddatasetList,ppdoutdirList):
            lib=""
            try:
                int(ligand[-2])
            except ValueError:
                lib=ligand[:-2]
            else:
                lib=ligand[:-3]
            chdir="cd "+"/".join(ppdout.split("/")[:-1])
            if "apo" not in ppddata.lower():
                ligand = ppddata.split("/")[-1][:-12].replace(acr+"-","")
                rhofitINPUT=" -rhofit "+path+"/fragmax/process/fragment/"+lib+"/"+ligand+"/"+ligand+".cif "+keepH+clusterSearch+fitrefineMode+postrefineMode+scanChirals+occRef
            if "apo" in ppddata.lower():
                rhofitINPUT=""
            ppd="pipedream -h5 "+ppddata+" -d "+ppdout+" -xyzin "+userPDBpath+rhofitINPUT+useANISO+refineMode+pdbREDO+" -nofreeref -nthreads -1 -v"
        
            allPipedreamOut+=chdir+"\n"
            allPipedreamOut+=ppd+"\n\n"

        with open(path+"/fragmax/scripts/pipedream_allDatasets.sh","w") as ppdsh:
            ppdsh.write(allPipedreamOut)
        
        
        script=path+"/fragmax/scripts/pipedream_allDatasets.sh"
        command ='echo "module purge | module load autoPROC BUSTER | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

        
    return render(request, "fragview/submit_pipedream.html",{"command":"<br>".join(ppdCMD.split(";;"))})
    
def load_project_summary(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    number_known_apo=len(glob.glob(path+"/raw/"+acr+"/*Apo*"))
    number_datasets=len(glob.glob(path+"/raw/"+acr+"/*"))
    if "JBSA" in "".join(glob.glob(path+"/raw/"+acr+"/*")):
        fraglib="JBS Xtal Screen"
    else:
        fraglib="Custom library"
    months={"01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun","07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"}
    natdate=shift[0:4]+" "+months[shift[4:6]]+" "+shift[6:8]
    
    return render(request,'fragview/project_summary.html', {
        'acronym':acr,
        "proposal":proposal,
        "proposal_type":proposal_type,
        "shift":shift,
        "known_apo":number_known_apo,
        "num_dataset":number_datasets,
        "fraglib":fraglib,
        "exp_date":natdate})
    
def project_summary_load(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    a=str(request.GET.get('submitProc')) 
    out="No option selected"
    if "colParam" in a:
        create_dataColParam(acr,path)
        out="Data collection parameters synced"
    elif "panddaResults" in a:
        panddaResultSummary()
        out="PanDDA result summary synced"
    elif "procRef" in a:
        resultSummary()    
        out="Data processing and Refinement results synced"
    elif "ligfitting" in a:
        parseLigand_results()
        out="Ligand fitting results synced"
    return render(request,'fragview/project_summary_load.html', {'option': out})

def dataset_info(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    a=str(request.GET.get('proteinPrefix'))     
    prefix=a.split(";")[0]
    images=a.split(";")[1]
    run=a.split(";")[2]

    images=str(int(images)/2)
    xmlfile=path+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_1.xml"
    datainfo=retrieveParameters(xmlfile)    

    energy=format(float(datainfo["wavelength"])*13.6307922,".2f")
    totalExposure=str(float(datainfo["exposureTime"])*float(datainfo["numberOfImages"]))
    edgeResolution=str(float(datainfo["resolution"])*0.75625)
    ligpng="JBS/"+prefix.split("-")[1]+"/image.png"

    fragConc="100 mM"
    solventConc="15%"
    soakTime="24h"

    if "Apo" in prefix:
        soakTime="Soaking not performed"
        fragConc="-"
        solventConc="-"
    
    new_run=""
    search_new_run_path=path+"/fragmax/manual_proc/"+acr+"/"+prefix

    if os.path.exists(search_new_run_path):
        if glob.glob(path+"/fragmax/manual_proc/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/*") == []:
            new_run="<p style='padding-left:310px;'><font color='green'>All processed data are merged to your project.</font></p>"    
        elif os.path.exists(path+"/fragmax/manual_proc/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/stat"):
            with open(path+"/fragmax/manual_proc/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/stat","r") as inp:
                if "None" in inp.readlines()[0]:
                    new_run="<p style='padding-left:310px;'><font color='green'>All processed data are merged to your project.</font></p>"    
                else:
                    new_run="""<form style="padding-left:310px;" action="/dataproc_merge/" method="get" id="mergeproc">
                               <p><font color='red'>You have manual processed data not merged to your project. 
                               <input type="hidden" value="""+search_new_run_path+""" name="mergeprocinput" size="1">
                               <a href="javascript:{}" onclick="document.getElementById('mergeproc').submit();">Click here</a> to compare results</font></p></form>"""
        else:
            new_run="""<form style="padding-left:310px;" action="/dataproc_merge/" method="get" id="mergeproc">
                       <p><font color='red'>You have manual processed data not merged to your project. 
                       <input type="hidden" value="""+search_new_run_path+""" name="mergeprocinput" size="1">
                       <a href="javascript:{}" onclick="document.getElementById('mergeproc').submit();">Click here</a> to compare results</font></p></form>"""
        #new_run+=search_new_run_path
    #new_run="<p style='padding-left:260px;'>"+path+"/fragmax/manual_proc/"+acr+"/"+prefix+"/"+prefix+"_"+run+"     "+search_new_run_path+"</p>"
    return render(request,'fragview/dataset_info.html', {
        "proposal":proposal,
        "shift":shift,
        "new_proc_run":new_run,
        "run":run,
        'imgprf': prefix, 
        'imgs': images,
        "ligand": ligpng,
        "fragConc": fragConc,
        "solventConc":solventConc,
        "soakTime":soakTime,
        "axisEnd":datainfo["axisEnd"],
        "axisRange":datainfo["axisRange"],
        "axisStart":datainfo["axisStart"],
        "beamShape":datainfo["beamShape"],
        "beamSizeSampleX":datainfo["beamSizeSampleX"],
        "beamSizeSampleY":datainfo["beamSizeSampleY"],
        "detectorDistance":datainfo["detectorDistance"],
        "endTime":datainfo["endTime"],
        "exposureTime":datainfo["exposureTime"],
        "flux":datainfo["flux"],
        "imageDirectory":datainfo["imageDirectory"],
        "imagePrefix":datainfo["imagePrefix"],
        "kappaStart":datainfo["kappaStart"],
        "numberOfImages":datainfo["numberOfImages"],
        "overlap":datainfo["overlap"],
        "phiStart":datainfo["phiStart"],
        "resolution":datainfo["resolution"],
        "rotatioAxis":datainfo["rotatioAxis"],
        "runStatus":datainfo["runStatus"],
        "slitV":datainfo["slitV"],
        "slitH":datainfo["slitH"],
        "startTime":datainfo["startTime"],
        "synchrotronMode":datainfo["synchrotronMode"],
        "transmission":datainfo["transmission"],
        "wavelength":datainfo["wavelength"],
        "xbeampos":datainfo["xbeampos"],
        "snapshot1":datainfo["snapshot1"],
        "snapshot2":datainfo["snapshot2"],
        "snapshot3":datainfo["snapshot3"],
        "snapshot4":datainfo["snapshot4"],
        "ybeampos":datainfo["ybeampos"],        
        "energy":energy,
        "totalExposure":totalExposure,
        "edgeResolution":edgeResolution,
        "acr":prefix.split("-")[0]
        })
  
def post_list(request):
    
    posts = Post.objects.filter(published_date__lte=timezone.now()).order_by('published_date')
    #posts = glob.glob("/data/visitors/*")
    return render(request, 'fragview/post_list.html', {'posts': posts})

def post_detail(request,pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'fragview/post_detail.html', {'post': post})

def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.published_date = timezone.now()
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'fragview/post_edit.html', {'form': form})

def datasets(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    resyncAction=str(request.GET.get("resyncdsButton"))
    resyncImages=str(request.GET.get("resyncImgButton"))
    resyncStatus=str(request.GET.get("resyncstButton"))

    if os.path.exists(path+"/fragmax/process/datacollectionPar.csv"):
        with open(path+"/fragmax/process/datacollectionPar.csv") as csvinp:
            if acr not in "".join(csvinp.readlines()):
                os.remove(path+"/fragmax/process/datacollectionPar.csv")
                create_dataColParam(acr,path)   
                get_project_status()     
                if not os.path.exists(path+"/fragmax/results/"):    
                    get_project_status_initial()
    else:
        create_dataColParam(acr,path)    
        if not os.path.exists(path+"/fragmax/results/"):
            get_project_status_initial()        
    if "resyncDataset" in resyncAction:
        shutil.move(path+"/fragmax/process/datacollectionPar.csv",path+"/fragmax/process/datacollectionParold.csv")
        create_dataColParam(acr,path)
    if "resyncImages" in resyncImages:
        #project_dif_svg()        
        pass
    if "resyncStatus" in resyncStatus:
        get_project_status()
        if not os.path.exists(path+"/fragmax/results/"):
            get_project_status_initial()
        
    

    with open(path+"/fragmax/process/datacollectionPar.csv","r") as inp:
        a=inp.readlines()
    try:
        acr_list=a[1].split(",")
        smp_list=[x.split(acr+"-")[-1] for x in a[2].split(",")]
        prf_list=a[2].split(",")
        res_list=a[3].split(",")
        img_list=a[4].split(",")
        path_list=a[5].split(",")
        snap_list=a[6].split(",")
        png_list=a[7].split(",")
        run_list=a[8].split(",")
        dpentry=list()
        rfentry=list()
        lgentry=list()




        ##Proc status
        if os.path.exists(path+"/fragmax/process/dpstatus.csv"):
            with open(path+"/fragmax/process/dpstatus.csv") as inp:
                dp=inp.readlines()
                dpDict=dict()
                for line in dp:
                    key=line.split(":")[0]
                    value=":".join(line.split(":")[1:])
                    dpDict[key]=value
            for i,j in zip(prf_list,run_list):
                dictEntry=i+"_"+j
                if dictEntry in dpDict:
                    da="<td>"
                    if "autoproc:full" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> autoPROC</font></p>""")
                    elif "autoproc:partial" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> autoPROC</font></p>""")
                    else:
                        da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> autoPROC</font></p>""")

                    if "dials:full" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XIA2/DIALS</font></p>""")
                    elif "dials:partial" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> XIA2/DIALS</font></p>""")
                    else:
                        da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/DIALS</font></p>""")

                    if "xdsxscale:full" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XIA2/XDS</font></p>""")
                    elif "xdsxscale:partial" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> XIA2/XDS</font></p>""")
                    else:
                        da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>""")

                    if "xdsapp:full" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XDSAPP</font></p>""")
                    elif "xdsapp:partial" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> XDSAPP</font></p>""")
                    else:
                        da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDSAPP</font></p>""")


                    if "fastdp:full" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> fastdp</font></p>""")
                    elif "fastdp:partial" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> fastdp</font></p>""")
                    else:
                        da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> fastdp</font></p>""")


                    if "EDNA_proc:full" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> EDNA_proc</font></p>""")
                    elif "EDNA_proc:partial" in dpDict[dictEntry]:
                        da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> EDNA_proc</font></p>""")
                    else:
                        da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> EDNA_proc</font></p></td>""")

                    
                    
                    dpentry.append(da)

                else:                
                    dpentry.append("""<td>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> autoPROC</font></p>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XIA2/DIALS</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XDSAPP</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> fastdp</font></p>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> EDNA_proc</font></p>    
                    </td>""")
        else:
            for i in prf_list:
                dpentry.append("""<td>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> autoPROC</font></p>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XIA2/DIALS</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XDSAPP</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> fastdp</font></p>
                        <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> EDNA_proc</font></p>    
                    </td>""")
        ##Ref status
        if os.path.exists(path+"/fragmax/process/rfstatus.csv"):
            with open(path+"/fragmax/process/rfstatus.csv") as inp:
                rf=inp.readlines() 
                rfDict=dict()
                for line in rf:
                    key=line.split(":")[0]
                    value=":".join(line.split(":")[1:])
                    rfDict[key]=value

            for i,j in zip(prf_list,run_list):
                dictEntry=i+"_"+j
                if dictEntry in rfDict:
                    re="<td>"  
                    if "BUSTER:full" in rfDict[dictEntry]:
                        re+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> BUSTER</font></p>""")
                    else:
                        re+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> BUSTER</font></p>""")

                    if "dimple:full" in rfDict[dictEntry]:
                        re+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Dimple</font></p>""")
                    else:
                        re+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Dimple</font></p>""")
                    if "fspipeline:full" in rfDict[dictEntry]:
                        re+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> FSpipeline</font></p></td>""")
                    else:
                        re+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> FSpipeline</font></p></td>""")
                    
                    rfentry.append(re)

                else:
                    rfentry.append("""<td>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> BUSTER</font></p>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Dimple</font></p>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> FSpipeline</font></p>    
                        </td>""")
        else:
            for i in prf_list:
                rfentry.append("""<td>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> BUSTER</font></p>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Dimple</font></p>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> FSpipeline</font></p>    
                        </td>""")
        ##Lig status
        if os.path.exists(path+"/fragmax/process/lgstatus.csv"):
            with open(path+"/fragmax/process/lgstatus.csv") as inp:
                lg=inp.readlines()
                lgDict=dict()
                for line in lg:
                    key=line.split(":")[0]
                    value=":".join(line.split(":")[1:])
                    lgDict[key]=value
            
            for i,j in zip(prf_list,run_list):
                dictEntry=i+"_"+j
                if "Apo" not in dictEntry:
                    if dictEntry in lgDict:
                        lge="<td>"
                        if "rhofit:full" in lgDict[dictEntry] :
                            lge+='<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> RhoFit</font></p>'
                            if "ligandfit:full" in lgDict[dictEntry]:
                                lge+='<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Phenix LigFit</font></p></td>'
                            elif "ligandfit:partial" in lgDict[dictEntry]:
                                lge+='<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> Phenix LigFit</font></p></td>'
                            else:
                                lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
                            lgentry.append(lge)
                        elif "rhofit:partial" in lgDict[dictEntry] :
                            lge+='<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> RhoFit</font></p>'
                            if "ligandfit:full" in lgDict[dictEntry]:
                                lge+='<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Phenix LigFit</font></p></td>'
                            elif "ligandfit:partial" in lgDict[dictEntry]:
                                lge+='<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> Phenix LigFit</font></p></td>'
                            else:
                                lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
                            lgentry.append(lge)
                        elif "rhofit:none" in lgDict[dictEntry] :
                            lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>'
                            if "ligandfit:full" in lgDict[dictEntry]:
                                lge+='<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Phenix LigFit</font></p></td>'
                            elif "ligandfit:partial" in lgDict[dictEntry]:
                                lge+='<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> Phenix LigFit</font></p></td>'
                            else:
                                lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
                            lgentry.append(lge)
                        else:
                            lgentry.append("""<td>
                                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>
                                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p>    
                                </td>""")


                #         if "rhofit:full" in lgDict[dictEntry] and "ligandfit:full" in lgDict[dictEntry]:
                #             lgentry.append("""<td>
                #                     <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> RhoFit</font></p>
                #                     <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Phenix LigFit</font></p>    
                #                 </td>""")
                #         elif "rhofit:full" in lgDict[dictEntry] and "ligandfit:full" not in lgDict[dictEntry]:
                #             lgentry.append("""<td>
                #                 <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> RhoFit</font></p>
                #                 <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p>    
                #             </td>""")
                #         elif "rhofit:full" not in lgDict[dictEntry] and "ligandfit:full" in lgDict[dictEntry]:
                #             lgentry.append("""<td>
                #                 <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>
                #                 <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Phenix LigFit</font></p>    
                #             </td>""")
                #     else:
                #         lgentry.append("""<td>
                #                 <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>
                #                 <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p>    
                #             </td>""")
                else:
                    lgentry.append("""<td>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p>    
                        </td>""")
        else:
            for i in prf_list:
                lgentry.append("""<td>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>
                            <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p>    
                        </td>""")
        results = zip(img_list,prf_list,res_list,path_list,snap_list,acr_list,png_list,run_list,smp_list,dpentry,rfentry,lgentry)
        return render_to_response('fragview/datasets.html', {'files': results})
    except:
        return render_to_response('fragview/datasets_notready.html')    
    
def results(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    
    resync=str(request.GET.get("resync"))
    if "resyncresults" in resync:
        resultSummary()
    if not os.path.exists(path+"/fragmax/process/generalrefsum.csv"):
        resultSummary()
    try:
        with open(path+"/fragmax/process/generalrefsum.csv","r") as inp:
            a=inp.readlines()
        return render_to_response('fragview/results.html', {'files': a})
    except:
        return render_to_response('fragview/results_notready.html')

def request_page(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    a=str(request.GET.get('structure'))     
    name=a.split(";")[0].split("/modelled_structures/")[-1].split(".pdb")[0]  
    a=zip([a.split(";")[0]],[a.split(";")[1]],[a.split(";")[2]],[a.split(";")[3]])  
    
    return render(request,'fragview/pandda_density.html', {'structure': a,'protname':name})

def request_page_res(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    a=str(request.GET.get('structure')) 
    center=""
    if "],[" in a.split(";")[3]:
        center=[a.split(";")[3].split("],[")[0]+"]"]
    else:
        center=[a.split(";")[-1].replace("],","]")]    
    
    a=zip(["_".join(a.split(";")[0].split("/")[-4:-1])],[a.split(";")[0]],[a.split(";")[1]],[a.split(";")[2]],[a.split(";")[3]],center )    
    
    return render(request,'fragview/density.html', {'structure': a})

def ugly(request):
    return render(request,'fragview/ugly.html')

def dual_ligand(request):
    try:
        a="load maps and pdb"
        return render(request,'fragview/dual_ligand.html', {'Report': a})
    except:
        return render(request,'fragview/dual_ligand_notready.html', {'Report': a})

##################################
####### COMPARE TWO LIGANDS ######
##################################

def compare_poses(request):   
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    a=str(request.GET.get('ligfit_dataset')) 
    data=a.split(";")[0]
    blob=a.split(";")[1]
    lig=data.split(acr+"-")[-1].split("_")[0]
    ligpng=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".svg"    
    rhofit=path+"/fragmax/results/ligandfit/"+data+"/rhofit/best.pdb"
    ligfit=path+"/fragmax/results/ligandfit/"+data+"/LigandFit_run_1_/ligand_fit_1.pdb"
    ligcenter="[]"
    rhocenter="[]"
    if os.path.exists(ligfit):
        with open(ligfit,"r") as ligfitfile:
            for line in ligfitfile.readlines():
                if line.startswith("HETATM"):
                    ligcenter="["+",".join(line[32:54].split())+"]"
                    break
    if os.path.exists(rhofit):                    
        with open(rhofit,"r") as rhofitfile:
            for line in rhofitfile.readlines():
                if line.startswith("HETATM"):
                    rhocenter="["+",".join(line[32:54].split())+"]"
                    break
    path=path.replace("/data/visitors/","")
        
    return render(request,'fragview/dual_density.html', {'ligfit_dataset': data,'blob': blob, 'png':ligpng, "path":path,"rhofitcenter":rhocenter,"ligandfitcenter":ligcenter, "ligand":fraglib+"_"+lig})

def ligfit_results(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    resyncLigFits=str(request.GET.get("resyncligfit"))

    if "resyncligfit" in resyncLigFits:
        parseLigand_results()
    if os.path.exists(path+"/fragmax/process/autolig.csv"):
        try:
            with open(path+"/fragmax/process/autolig.csv","r") as outp:
                a="".join(outp.readlines())
            
            return render(request,'fragview/ligfit_results.html', {'resTable': a})
        except:
            return render(request,'fragview/ligfit_results_notready.html')
    else:
        return render(request,'fragview/ligfit_results_notready.html')

###################################
##########Load external HTML#######
###################################


def pandda(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    
    if os.path.exists(path+"/fragmax/results/pandda/pandda/analyses/html_summaries/pandda_analyse.html"):
        if not os.path.exists(path+"/fragmax/process/panddarefsum.csv"):
            panddaResultSummary()
            parseLigand_results()
        try:
            with open(path+"/fragmax/results/pandda/pandda/analyses/html_summaries/pandda_analyse.html","r") as inp:
                a="".join(inp.readlines())
            
                
            with open(path+"/fragmax/process/panddarefsum.csv","r") as inp:
                body="".join(inp.readlines())
            thead_ini=a.index("<thead>")+8
            thead_end=a.index("</thead>") 
            tbody_ini=a.index("<tbody>")+8
            tbody_end=a.index("</tbody>")     
            a=a.replace(a[thead_ini:tbody_end],"""<tr>
                <th>Data set</th>
                <th>Space group</th>
                <th>Res. [Å]</th>
                <th>R<sub>work</sub> [%]</th>
                <th>R<sub>free</sub> [%]</th>
                <th>RMS bonds [Å]</th>
                <th>RMS angles [°]</th>
                <th>a</th>
                <th>b</th>
                <th>c</th>
                <th>α</th>
                <th>β</th>
                <th>γ</th>
                <th>Unmodelled blobs</th>
                <th>σ</th>
                <th>Event</th>
                </tr>
                </thead>
                <tbody><tr></tr>"""+body)
            a=a.replace('class="table-responsive"','').replace('id="main-table" class="table table-bordered table-striped"','id="resultsTable"')
            
            return render(request,'fragview/pandda.html', {'Report': a})
        except:
            actionbtn=str(request.GET.get("runpanddafolderform"))
            return render(request,'fragview/pandda_notready.html',{"panddafolder":actionbtn})
    else:
        folderbtn=str(request.GET.get("runpanddafolderform"))
        runpanddabtn=str(request.GET.get("runpanddaform"))
        populateMissing=str(request.GET.get("missingreflform"))
        actionbtn="No Action"
        if "run" in folderbtn:
            actionbtn="makefolders"
            t = threading.Thread(target=prepare_pandda_folder,args=())
            t.daemon = True
            t.start()
        if "run" in runpanddabtn:

            actionbtn="runpandda"
            panddaRUNscript=""
            panddaRUNscript+='#!/bin/bash\n'
            panddaRUNscript+='#!/bin/bash\n'
            panddaRUNscript+='#SBATCH -t 99:55:00\n'
            panddaRUNscript+='#SBATCH -J PanDDA\n'
            panddaRUNscript+='#SBATCH --exclusive\n'
            panddaRUNscript+='#SBATCH -N1\n'
            panddaRUNscript+='#SBATCH --cpus-per-task=48\n'
            panddaRUNscript+='#SBATCH --mem=220000\n'
            panddaRUNscript+='#SBATCH -o '+path+'/fragmax/logs/panddarun_%j.out\n'
            panddaRUNscript+='#SBATCH -e '+path+'/fragmax/logs/panddarun_%j.err\n'
            panddaRUNscript+='module purge\n'
            panddaRUNscript+='module load CCP4 PyMOL\n\n'
            panddaRUNscript+='cd '+path+'/fragmax/results/pandda/\n'
            panddaRUNscript+='pandda.analyse data_dirs="'+path+'/fragmax/results/pandda/*" cpus=48  input.max_new_datasets=1000  \n'
            panddaRUNscript+='python '+path+'/fragmax/scripts/checkPanDDA.py '+path

            if not os.path.exists(path+"/fragmax/scripts/panddaRUN.sh"):
                with open(path+"/fragmax/scripts/panddaRUN.sh","w") as outp:
                    outp.write(panddaRUNscript)

            script=path+"/fragmax/scripts/panddaRUN.sh"
            command ='echo "module purge | module load CCP4 PyMOL | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)


        if "run" in populateMissing:
            actionbtn="population missing reflections"
            t = threading.Thread(target=populate_missing,args=())
            t.daemon = True
            t.start()
            #populate_missing()
        return render(request,'fragview/pandda_notready.html',{"panddafolder": actionbtn})

def procReport(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    biomax_static=path.replace("/data/visitors/","/static/")
    a=str(request.GET.get('dataHeader')) 
    if a.startswith("dials"):
        a=a.replace("dials","")
        a=path+"/fragmax/process/"+a.split("-")[0]+"/"+a+"/"+a+"_1/dials/xia2.html"
        if os.path.exists(a):
            with open(a,"r") as inp:
                html="".join(inp.readlines())
        else:
            html='<h5 style="padding-left:260px;" >DIALS report for this dataset is not available</h5>'
        html=html.replace("DEFAULT/scale/",a.replace(path,biomax_static).replace("xia2.html","DEFAULT/scale/"))
        html=html.replace("DataFiles/",a.replace(path,biomax_static).replace("xia2.html","DataFiles/"))
    
    if a.startswith("xdsxscale"):
        a=a.replace("xdsxscale","")
        a=path+"/fragmax/process/"+a.split("-")[0]+"/"+a+"/"+a+"_1/xdsxscale/xia2.html"
        if os.path.exists(a):
            with open(a,"r") as inp:
                html="".join(inp.readlines())
        else:
            html='<h5 style="padding-left:260px;" >XDS/XSCALE report for this dataset is not available</h5>'
        html=html.replace("DEFAULT/scale/",a.replace(path,biomax_static).replace("xia2.html","DEFAULT/scale/"))
        html=html.replace("DataFiles/",a.replace(path,biomax_static).replace("xia2.html","DataFiles/"))
    
    if a.startswith("xdsapp"):
        a=a.replace("xdsapp","")
        a=path+"/fragmax/process/"+acr+"/"+a+"/"+a+"_1/xdsapp/results_"+a+"_1_data.txt"
        #a=path+"/fragmax/process/"+a.split("-")[0]+"/"+a+"/"+a+"_1/xdsxscale/xia2.html"
        if os.path.exists(a):
            with open(a,"r") as inp:
                html="<br>".join(inp.readlines())
        else:
            html='<h5 style="padding-left:260px;" >XDSAPP report for this dataset is not available</h5>'
        #html=html.replace("DEFAULT/scale/",a.replace(path,biomax_static).replace("xia2.html","DEFAULT/scale/"))
        #html=html.replace("DataFiles/",a.replace(path,biomax_static).replace("xia2.html","DataFiles/"))
        html='''<style>  .card {  margin: 40px 0 0 50px !important; }</style><div class="card" ><div class="card-content"><div class="card-title">XDSAPP Processing report</div><br>'''+html+'</div></div>'

    if a.startswith("autoPROC"):
        a=a.replace("autoPROC","")
        if os.path.exists(path+"/fragmax/results/"+a+"_1/pipedream/process/summary.html"):
            a=path+"/fragmax/results/"+a+"_1/pipedream/process/summary.html"
        else:
            a=path+"/fragmax/process/"+a.split("-")[0]+"/"+a+"/"+a+"_1/autoproc/summary.html"


        if os.path.exists(a):
            with open(a,"r") as inp:
                html="".join(inp.readlines())
        else:
            html='<h5 style="padding-left:310px;" >autoPROC report for this dataset is not available</h5>' 
    html=html.replace('src="/data/visitors/','src="/static/').replace('href="/data/visitors/','href="/static/').replace("gphl_logo.png","data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAUgAAACaCAMAAAD8SyGRAAAAllBMVEX///8fSX0AOnUAOXQAPHYWRHoAP3jp7PFbdZoZRnsAN3OYp77AytcANXIMQHgAPndDYIt0iai4wtL19/psgqIvU4ODlK8AMnGQoLlVcJajr8Pv8vYALm/M097a4Ohof6BKaJIAKGyuusy+x9WJm7Xj5+0AJGtbc5glToE3Woidq8BPa5OxvM2Ela8AIGnd4uoAEWUAGWdi6FPvAAARhUlEQVR4nO1daYOisLJFSGRRAogKgoAb3eAy3vv//9wlG4KCprtnkfdyPsyoTUJySFKVSlWhKBISEhISEhISEhISEhISEhISEhISEhISEhL/H+Cn+6OXGafTKvPCcxL/6/YME+nEQDZAkGEMNHuR7XTB0sdsPve85eVyOIQEh8PlsvQ8b555nQWmRoYLLKsCh7sCmf/7evW3kYcLG8ERgTniMKETlEchLhfkCSCK8Zh9II/E7uTFA7BZolkgSH9v5/4eEsMeY/pMBCwLFhDYFqhpRbYbveayIvL2ABowKyI7C1REml0lqgLrgRKZbixCGrTKw5RS5qfT0BirnEsHuJPk+XyLjJU7spw2NciC5cq4dBZIjM9NYYF2Aag5i5MxH+TUjj2N8IXG3rX9F3+/4lSOIFpPXlbl51EBb6yYMEyfU+LH5xI1eATei8f1xpiZpCemNu+S0elKqweLIVJdXDZWWKEZatyot85favpbwbNJx1GR9Fww0+qOClWYWPxyZydUwK+HJJwLNvr9EC9oL6wnXdAXjEmQC9VZD0lVcJbO+ZNS+x7m2yNlktkOn13ll/QqsBeqlPNibgRbsXP4zB7q+pggOnjs6Pl1cUGuG7+WNhhHNlVhtx7+iKnKiBwLFng3pGPKo/p0PGIkROLATKjaM6C0oKVgO3K2qpqlYIE3g84UaEdg5IR49pmFUL0zTuRBsCE5G5FwI1jgzcBkCHRFLiaTO3hxkZ8cvdWiFsLIHm2842sBojPmzZVIS94OGevwWGgnPcOjxro+uSIJy0Bz2ru+arfnaIE7eVauInLMRqSQovpuOLOFSX0haDgWFUFa7+jKJyOtWnEhUi1Q04hs1cHLB0TaInpikRs0kTobj6bQxK6wqwgCPRuP61yt5D8E8HMyzZU9XyMn+jTKCgurBiZAl14qB03knBFpi+rAfkXHuFO8xx42eZjaaUbVwGlNJPmaXkbkB4T6tKchE8n3cWKShsCD3QrNGeJn4pT1E7kjsnoG0ZjINVB2772HTOSGiQR1Klyk4r5LxaZ79ebW6IHIikqDKqL2savmARPJB6SgZkjgjxx78/CjS7Z31qzxWweRijKhd7S6dNYBE7li22FHbNNHER1m9/LCp7qo3eSxm0jlSM1xoGN3NFwi+Z5M1J7TC5fw6LQt4N1EKh4Vb+rjOjtcIsOv6j49oDr9/frQQyTRRPHwfbBSDpdI1qUedUYYER3YYNb+uY/IvdYzDQZL5NVmM9v6kSGVbZHNe8N5H5H8+T3wNVgij9yQin7kSZFRiYXuh3UvkRG77/0mYLBEZtyE/aMl8sqMX+q9lt1LJLfywM+734dKJBuPPzxr8rjEuj8f6CWyPs1R26vkUInU+RL5MCm/BN77zf0f+olcMu7vjheHSmR9RNJnzBFCwmTw47axn0i+SN4xNlQiI24x/MJG+xFcF0UP2+d+IvkjvBP0QyXyws8C+u20AuD+EeDBMNxP5JV7bYDWujpUIuvzeOsnPl+F2bneKc+IzPlcAK3jjaESWfvaPD2CeQWuiz4utP1EcsbuNjdDJXL1W0YkH1xfGZH8fGMEWjuBoRJ5qon8yRrJ3XqdL6yRt6nd+nmoRK7EfZaO0W53nu2n04Rhup/t6Ek1V64fldHXRN65VAyVyHqNvDfbPCBdO44DAFBVVcOo/gfAsUh/+T7zcXv0RGozOyhq655DJZJT0KEC3iGpnUybME/4b/02zX4iE749b7u1DZVIr/ZmfuX0c90CB8FRGyggY5CT8pW9Nvffg+0iQyVywmXna+tPMotCAzb95SG87InI9ev90f1K208k2wrczezBEsm9xR5GRh/2Nwd7eKqL8BXiwenspfVHvdNfh0rkzclbVP+J6xCmhim4rgbeXd1LZAw6B+Rgiawnpbgdja8GLVdTl++2Bc9s2BJpmvd2+aESedPIhR1War+o5sFrn5fBizMb+0HpGiyRh9oVVPRcm4vo9hD2GAGgrUb1EXkmyhT4P3Su3YiEEXSO7CbS5xag9qa9h8iYeFqj02PtgyWSnxKIu793E6nkKmWyvez1EEkWFKeDxwETuazntqBtt4dIJWVMwqJhYOwm0sD3VDvjIoZLZFrPbcG29xGpXE3m0Q9vxxZdROZuxaNpd8c5DJdIZVNr2LaQcbeXSCWmno8j0/L49O4gcuJUN0RmzxmRIJFzN/vJIdMfwf6LIa/9RCpKhNjGb3ygOsA9kfpk5OBAbK9vHyVGpG9D8H5Bn+5tSIqsks+IVPxDQMPdkX06VvI74UQeceTNZGNjR3171W+OFyOy2tm+NFf9fdw0IHMhcvkzIrGT+ILELoygY9nuJ/eIOa1goCE4gsDynp1qiBFZLUcvDaj/APNacDsC+8QXROIrDi5O0IIjQerBbkLThEhzjN1z44gQkan9w0OmP4RamRaKkn5NZAV9HxoltK1bHLsFilU4fWli0rsdMNrAh8hiQWp/GYldD5wHK8LjxSJEEsR6GtZhxtdYyE5XB3V+9l+DB6RZvGU89+SmTJavGlgTKRLwWls4hKNjedDPpv8aLB1/6qn9p+DdDLyvWsiJFIpfPbOZKhyvXZuR+uXeEtcpGC/+95HdDJPu89ldH9BoAlYOblwS3qjwSPlRd6KlCqEltrD8K3g3vbx4KhBrIoH7epnix71CihUGX1R73eM8evsfuSH+WRwsLrtN8Cx2aUm5Ma3unFIt+LU6IOpbVKdlgZ0rR+KyteIdtR+O/bjW+oDbpwYlG9oTpzc3UBMhd6/6ag4M3IYH+eTvDYs3cfzOWRj1Uz0oq21cx9TyzyebZvx6nUMEI1RHN156t9cN7JpeCMCNkvRKkKbJrJGe7f1zh+xH9bk11JA3u81HPT3j/QruienYyxfjIU6S8yRTm5nOKpV8Fe6SpPtAw0+S2cSDoFmgupFmcWig5Z3w/la23cK6HVwDVYWLslyMHKBWPaG5EO3y+HJsnWwVjO/dMqqyjmqpnQXC9R1TL/DDOLW/gn02Bo3sjyYG/QQR0NyDyCpfmH0M3Hk6c3gtEs1+8FrEEmH9Y8Tn+UIFCEHWeJxp1NFAsVnuBZf4U6ACZwwh6XlREG6qSsZAtUFngWpEqtUgHiOSmaV0O1HNjaKo6qnmx68fhvL+PeT7o7dyq4YvSneTXY67RP/C5jbOc13XYwyfgHysftLzbluDn5MSOi3RXzGuCdcyGB4lJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJN4BcbpfPobuxel53uej51+n4RMfcfznAXgoYvjpdCmYZKITSejNlxHzuEUf6uNbEWJ7C3rfXb38Zas3b3j/MDlGk4M390LqOe5t7WcvRm3CF8+nqNNEgNOGw9qLwgKvOz5ttefvHn2KyDIPs3NY/ipC4tGYo65wikR9Emvgopv7vH/0bAcsdsne20Lq4rkReYMiLjreCscDJ4ZpazYybt7r2fppVFS4FXkHD3K+G5Gsu7zxMxBQAhdqR1Ru7tj9foZeO7LcgyoZKFMQkJrmHalmuhBvA9GgLwzTHDV9WV37aXzO3Fbp1ddn/pLuYw5lMegwqFnbr2k3FloHkTp6QuRSbRE5cUz6wYAkbZfX8S6aTky/8r4hZYU2za95+NSj1J+Qqe9/bp95Qm9E31J4j7LZR4PmhPkxkZEz8tkHkkVNmMivYY6+8YbOGDxN7PZdIidq0989ofnSfx+RM6D9SSKdbxDpwz9BpG+2kpYpdOW+ERknCZcwFZF69b0hudPblz4iz4BIKEqk3iicJw0Zqt8CamL2IaE3uD26qiU6ziPZzBP0QCSrP4lJ4Zi1Um//uRlQlzf7Qzp0+h6Re60rCwAnUjccw/0o2BekpdnHeguZRN+NPzNksS99RB4csv5jIpPFx9Y2KTPJYjNfrFnUW7wKstPWqlbH83KzxsrH0nW2uXIMPtY2UwZio/Cyj9VmN/9vo+ctIpODoeKg590Gbs/K1PwIrIqSsKokwAtvHmbQqRpVbM2Rvd1uCdfl4tYMJVq7BhwLJytr44K0jsABRmSq4W6ko4BoVjoyzTOOqbaJQLj80nFahnXSQyT53y+CPSXyEKFjOjURicE6f+BfjYBqC6UTYzlX1bozEOlGckBqYrj79AICUn9MguASu/CVZnPbRHqIJBJII+Tsjot9unS0pJgn6QEFVaF8aUL8UPV0BGZ6jnmcbnFPPCZhM6ImL9H3iDSg1fErJdJfqGRYJTbpjY5oLG8EguqOebDGX47a/AmR+mpNpbCHRkSR3AEyUke4Bhy1Tqpfkz+dCKsI0K1AAUekP65DxotH3y+Zae2l9m5qz52MdaogVS4gnW5II0/zSGeHz7OI6hYRrblKVLVwSydX8T31Z/OEyF3AyNkQ4agji8xLvxh7uBUkUDKxqOr2QKR5Wn26wYqtGx5LEXfVSJaOBZnhsUpevLCnNU3JlC1VpslSApUlIJSMqWIbgbaieEfkhTWC3+0T0E2Kq5FKdyq5UU2kR2eLP8K91QFLr/pNYXMytVqlLf4bOOAXbjgl8sQDsY8ODtOtpfYc4e7QNTDRqML4OCLzNE1rccKldg4aL63wEXlXVb5G8/rCUuNbAvr/gdYb0Lw9Z1WMSHY3g0XlMm7uibShMc+y7GStq+EeaSypxDeJnMOGsNE9SBcIQqRfD/Jqc5g2iAwRYr8fFqpJP/eskRw1kY7KiEwnG5u99OsSIJvbQ3qIdGnvIq0d5vojIlMLzKb7/X42m1VtyhxW9TeJjJxmuodEtcn4JETGkBOZqlgZvBFJ15ozcKM8tfqIbBkIbiOSEpmU5iT1TY3Sd15oyKYX9BC5p++ePa3bKsaPiEw0uyG4TtxY8E0ida2Z57aq+0akX2eaSgHOzFcTuQT44XkfR1LiO0Qe17jVPtS4KnMuEdUFeohUsu08vXrrO6NUg0jMzVeJBI1o/RNPmPrdnY2HGlKqRaTi8p1sYuEc9jWRK6yf7QIqbL5IJJnaqQ3xbWJKJM03lUGy2PYQebWTw8qY3GtqNyL1/yhfJVIPmllxKr1CaV78ZcTIRPX2oSaSdCMCTMeMbNxATmQMcDT6CpAdUaqNySXL9ruGa6MF7zEVvsqVVBkSxZmPyA0ZF6kV0DvTQceJvNB6l115YfEbaDmRl7LRCH43gyW6cGlO5B1oqz8FhDfb0VkF9NcSfNOMlga3XVdirc/kVlSbWzj0CZeEQU7kcouH62pMFuclsu66RPuFrFastsFqSjWsQrFFdgcIkXPS+6tNhgu3BnJBxzSZVXdSChey32dEF/XYAOXr3clhxiyqS0UOWcV8krymasbOgvT5HPBCZtJsVqH9LD3YU+RuEJBJo8+KMW5+GqqoxBvU3FwvfcXPtmTM6MB2Y8Vf/qICtNqAxUmZOc7xmOR7B47Ptdk3PSOITtN6L5efqz/jKPjUcBwjUZIAeHFurArkzXaKhzXhePWR4DtbaFHdOT3gFvhKvDehtav6fLFX0TFcXiYNYeOnRwuq3mw/i06BNlHyGawuvlZ3syCcxYq+cxCsKtF3NiqmsT4tkBriNrmojAyci8yzncUu2ZVk/E4DsEqm5XKOrPV3LSzTbLS2x3CRnfFypbufWWaQjYZ/KKrfMzr1r+Mks8fjjPEVjj4CN1FWgZXF81Olj634mIw3q+qrsdrwQTnH308VXa5R/e7mlZheb4td9fSDTaocV3BsAiPFBT/xhaFCWlD9aUbqxf1019X2eL0O7LIe6Qm+2vg8nSrVP6s0f9oIo1oGcCWRMsH/bxLlgu++2ZOvnziLU4KCgmrIs814u3aZdTI5WR/lVJmMjgJHEr3Acft9f6g/tr7hL7d/v36/Zln/VW6+xIiveqynu4X6DcNZ983Zx/sOvWVav9+F/IMrKr67/actGTi8da1YhOt/2ZChY3PLi+yKppaU6IAHmB7pG2+fU+qtoUO7iNLkPF88OC5IfAn+8bMsT4efvNZSQkJCQkJCQkJC4p/hf5UYQ1q6MlLEAAAAAElFTkSuQmCC")

    return render(request,'fragview/procReport.html', {'Report': html})

def dataproc_merge(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    outinfo=str(request.GET.get("mergeprocinput")).replace("static","data/visitors")
    
    runList="<br>".join(glob.glob(outinfo+"*/*"))
    
    return render(request,'fragview/dataproc_merge.html', {'datasetsRuns': runList})

def reproc_web(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    
    dataproc = str(request.GET.get("submitProc"))
    outdir=dataproc.split(";")[0]
    data=dataproc.split(";")[1]
    SW=outdir.split(" #")[-1]
    outdir=add_run_DP(outdir)
    if "autoPROC" in SW:
        data=data+" -d "+outdir.split("cd ")[-1].split(" #")[0]
    if "XDSAPP" in SW:
        data=data.replace("xdsapp --cmd","xdsapp --cmd "+" --dir "+outdir.split("cd ")[-1].split(" #")[0])
    
    base_script="""#!/bin/bash\n#!/bin/bash\n#SBATCH -t 99:55:00\n#SBATCH -J FragWeb\n#SBATCH --exclusive\n#SBATCH -N1\n#SBATCH --cpus-per-task=48\n#SBATCH --mem=220000\n#SBATCH -o /data/visitors/biomax/20180489/20190127/fragmax/logs/manual_proc_WebApp_%j.out\n#SBATCH -e /data/visitors/biomax/20180489/20190127/fragmax/logs/manual_proc_WebApp_%j.err\nmodule purge\nmodule load CCP4 XDSAPP autoPROC Phenix BUSTER\n\n{0}\n\n{1}\n""".format(outdir, data)

    with open("/data/visitors/biomax/20180489/20190127/fragmax/scripts/reprocess_webapp.sh","w") as inp:
        inp.write(base_script)

    command ='echo "module purge | module load CCP4 XDSAPP | sbatch /data/visitors/biomax/20180489/20190127/fragmax/scripts/reprocess_webapp.sh " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(command,shell=True)

    proc = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'squeue','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    output=""
    for i in out.decode("UTF-8").split("\n")[1:-1]:
        output+="<tr><td>"+"</td><td>".join(i.split())+"</td></tr>"
    base_script=base_script.replace("\n","<br>")
    return render(request,'fragview/reproc_web.html', {'command': base_script})

def refine_datasets(request):
    userInput=str(request.GET.get("submitrfProc"))
    empty,dimpleSW,fspSW,busterSW,refinemode,mrthreshold,refinerescutoff,userPDB,refspacegroup=userInput.split(";;")
    if "false" in dimpleSW:
        useDIMPLE=False
    else:
        useDIMPLE=True
    if "false" in fspSW:
        useFSP=False
    else:
        useFSP=True
    if "false" in busterSW:
        useBUSTER=False
    else:
        useBUSTER=True
    if len(userPDB)<20:
        pdbmodel=userPDB.replace("pdbmodel:","")
    if "ATOM" in userPDB:
        userPDB=userPDB.replace("pdbmodel:","")
        pdbmodel=path+"fragmax/process/userPDB.pdb"
        with open(path+"fragmax/process/userPDB.pdb","w") as pdbfile:
            pdbfile.write(userPDB)
    spacegroup=refspacegroup.replace("refspacegroup:","")
    # t = threading.Thread(target=run_structure_solving,args=(useDIMPLE, useFSP, useBUSTER, pdbmodel, spacegroup))
    # t.daemon = True
    # t.start()
    run_structure_solving(useDIMPLE, useFSP, useBUSTER, pdbmodel, spacegroup)
    outinfo = "<br>".join(userInput.split(";;"))

    return render(request,'fragview/refine_datasets.html', {'allproc': outinfo})

def ligfit_datasets(request):
    userInput=str(request.GET.get("submitligProc"))
    empty,rhofitSW,ligfitSW,ligandfile,fitprocess,scanchirals,customligfit,ligfromname=userInput.split(";;")
    useRhoFit="False"
    useLigFit="False"
    


    if "true" in rhofitSW:
        useRhoFit="True"
    if "true" in ligfitSW:
        useLigFit="True"
  
    t1 = threading.Thread(target=autoLigandFit,args=(useLigFit,useRhoFit,fraglib,))
    t1.daemon = True
    t1.start()
    return render(request,'fragview/ligfit_datasets.html', {'allproc': "<br>".join(userInput.split(";;"))})

def dataproc_datasets(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    allprc  = str(request.GET.get("submitallProc"))
    dtprc   = str(request.GET.get("submitdtProc"))
    refprc  = str(request.GET.get("submitrfProc"))
    ligproc = str(request.GET.get("submitligProc"))
    if allprc!="None":
        pass
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
        sbatch_script_list=list()
        if usexdsapp=="true":
            t = threading.Thread(target=run_xdsapp,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff))
            t.daemon = True
            t.start()
            
            sbatch_script_list.append(path+"/fragmax/scripts/xdsapp_fragmax_part0.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/xdsapp_fragmax_part1.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/xdsapp_fragmax_part2.sh")
        if usedials=="true":
            t = threading.Thread(target=run_dials,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff))
            t.daemon = True
            t.start()
            
            sbatch_script_list.append(path+"/fragmax/scripts/dials_fragmax_part0.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/dials_fragmax_part1.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/dials_fragmax_part2.sh")
        if useautproc=="true":
            t = threading.Thread(target=run_autoproc,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff))
            t.daemon = True
            t.start()

            sbatch_script_list.append(path+"/fragmax/scripts/autoproc_fragmax_part0.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/autoproc_fragmax_part1.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/autoproc_fragmax_part2.sh")            
        if usexdsxscale=="true":
            t = threading.Thread(target=run_xdsxscale,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff))
            t.daemon = True
            t.start()
            
            sbatch_script_list.append(path+"/fragmax/scripts/xdsxscale_fragmax_part0.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/xdsxscale_fragmax_part1.sh")
            sbatch_script_list.append(path+"/fragmax/scripts/xdsxscale_fragmax_part2.sh")
        
        
        #for script in sbatch_script_list:            
        #    command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        #    subprocess.call(command,shell=True)
        return render(request,'fragview/dataproc_datasets.html', {'allproc': "\n"+"\n".join(sbatch_script_list)})

    
    if refprc!="None":
        pass

    if ligproc!="None":
        pass
    return render(request,'fragview/dataproc_datasets.html', {'allproc': "\n"+"\n".join(sbatch_script_list)})

def kill_HPC_job(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    jobid_k=str(request.GET.get('jobid_kill'))     

    subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'scancel', jobid_k], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    sleep(5)
    proc = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'squeue','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    output=""   


    for i in out.decode("UTF-8").split("\n")[1:-1]:
        proc_info = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'scontrol', 'show', 'jobid', '-dd', i.split()[0]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_info, err_info = proc_info.communicate()
        stdout_file=[x for x in out_info.decode("UTF-8").splitlines() if "StdOut=" in x][0].split("/data/visitors")[-1]
        stderr_file=[x for x in out_info.decode("UTF-8").splitlines() if "StdErr=" in x][0].split("/data/visitors")[-1]
        try:
            prosw=      [x for x in out_info.decode("UTF-8").splitlines() if "#SW=" in x][0].split("#SW=")[-1]
        except:
            prosw="Unkown"
        output+="<tr><td>"+"</td><td>".join(i.split())+"</td><td>"+prosw+"</td><td><a href='/static"+stdout_file+"'> job_"+i.split()[0]+".out</a></td><td><a href='/static"+stderr_file+"'>job_"+i.split()[0]+""".err</a></td><td>
           
        <form action="/hpcstatus_jobkilled/" method="get" id="kill_job_{0}" >
            <button class="btn-small" type="submit" value={0} name="jobid_kill" size="1">Kill</button>
        </form>

        </tr>""".format(i.split()[0])

    # proc_sacct = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'sacct','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # out_sacct, err_sacct = proc_sacct.communicate()
    # sacct=""
    # for a in out_sacct.decode("UTF-8").split("\n")[2:-1]:
    #     linelist=[a[:13],a[13:23],a[23:34],a[34:45],a[45:56],a[56:67],a[67:]]
    #     linelist=[x.replace(" ","") for x in linelist]
    #     sacct+="<tr><td>"+"</td><td>".join(linelist)+"</td></tr>"

    
    
    return render(request,'fragview/hpcstatus_jobkilled.html', {'command': output, 'history': ""})

def hpcstatus(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()


    proc = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'squeue','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    output=""

    


    for i in out.decode("UTF-8").split("\n")[1:-1]:
        proc_info = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'scontrol', 'show', 'jobid', '-dd', i.split()[0]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_info, err_info = proc_info.communicate()
        try:
            stdout_file=[x for x in out_info.decode("UTF-8").splitlines() if "StdOut=" in x][0].split("/data/visitors")[-1]
            stderr_file=[x for x in out_info.decode("UTF-8").splitlines() if "StdErr=" in x][0].split("/data/visitors")[-1]
        except IndexError:
            stdout_file="No_output"
            stderr_file="No_output"

        try:
            prosw=      [x for x in out_info.decode("UTF-8").splitlines() if "#SW=" in x][0].split("#SW=")[-1]
        except:
            prosw="Unkown"
        
        # if not os.path.exists(stdout_file):
        #     output+="<tr><td>"+"</td><td>".join(i.split())+"</td><td>"+prosw+"</td><td>No output</td><td>No output"+"""</a></td><td>
            
        #     <form action="/hpcstatus_jobkilled/" method="get" id="kill_job_{0}" >
        #         <button class="btn-small" type="submit" value={0} name="jobid_kill" size="1">Kill</button>
        #     </form>

        #     </tr>""".format(i.split()[0])
        # else:
        output+="<tr><td>"+"</td><td>".join(i.split())+"</td><td>"+prosw+"</td><td><a href='/static"+stdout_file+"'> job_"+i.split()[0]+".out</a></td><td><a href='/static"+stderr_file+"'>job_"+i.split()[0]+""".err</a></td><td>
        
        <form action="/hpcstatus_jobkilled/" method="get" id="kill_job_{0}" >
            <button class="btn-small" type="submit" value={0} name="jobid_kill" size="1">Kill</button>
        </form>

        </tr>""".format(i.split()[0])

    # proc_sacct = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'sacct','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # out_sacct, err_sacct = proc_sacct.communicate()
    # sacct=""
    # for a in out_sacct.decode("UTF-8").split("\n")[2:-1]:
    #     linelist=[a[:13],a[13:23],a[23:34],a[34:45],a[45:56],a[56:67],a[67:]]
    #     linelist=[x.replace(" ","") for x in linelist]
    #     sacct+="<tr><td>"+"</td><td>".join(linelist)+"</td></tr>"

    

    return render(request,'fragview/hpcstatus.html', {'command': output, 'history': ""})


#####################################################################################
#####################################################################################
########################## REGULAR PYTHON FUNCTIONS #################################
#####################################################################################
#####################################################################################

def add_run_DP(outdir):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    fout=outdir.split("cd ")[-1].split(" #")[0]
    SW=outdir.split(" #")[-1]
    runs=[x for x in glob.glob(fout+"/*") if os.path.isdir(x) and "run_" in x]
    if len(runs)==0:
        last_run=0
    else:
        rlist=[x.split("/")[-1] for x in runs]
        last_run=[int(x.replace("run_","")) for x in natsort.natsorted(rlist)][-1]
    
    next_run=fout+"/run_"+str(last_run+1)
    
    if not os.path.exists(next_run) and "autoPROC" not in SW:
        os.makedirs(next_run, exist_ok=True)

    return "cd "+next_run+" #"+SW

def retrieveParameters(xmlfile):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    #Dictionary with parameters for dataset info template page
    
    with open(xmlfile,"r") as inp:
        a=inp.readlines()

    paramDict=dict()
    paramDict["axisEnd"]=format(float(a[4].split("</")[0].split(">")[1]),".1f")
    paramDict["axisRange"]=format(float(a[5].split("</")[0].split(">")[1]),".1f")
    paramDict["axisStart"]=format(float(a[6].split("</")[0].split(">")[1]),".1f")
    paramDict["beamShape"]=a[7].split("</")[0].split(">")[1]
    paramDict["beamSizeSampleX"]=format(float(a[8].split("</")[0].split(">")[1])*1000,".0f")
    paramDict["beamSizeSampleY"]=format(float(a[9].split("</")[0].split(">")[1])*1000,".0f")
    paramDict["detectorDistance"]=format(float(a[16].split("</")[0].split(">")[1]),".2f")
    paramDict["endTime"]=a[18].split("</")[0].split(">")[1]
    paramDict["exposureTime"]=format(float(a[19].split("</")[0].split(">")[1]),".3f")
    paramDict["flux"]=a[22].split("</")[0].split(">")[1]
    paramDict["imageDirectory"]=a[23].split("</")[0].split(">")[1]
    paramDict["imagePrefix"]=a[24].split("</")[0].split(">")[1]
    paramDict["kappaStart"]=format(float(a[26].split("</")[0].split(">")[1]),".2f")
    paramDict["numberOfImages"]=a[27].split("</")[0].split(">")[1]
    paramDict["overlap"]=format(float(a[29].split("</")[0].split(">")[1]),".1f")
    paramDict["phiStart"]=format(float(a[30].split("</")[0].split(">")[1]),".2f")
    paramDict["resolution"]=format(float(a[32].split("</")[0].split(">")[1]),".2f")
    paramDict["rotatioAxis"]=a[33].split("</")[0].split(">")[1]
    paramDict["runStatus"]=a[34].split("</")[0].split(">")[1]
    paramDict["slitV"]=format(float(a[35].split("</")[0].split(">")[1])*1000,".1f")
    paramDict["slitH"]=format(float(a[36].split("</")[0].split(">")[1])*1000,".1f")
    paramDict["startTime"]=a[38].split("</")[0].split(">")[1]
    paramDict["synchrotronMode"]=a[39].split("</")[0].split(">")[1]
    paramDict["transmission"]=format(float(a[40].split("</")[0].split(">")[1]),".3f")
    paramDict["wavelength"]=format(float(a[41].split("</")[0].split(">")[1]),".6f")
    paramDict["xbeampos"]=format(float(a[42].split("</")[0].split(">")[1]),".2f")
    paramDict["snapshot1"]=a[43].split("</")[0].split(">")[1]
    paramDict["snapshot2"]=a[44].split("</")[0].split(">")[1]
    paramDict["snapshot3"]=a[45].split("</")[0].split(">")[1]
    paramDict["snapshot4"]=a[46].split("</")[0].split(">")[1]
    paramDict["ybeampos"]=format(float(a[47].split("</")[0].split(">")[1]),".2f")
    
    return paramDict

def create_dataColParam(acr, path):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    
    if os.path.exists(path+"/fragmax/process/datacollectionPar.csv"):
        return
    else:
        
        t = threading.Thread(target=ligandToSVG,args=())
        t.daemon = True
        t.start()

        xml_list=glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn*/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")
        img_list=list()
        prf_list=list()
        res_list=list()
        snap_list=list()
        path_list=list()
        acr_list=list()
        png_list=list()
        run_list=list()

        for xml in natsort.natsorted(xml_list):
            with open(xml) as inp:
                    a=inp.readlines()

            for i in a:
                if "numberOfImages" in i:
                    img_list.append(i.split(">")[1].split("<")[0])
                if "resolution" in i:
                    res_list.append("%.2f" % float(i.split(">")[1].split("<")[0])) 
                #if "xtalSnapshotFullPath1" in i:        
                #    snap_list.append(i.split(">")[1].split("<")[0])     
                if "dataCollectionNumber" in i:
                    run_number=i.split(">")[1].split("<")[0]
                    run_list.append(i.split(">")[1].split("<")[0])
                if "imagePrefix" in i:
                    prf=i.split(">")[1].split("<")[0]
                    prf_list.append(prf) 
            #snap_list.append(path.replace("/data/visitors/","/static/")+"/fragmax/process/"+acr+"/"+prf+"/"+prf+"_snapshot.jpg")
            snap_list.append("/static/pyarch/visitors/"+proposal+"/"+shift+"/raw/"+acr+"/"+prf+"/"+prf+"_"+run_number+"_1.snapshot.jpeg")
            os.makedirs(path+"/fragmax/process/"+acr+"/"+prf+"/",exist_ok=True)
            shutil.copyfile(xml,path+"/fragmax/process/"+acr+"/"+prf+"/"+prf+"_1.xml")
            path_list.append(xml.split("xds")[0].replace("process","raw"))
            acr_list.append(acr)
        

        ##
        ##
        ##
        ##HARD CODED LIB
        fraglib="F2XEntry"  
        ##
        ##
        ##
                         
        #Create fragment list png for Datasets view                         
        pngDict=dict()
        for prf in prf_list:
            if "Apo" in prf:
                pngDict[prf]="/static/img/apo.png"
            #elif "Apo" not in prf and "DM" not in prf and "ICC" not in prf:
            #    wellNo=prf.split(acr+"-")[-1]        
            #    pngDict[prf]=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+wellNo+"/"+wellNo+".svg"
            elif fraglib in prf:
                wellNo=prf.split(acr+"-")[-1]        
                pngDict[prf]=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+wellNo+"/"+wellNo+".svg"
            elif "ICC" in prf:
                wellNo=prf.split(acr+"-")[-1]        
                pngDict[prf]=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+"ICCBS"+"/"+wellNo+"/"+wellNo+".svg"
            elif "F2XEntry" in prf:
                wellNo=prf.split(acr+"-")[-1]        
                pngDict[prf]=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+"F2XEntry"+"/"+wellNo+"/"+wellNo+".svg"
            elif "JBS" in prf:
                wellNo=prf.split(acr+"-")[-1]        
                pngDict[prf]=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+"JBS"+"/"+wellNo+"/"+wellNo+".svg"
            
            else:
                pngDict[prf]="/static/img/nolig.png"

        png_list=[pngDict[x] for x in prf_list]
        
        line="sep=,"
        line+="\n"
        line+=",".join(acr_list)
        line+="\n"
        line+=",".join(prf_list)
        line+="\n"
        line+=",".join(res_list)
        line+="\n"
        line+=",".join(img_list)
        line+="\n"
        line+=",".join(path_list)
        line+="\n"
        line+=",".join(snap_list)
        line+="\n"
        line+=",".join(png_list)
        line+="\n"

        line+=",".join(run_list)
        for x in os.listdir(subpath):
            if os.path.isdir(subpath+x+"/fragmax/process/"):
                with open(subpath+x+"/fragmax/process/datacollectionPar.csv","w") as outp:
                    outp.write(line)
        
        

        
def parseLigand_results():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    with open(path+"/fragmax/process/autolig.csv","w") as outp:
            

        for dataset in glob.glob(path+"/fragmax/results/ligandfit/*"):
            if os.path.exists(dataset+"/final.pdb") and "Apo" not in dataset:
                blob=[""]
                resolution="NaN"
                key=dataset.split("/")[-1]
                if "EDNA_proc" in dataset:
                    pipeline="_".join(dataset.split("_")[-3:])
                else:
                    pipeline="_".join(dataset.split("_")[-2:])
                if os.path.exists(dataset+"/rhofit/Hit_corr.log"):
                    with open(dataset+"/rhofit/Hit_corr.log","r") as inp:
                        rhofitscore=inp.readlines()[0].split()[1]               

                if os.path.exists(dataset+"/LigandFit_run_1_/LigandFit_summary.dat"):
                    with open(dataset+"/LigandFit_run_1_/LigandFit_summary.dat","r") as inp:
                        ligfitscore=inp.readlines()[6].split()[2]

                lig=dataset.split(acr+"-")[-1].split("_")[0]
                ligpng=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".svg"

                with open(dataset+"/final.pdb","r") as inp:
                    for line in inp.readlines():
                        if "RESOLUTION RANGE HIGH " in line:

                            resolution=line[-10:].replace(" ","").replace("\n","")

                if os.path.exists(dataset+"/LigandFit_run_1_/LigandFit_run_1_1.log"):
                    with open(dataset+"/LigandFit_run_1_/LigandFit_run_1_1.log","r") as inp:
                        for line in inp.readlines():
                            if line.startswith(" lig_xyz"):
                                blob=line.split("lig_xyz ")[-1].replace("\n","")


                l='''<tr>
                <td>
                <form action="/dual_density/" method="get" id="%s_form" target="_blank">
                <button class="btn" type="submit" value="%s;%s" name="ligfit_dataset" size="1">Open Dual Viewer</button>
                </form>
                </td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>
                
                
                
                <a href=%s target="_blank">

                    <img class="ligpng" id="ligand" src=%s onerror="if (this.src != '/static/blog/nopic/noloop.png') this.src='/static/blog/nopic/noloop.png';" height="115" >

                </a>
                </td>  
                </tr>
                ''' % (key,key,blob,key,resolution,rhofitscore,ligfitscore,ligpng,ligpng)

                outp.write(l)                                                                 


def panddaResultSummary():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    fix_pandda_symlinks
    tpandda = threading.Thread(target=fix_pandda_symlinks, args=())
    tpandda.start()

    acr_list=glob.glob(subpath+"*/fragmax/results/"+acr+"*")
    pipeline_dict=dict()
    for acr in acr_list:
        pipeline_dict[acr.split("/")[-1]]=glob.glob(acr+"/*")

    dimple_dict=dict()
    fspipe_dict=dict()

    for key,value in pipeline_dict.items():
        l=list()
        for dtprc in value:        
            if os.path.exists(dtprc+"/dimple/dimple.log"):
                l.append(dtprc+"/dimple/dimple.log")
        dimple_dict[key]=l
        m=list()
        for dtprc in value:        
            if os.path.isdir(dtprc+"/fspipeline"):
                m.append(glob.glob(dtprc+"/fspipeline/final*pdb")[0])
        fspipe_dict[key]=m


    fspline=""
    dimpleline=""
    sortedline=""

    sortedacr=[x for x in natsort.natsorted(set(list(fspipe_dict.keys())+list(dimple_dict.keys()))) if "Apo" not in x and "DM" not in x]
    sortedacr+=[x for x in natsort.natsorted(set(list(fspipe_dict.keys())+list(dimple_dict.keys()))) if "Apo" in x or "DM" in x]



    for key,value in natsort.natsorted(fspipe_dict.items()):
        for f in value:
            fspline+=fsp_info(f)+"\n"

    for key,value in natsort.natsorted(dimple_dict.items()):
        for f in value:
            dimpleline+=dpl_info(f)+"\n"

    dl=fspline.split("\n")+dimpleline.split("\n")            
    for i in sortedacr:
        for j in dl:
            if i in j:
                sortedline+=j+"\n"            

    with open(path+"/fragmax/process/panddarefsum.csv","w") as outp:
        outp.write(sortedline)

def fsp_info_general(entry):
    usracr=""
    spg=""
    res=""
    r_work=""
    r_free=""
    bonds=""
    angles=""
    blob=""
    sigma=""
    a=""
    b=""
    c=""
    alpha=""
    beta=""
    gamma=""
    blist=""    
    usracr=entry.split("/results/")[1].split("/")[0]+entry.split(entry.split("/results/")[1].split("/")[0])[-1].split("_merged.pdb")[0]+"_fspipeline"
    #usrpdbpath= line.replace("data_file: ","")
    with open("/".join(entry.split("/")[:-1])+"/mtz2map.log","r") as inp:
        blobs_log=inp.readlines()
    with open(entry,"r") as inp:
        pdb_file=inp.readlines()
    
    for line in pdb_file:
        if "REMARK Final:" in line:            
            r_work=line.split()[4]
            r_free=line.split()[7]
            r_free=str("{0:.2f}".format(float(r_free)))
            r_work=str("{0:.2f}".format(float(r_work)))
            bonds=line.split()[10]
            angles=line.split()[13]
        if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
            res=line.split(":")[-1].replace(" ","").replace("\n","")
            res=str("{0:.2f}".format(float(res)))
        if "CRYST1" in line:
            #a,b,c,alpha,beta,gamma=line.split(" ")[1:-4]
            a=line[9:15]
            b=line[18:24]
            c=line[27:33]
            alpha=line[34:40]
            beta=line[41:47]
            gamma=line[48:54]
            a=str("{0:.2f}".format(float(a)))
            b=str("{0:.2f}".format(float(b)))
            c=str("{0:.2f}".format(float(c)))

            spg="".join(line.split()[-4:])
            
    with open("/".join(entry.split("/")[:-1])+"/blobs.log","r") as inp:
        blobs_log=inp.readlines()
    for line in blobs_log:
        if "using sigma cut off " in line:
            sigma=line.split("cut off")[-1].replace(" ","").replace("\n","")
        if "INFO:: cluster at xyz = " in line:
            blob=line.split("(")[-1].split(")")[0].replace("  ","").replace("\n","")
            blob="["+blob+"]"
            blist=blob+"<br>"+blist
        #print(blist)
    blist="<br>".join(blist.split("<br>")[:3])
    try:
    
        with open("/".join(entry.split("/")[:-1])+"/mtz2map.log","r") as inp:
            for mline in inp.readlines():
                if "_2mFo-DFc.ccp4" in mline:
                    pdbout  ="/".join(entry.split("/")[:-1])[15:]+"/"+mline.split("/")[-1].replace("\n","").replace("_2mFo-DFc.ccp4",".pdb")
                    event1  ="/".join(entry.split("/")[:-1])[15:]+"/"+mline.split("/")[-1].replace("\n","")
                    ccp4_nat="/".join(entry.split("/")[:-1])[15:]+"/"+mline.split("/")[-1].replace("\n","").replace("_2mFo-DFc.ccp4","_mFo-DFc.ccp4")
            
        
        #pdbout="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final.pdb"
        #event1="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_2mFo-DFc.ccp4"
        #ccp4_nat="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_mFo-DFc.ccp4"
        tr= """<tr><td><form action="/density/" method="get" id="%s_form" target="_blank"><button class="btn" type="submit" value="%s"  name="structure" size="1" >Open</button></form></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>""".replace("        ","").replace("\n","")%(usracr,pdbout+";"+event1+";"+ccp4_nat+";"+blist.replace("<br>",",").replace(" ",""),usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,sigma)
    except:
        pdbout="None"
        event1="None"
        ccp4_nat="None"
        tr= """<tr><td></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>""".replace("        ","").replace("\n","")%(usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blob,sigma)
    
    return tr

def dpl_info_general(entry):
    usracr=""
    spg=""
    res=""
    r_work=""
    r_free=""
    bonds=""
    angles=""
    blob=""
    sigma=""
    a=""
    b=""
    c=""
    alpha=""
    beta=""
    gamma=""
    
    with open(entry,"r") as inp:
        dimple_log=inp.readlines()
    for n,line in enumerate(dimple_log):
        if "data_file: " in line:
            usracr=line.split("/")[-3]+"_"+line.split("/")[-2]+"_dimple"
            usracr=usracr.replace(".mtz","")   
            usrpdbpath= line.replace("data_file: ","")
        if "# MTZ " in line:
            spg=line.split(")")[1].split("(")[0].replace(" ","")
            a,b,c,alpha,beta,gamma=line.split(")")[1].split("(")[-1].replace(" ","").split(",")
            alpha=str("{0:.2f}".format(float(alpha)))
            beta=str("{0:.2f}".format(float(beta)))
            gamma=str("{0:.2f}".format(float(gamma)))
        
        if line.startswith("info:") and "R/Rfree" in line:
            r_work,r_free=line.split("->")[-1].replace("\n","").replace(" ","").split("/")
            r_free=str("{0:.2f}".format(float(r_free)))
            r_work=str("{0:.2f}".format(float(r_work)))
        if line.startswith( "density_info: Density"):
            sigma=line.split("(")[-1].split(" sigma")[0]
        if line.startswith("blobs: "):
            l=""
            l=ast.literal_eval(line.split(":")[-1].replace(" ",""))
            blob="<br>".join(map(str,l[:]))
            blob5="<br>".join(map(str,l[:5]))
        if line.startswith("#     RMS: "):
            bonds,angles=line.split()[5],line.split()[9]
        if line.startswith("info: resol. "):
            res=line.split()[2]
            res=str("{0:.2f}".format(float(res)))
    
    try:        
        
        pdbout="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final.pdb"
        event1="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_2mFo-DFc.ccp4"
        ccp4_nat="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_mFo-DFc.ccp4"
        if os.path.exists("/data/visitors/"+pdbout):
            tr= """<tr><td><form action="/density/" method="get" id="%s_form" target="_blank"><button class="btn" type="submit" value="%s"  name="structure" size="1" >Open</button></form></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"""%(usracr,pdbout+";"+event1+";"+ccp4_nat+";"+blob.replace("<br>",",").replace(" ",""),usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blob5,sigma)
        else:
            tr=""
    except:    
        pdbout="None"
        event1="None"
        ccp4_nat="None"
        if os.path.exists("/data/visitors/"+pdbout):
            tr= """<tr><td>No structure</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>NO</td></tr>"""%(usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blob,sigma)
        else:
            tr=""
    return tr

def dpl_info(entry):
    usracr=""
    spg=""
    res=""
    r_work=""
    r_free=""
    bonds=""
    angles=""
    blob=""
    sigma=""
    a=""
    b=""
    c=""
    alpha=""
    beta=""
    gamma=""
    
    with open(entry,"r") as inp:
        dimple_log=inp.readlines()
    for n,line in enumerate(dimple_log):
        if "data_file: " in line:
            usracr=line.split("/")[-1].split("_merged.pdb")[0].split("_unmerged_unscaled.mtz")[0].replace("\n","")+"_dimple"
        if "# MTZ " in line:
            spg=line.split(")")[1].split("(")[0].replace(" ","")
            a,b,c,alpha,beta,gamma=line.split(")")[1].split("(")[-1].replace(" ","").split(",")
            alpha=str("{0:.2f}".format(float(alpha)))
            beta=str("{0:.2f}".format(float(beta)))
            gamma=str("{0:.2f}".format(float(gamma)))
        if line.startswith( "info:  8/8   R/Rfree"):
            r_work,r_free=line.split("->")[-1].replace("\n","").replace(" ","").split("/")
            r_free=str("{0:.2f}".format(float(r_free)))
            r_work=str("{0:.2f}".format(float(r_work)))
        if line.startswith( "density_info: Density"):
            sigma=line.split("(")[-1].split(" sigma")[0]
        if line.startswith("blobs: "):
            l=""
            l=ast.literal_eval(line.split(":")[-1].replace(" ",""))
            blob="<br>".join(map(str,l[:3]))
            #print(blob)
        if line.startswith("#     RMS: "):
            bonds,angles=line.split()[5],line.split()[9]
        if line.startswith("info: resol. "):
            res=line.split()[2]
            res=str("{0:.2f}".format(float(res)))
    try:
        pdbout=[x for x in glob.glob(path+panddaprocessed+usracr+"/*/*.pdb") if "fitted" not in x and "ligand" not in x][0].replace("/data/visitors/","")
        event1=[x for x in glob.glob(path+panddaprocessed+usracr+"/*.ccp4") if "event_1" in x][0].replace("/data/visitors/","")
        ccp4_nat=[x for x in glob.glob(path+panddaprocessed+usracr+"/*.ccp4") if "z_map.native" in x][0].replace("/data/visitors/","")
        tr= """<tr><td><form action="/pandda_density/" method="get" id="%s_form" target="_blank"><input type="hidden" value="%s" name="structure" size="1"/><a href="javascript:{}" onclick="document.getElementById('%s_form').submit();"></form>%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>YES</td></tr>"""%(usracr,pdbout+";"+event1+";"+ccp4_nat+";"+blob.split("<br>")[0],usracr,usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blob,sigma)

    except:
        pdbout="None"
        event1="None"
        ccp4_nat="None"
        tr= """<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>NO</td></tr>"""%(usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blob,sigma)
    return tr

def fsp_info(entry):
    usracr=""
    spg=""
    res=""
    r_work=""
    r_free=""
    bonds=""
    angles=""
    blob=""
    sigma=""
    a=""
    b=""
    c=""
    alpha=""
    beta=""
    gamma=""
    blist=""    
    usracr=entry.split("/results/")[1].split("/")[0]+entry.split(entry.split("/results/")[1].split("/")[0])[-1].split("_merged.pdb")[0]+"_fspipeline"
    with open(entry,"r") as inp:
        pdb_file=inp.readlines()
    
    for line in pdb_file:
        if "REMARK Final:" in line:            
            r_work=line.split()[4]
            r_free=line.split()[7]
            r_free=str("{0:.2f}".format(float(r_free)))
            r_work=str("{0:.2f}".format(float(r_work)))
            bonds=line.split()[10]
            angles=line.split()[13]
        if "REMARK   3   RESOLUTION RANGE HIGH (ANGSTROMS) :" in line:
            res=line.split(":")[-1].replace(" ","").replace("\n","")
            res=str("{0:.2f}".format(float(res)))
        if "CRYST1" in line:
            a,b,c,alpha,beta,gamma=line.split()[1:-4]
            a=str("{0:.2f}".format(float(a)))
            b=str("{0:.2f}".format(float(b)))
            c=str("{0:.2f}".format(float(c)))

            spg="".join(line.split()[-4:])
            
    with open("/".join(entry.split("/")[:-1])+"/blobs.log","r") as inp:
        blobs_log=inp.readlines()
    for line in blobs_log:
        if "using sigma cut off " in line:
            sigma=line.split("cut off")[-1].replace(" ","").replace("\n","")
        if "INFO:: cluster at xyz = " in line:
            blob=line.split("(")[-1].split(")")[0].replace("  ","").replace("\n","")
            blob="["+blob+"]"
            blist=blob+"<br>"+blist
        #print(blist)
    try:
        pdbout=[x for x in glob.glob(path+panddaprocessed+usracr+"/*/*.pdb") if "fitted" not in x and "ligand" not in x][0].replace("/data/visitors/","")
        event1=[x for x in glob.glob(path+panddaprocessed+usracr+"/*.ccp4") if "event_1" in x][0].replace("/data/visitors/","")
        ccp4_nat=[x for x in glob.glob(path+panddaprocessed+usracr+"/*.ccp4") if "z_map.native" in x][0].replace("/data/visitors/","")
        tr= """<tr><td><form action="/pandda_density/" method="get" id="%s_form" target="_blank"><input type="hidden" value="%s" name="structure" size="1"/><a href="javascript:{}" onclick="document.getElementById('%s_form').submit();"></form>%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>YES</td></tr>""".replace("        ","").replace("\n","")%(usracr,pdbout+";"+event1+";"+ccp4_nat+";"+blob.split("<br>")[0],usracr,usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,sigma)
    except:
        pdbout="None"
        event1="None"
        ccp4_nat="None"
        tr= """<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>NO</td></tr>""".replace("        ","").replace("\n","")%(usracr,spg,res,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blob,sigma)
    
    return tr
#fsp_info("/data/visitors/biomax/20180479/20190323/fragmax/results/ProteinaseK-JBSE7_1/xdsapp/fspipeline/final_13_ProteinaseK-JBSE7_1_xdsapp_merged.pdb")

def resultSummary():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    
    #acr_list=glob.glob(subpath+"*/fragmax/results/"+acr+"**")
    acr_list=glob.glob(path+"*/fragmax/results/"+acr+"**")
    pipeline_dict=dict()
    for pacr in acr_list:
        pipeline_dict[pacr.split("/")[-1]]=glob.glob(pacr+"/**")

    dimple_dict=dict()
    fspipe_dict=dict()

    for key,value in pipeline_dict.items():
        l=list()
        for dtprc in value:        
            if os.path.exists(dtprc+"/dimple/dimple.log"):
                l.append(dtprc+"/dimple/dimple.log")
        dimple_dict[key]=l
        m=list()
        for dtprc in value:        
            if os.path.isdir(dtprc+"/fspipeline"):
                m.append(glob.glob(dtprc+"/fspipeline/final**pdb")[0])
        fspipe_dict[key]=m


    fspline=""
    dimpleline=""
    sortedline=""

    sortedacr=[x for x in natsort.natsorted(set(list(fspipe_dict.keys())+list(dimple_dict.keys()))) if "Apo" not in x and "DM" not in x]
    sortedacr+=[x for x in natsort.natsorted(set(list(fspipe_dict.keys())+list(dimple_dict.keys()))) if "Apo" in x or "DM" in x]



    for key,value in natsort.natsorted(fspipe_dict.items()):
        for f in value:            
            fspline+=fsp_info_general(f)+"\n"

    for key,value in natsort.natsorted(dimple_dict.items()):
        for f in value:
            dimpleline+=dpl_info_general(f)+"\n"

    dl=fspline.split("\n")+dimpleline.split("\n")            
    for i in sortedacr:
        for j in dl:
            if i in j:
                sortedline+=j+"\n"            


    with open(path+"/fragmax/process/generalrefsum.csv","w") as outp:
        outp.write(sortedline)

def hdf2jpg(paramDict):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    #generate two diffraction JPG: 1st image, half-th dataset
    #saves in fragmax/process folder
    
    imgdir,frames,prefix=paramDict["imageDirectory"],paramDict["numberOfImages"],paramDict["imagePrefix"]
    if imgdir[-1]!="/":
        imgdir+="/"
    
    h5master=glob.glob(imgdir+"*master.h5")[0]
    imglist=[str(1),str(int(frames)/2)]
    print("Converting to JPG")
    def convert(imgnb):
       name=h5master.split("_master")[0]

       converto2cbf="eiger2cbf "+h5master+" "+imgnb+" "+name+"_"+imgnb+".cbf"
       subprocess.call(converto2cbf, shell=True)



       convert2jpeg="diff2jpeg "+name+"_"+imgnb+".cbf"
       subprocess.call(convert2jpeg, shell=True)


       clean_up="rm "+name+"_"+imgnb+".cbf"
       subprocess.call(clean_up, shell=True)
       
       mvtofragmax="mv "+imgdir+"*.jpg "+path+"/fragmax/process/"+acr+"/"+prefix+"/"
       subprocess.call(mvtofragmax, shell=True)


    for i in imglist:        
        t = threading.Thread(target=convert, args=(i,))
        t.start()

def run_xdsapp(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()


    def listdir_fullpath(d):
        return [os.path.join(d, f) for f in os.listdir(d)]


    # In[5]:


    ##Start up definitions



    proteinNames      = dict() 
    proteinNames_path = dict()
    datasets          = dict()
    scriptList        = list()

    acronyms=os.listdir(path+"/raw/") #list acronym for collected data

    acronyms=[x for x in acronyms if "DS_Store" not in x]


    for acronym in acronyms: 
            #creat a dict of protein names
            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) 
            #create a dict of protein names with full path to the dir
            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) 

    for collectedProteins in proteinNames_path.values():
            for proteinName in collectedProteins:
                    #create a dict of keys:proteinNames, values:master files - 
                    datasets[proteinName] = glob.glob(proteinName+"/*master.h5") 


    # In[6]:



    def images_collected(h5image):
        f=h5py.File(h5image,"r")
        return int(f.get("entry/sample/goniometer/omega_range_total").value/f.get("entry/sample/goniometer/omega_increment").value)


    # In[7]:


    def split(a, n):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


    # In[8]:


    def createScript(ind, outd, fromImage, toImage,dataName):
            if "/Volumes/offline-visitors" in dataName:
                dataName =dataName.replace("/Volumes/offline-","/data/")
                ind      =ind.replace     ("/Volumes/offline-","/data/")
                outd     =outd.replace    ("/Volumes/offline-","/data/")

            fromImage=str(fromImage)
            toImage=str(toImage)
            #create empty string to start the script
            content=""
            content="\n"
            content="\n"

            xdsappcontent   = content



            # XDSAPP definitions 
            xdsappcontent+="cd "+outd+"/xdsapp"
            xdsappcontent+="\n"
            xdsappcontent+='xdsapp --cmd --dir='+outd+'/xdsapp -j 8 -c 6 -i '+ind+'  --fried='+friedel+' --range='+fromImage+'\ '+toImage+' '
            xdsappcontent+="\n"                    

            return xdsappcontent



    # In[9]:


    def create_headers():
        #init variables
        xdsappOut    = ""    

        #define env for script for XDSAPP
        xdsappOut+= """#!/bin/bash\n"""
        xdsappOut+= """#!/bin/bash\n"""
        xdsappOut+= """#SBATCH -t 99:55:00\n"""
        xdsappOut+= """#SBATCH -J XDSAPP\n"""
        xdsappOut+= """#SBATCH --exclusive\n"""
        xdsappOut+= """#SBATCH -N1\n"""
        xdsappOut+= """#SBATCH --cpus-per-task=48\n"""
        xdsappOut+= """#SBATCH --mem=220000\n""" 
        xdsappOut+= """#SBATCH -o """+path+"""/fragmax/logs/xdsapp_fragmax_%j.out\n"""
        xdsappOut+= """#SBATCH -e """+path+"""/fragmax/logs/xdsapp_fragmax_%j.err\n"""    
        xdsappOut+= """module purge\n\n"""
        xdsappOut+= """module load CCP4 XDSAPP\n\n"""


        return xdsappOut





    # In[10]:


    def prepareFolder(proteinDict=proteinNames): 

            os.makedirs(path+"/fragmax/process", exist_ok=True)
            os.makedirs(path+"/fragmax/scripts", exist_ok=True)
            os.makedirs(path+"/fragmax/logs"   , exist_ok=True)


    # In[11]:


    def processHDF5(userAcronym=None, userProtein=None):
            collectedImages=dict()

            if userAcronym and userProtein:
                if userAcronym in acronyms:
                    for acronym in userAcronym: 
                        try:
                            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) #creat a dict of protein names
                            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) #create a dict of protein names with full path to the dir

                            for collectedProteins in proteinNames_path.values():
                                    for proteinName in collectedProteins:
                                            if userProtein==proteinName:
                                                datasets[proteinName] = glob.glob(proteinName+"/*master.h5") #create a dict of keys:proteinNames, values:master files - 


                            for key,value in datasets.items():     
                                    for i in value:
                                            n = images_collected(i)
                                            if n>4:
                                                    collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way
                        except:
                            print("No dataset with the given name was found. Please check the list of datasets with the provided acronym:")
                            for i in os.listdir(path+"/raw/"+userAcronym):
                                print(i)
                            break
                else:
                    print("Acronym given is not valid. Please check the list of acronyms available")
                    print("for you proposal and date\n")
                    for i in acronyms:
                        print(i)


            else:
                for key,value in datasets.items():     
                        for i in value:
                                n = images_collected(i)
                                if n>4:
                                        collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way

            return collectedImages

    def runFragMAX(path=path):
        # FragMAX running script
        prepareFolder() # create folder system for reprocessing files
        nodes=3 #nodes per pipeline


        images = processHDF5()

        xdsappHeader=create_headers()

        scriptList=list()

        for masterFile, totalFrames in images.items():    
            #output dir for each protein separate
            outdir=masterFile.split("raw")[0]+"fragmax/process"+masterFile.split("raw")[1].split("_master.h5")[0]        
            os.makedirs(outdir+"/xdsapp",exist_ok=True)

            #get the real number of data existing in the directory
            dataN=outdir+"/"+outdir.split("/")[-1]

            #Create scripts for HPC for each dataset, with custom dataframe number and outdirs
            xdsappOut=createScript(masterFile,outdir, 1, totalFrames,dataN)    
            scriptList.append(xdsappOut)

        #Create partial HPC scripts to submmit to several nodes at same time
        #nodes=3
        chunkScripts=[xdsappHeader+"".join(x) for x in list(split(scriptList,nodes) )]


        for num,chunk in enumerate(chunkScripts):
            with open(path+"/fragmax/scripts/xdsapp_fragmax_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)
            
            script=path+"/fragmax/scripts/xdsapp_fragmax_part"+str(num)+".sh"
            command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)



    runFragMAX()

def run_autoproc(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()


    def listdir_fullpath(d):
        return [os.path.join(d, f) for f in os.listdir(d)]


    ##Start up definitions

    proteinNames      = dict() 
    proteinNames_path = dict()
    datasets          = dict()
    scriptList        = list()

    acronyms=os.listdir(path+"/raw/") #list acronym for collected data

    acronyms=[x for x in acronyms if "DS_Store" not in x]


    for acronym in acronyms: 
            #creat a dict of protein names
            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) 
            #create a dict of protein names with full path to the dir
            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) 

    for collectedProteins in proteinNames_path.values():
            for proteinName in collectedProteins:
                    #create a dict of keys:proteinNames, values:master files - 
                    datasets[proteinName] = glob.glob(proteinName+"/*master.h5") 



    def images_collected(h5image):
        f=h5py.File(h5image,"r")
        return int(f.get("entry/sample/goniometer/omega_range_total").value/f.get("entry/sample/goniometer/omega_increment").value)


    def split(a, n):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))



    def createScript(ind, outd, fromImage, toImage,dataName):
            if "/Volumes/offline-visitors" in dataName:
                dataName =dataName.replace("/Volumes/offline-","/data/")
                ind      =ind.replace     ("/Volumes/offline-","/data/")
                outd     =outd.replace    ("/Volumes/offline-","/data/")

            fromImage=str(fromImage)
            toImage=str(toImage)
            #create empty string to start the script
            content=""
            content="\n"
            content="\n"

            autoproccontent = content



            # autoPROC definitions             
            autoproccontent+="\n"
            autoproccontent+='''process -h5 '''+ind+''' -noANO autoPROC_XdsKeyword_LIB=\$EBROOTNEGGIA/lib/dectris-neggia.so autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=6 autoPROC_XdsKeyword_DATA_RANGE='''+fromImage+'''\ '''+toImage+''' autoPROC_XdsKeyword_SPOT_RANGE='''+fromImage+'''\ '''+toImage+''' -d '''+outd+'''/autoproc'''
            autoproccontent+="\n"                    

            
            
            
            return autoproccontent



    def create_headers():
        #init variables
        autoprocOut    = ""    

        #define env for script for autoPROC
        autoprocOut+= """#!/bin/bash\n"""
        autoprocOut+= """#!/bin/bash\n"""
        autoprocOut+= """#SBATCH -t 99:55:00\n"""
        autoprocOut+= """#SBATCH -J autoPRC\n"""
        autoprocOut+= """#SBATCH --exclusive\n"""
        autoprocOut+= """#SBATCH -N1\n"""
        autoprocOut+= """#SBATCH --cpus-per-task=48\n"""
        autoprocOut+= """#SBATCH --mem=220000\n""" 
        autoprocOut+= """#SBATCH -o """+path+"""/fragmax/logs/autoproc_fragmax_%j.out\n"""
        autoprocOut+= """#SBATCH -e """+path+"""/fragmax/logs/autoproc_fragmax_%j.err\n"""    
        autoprocOut+= """module purge\n\n"""
        autoprocOut+= """module load CCP4 autoPROC\n\n"""


        return autoprocOut



    def prepareFolder(proteinDict=proteinNames): 

            os.makedirs(path+"/fragmax/process", exist_ok=True)
            os.makedirs(path+"/fragmax/scripts", exist_ok=True)
            os.makedirs(path+"/fragmax/logs"   , exist_ok=True)



    def processHDF5(userAcronym=None, userProtein=None):
            collectedImages=dict()

            if userAcronym and userProtein:
                if userAcronym in acronyms:
                    for acronym in userAcronym: 
                        try:
                            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) #creat a dict of protein names
                            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) #create a dict of protein names with full path to the dir

                            for collectedProteins in proteinNames_path.values():
                                    for proteinName in collectedProteins:
                                            if userProtein==proteinName:
                                                datasets[proteinName] = glob.glob(proteinName+"/*master.h5") #create a dict of keys:proteinNames, values:master files - 


                            for key,value in datasets.items():     
                                    for i in value:
                                            n = images_collected(i)
                                            if n>4:
                                                    collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way
                        except:
                            print("No dataset with the given name was found. Please check the list of datasets with the provided acronym:")
                            for i in os.listdir(path+"/raw/"+userAcronym):
                                print(i)
                            break
                else:
                    print("Acronym given is not valid. Please check the list of acronyms available")
                    print("for you proposal and date\n")
                    for i in acronyms:
                        print(i)


            else:
                for key,value in datasets.items():     
                        for i in value:
                                n = images_collected(i)
                                if n>4:
                                        collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way

            return collectedImages


    # In[12]:


    def runFragMAX(path=path):
        # FragMAX running script
        prepareFolder() # create folder system for reprocessing files
        nodes=3 #nodes per pipeline

        images = processHDF5()

        autoPROCHeader=create_headers()

        scriptList=list()

        for masterFile, totalFrames in images.items():    
            #output dir for each protein separate
            outdir=masterFile.split("raw")[0]+"fragmax/process"+masterFile.split("raw")[1].split("_master.h5")[0]        
            os.makedirs(outdir,exist_ok=True)

            #get the real number of data existing in the directory
            dataN=outdir+"/"+outdir.split("/")[-1]

            #Create scripts for HPC for each dataset, with custom dataframe number and outdirs
            autoprocOut=createScript(masterFile,outdir, 1, totalFrames,dataN)    
            scriptList.append(autoprocOut)

        #Create partial HPC scripts to submmit to several nodes at same time
        nodes=3
        chunkScripts=[autoPROCHeader+"".join(x) for x in list(split(scriptList,nodes) )]

        for num,chunk in enumerate(chunkScripts):
            with open(path+"/fragmax/scripts/autoproc_fragmax_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)
            script=path+"/fragmax/scripts/autoproc_fragmax_part"+str(num)+".sh"
            command ='echo "module purge | module load CCP4 autoPROC DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)

    runFragMAX()

def run_xdsxscale(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()



    def listdir_fullpath(d):
        return [os.path.join(d, f) for f in os.listdir(d)]


    ##Start up definitions



    proteinNames      = dict() 
    proteinNames_path = dict()
    datasets          = dict()
    scriptList        = list()

    acronyms=os.listdir(path+"/raw/") #list acronym for collected data

    acronyms=[x for x in acronyms if "DS_Store" not in x]


    for acronym in acronyms: 
            #creat a dict of protein names
            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) 
            #create a dict of protein names with full path to the dir
            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) 

    for collectedProteins in proteinNames_path.values():
            for proteinName in collectedProteins:
                    #create a dict of keys:proteinNames, values:master files - 
                    datasets[proteinName] = glob.glob(proteinName+"/*master.h5") 





    def images_collected(h5image):
        f=h5py.File(h5image,"r")
        return int(f.get("entry/sample/goniometer/omega_range_total").value/f.get("entry/sample/goniometer/omega_increment").value)




    def split(a, n):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))




    def createScript(ind, outd, fromImage, toImage,dataName):
            if "/Volumes/offline-visitors" in dataName:
                dataName =dataName.replace("/Volumes/offline-","/data/")
                ind      =ind.replace     ("/Volumes/offline-","/data/")
                outd     =outd.replace    ("/Volumes/offline-","/data/")

            fromImage=str(fromImage)
            toImage=str(toImage)
            #create empty string to start the script
            content=""
            content="\n"
            content="\n"

            dialscontent   = content



            #DIALS definitions


            dialscontent+="cd "+outd+"/xdsxscale "
            dialscontent+="\n"
            dialscontent+="xia2 goniometer.axes=0,1,0  "                
            dialscontent+="    pipeline=3dii failover=true  nproc=48"                
            dialscontent+="    image="+ind+":"+fromImage+":"+toImage+"  "                
            dialscontent+="    multiprocessing.mode=serial  "                
            dialscontent+="    multiprocessing.njob=1  "                
            dialscontent+='    multiprocessing.nproc=auto'                
            dialscontent+="\n"

            return dialscontent





    def create_headers():
        #init variables
        dialsOut    = ""    

        #define env for script for DIALS
        dialsOut+= """#!/bin/bash\n"""
        dialsOut+= """#!/bin/bash\n"""
        dialsOut+= """#SBATCH -t 99:55:00\n"""
        dialsOut+= """#SBATCH -J XDSXSCALE\n"""
        dialsOut+= """#SBATCH --exclusive\n"""
        dialsOut+= """#SBATCH -N1\n"""
        dialsOut+= """#SBATCH --cpus-per-task=48\n"""
        dialsOut+= """#SBATCH --mem=220000\n""" 
        dialsOut+= """#SBATCH -o """+path+"""/fragmax/logs/xdsxscale_fragmax_%j.out\n"""
        dialsOut+= """#SBATCH -e """+path+"""/fragmax/logs/xdsxscale_fragmax_%j.err\n"""    
        dialsOut+= """module purge\n\n"""
        dialsOut+= """module load CCP4 DIALS/1.12.3-PReSTO\n\n"""

        return dialsOut


    def prepareFolder(proteinDict=proteinNames): 

            os.makedirs(path+"/fragmax/process", exist_ok=True)
            os.makedirs(path+"/fragmax/scripts", exist_ok=True)
            os.makedirs(path+"/fragmax/logs"   , exist_ok=True)


    def processHDF5(userAcronym=None, userProtein=None):
            collectedImages=dict()

            if userAcronym and userProtein:
                if userAcronym in acronyms:
                    for acronym in userAcronym: 
                        try:
                            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) #creat a dict of protein names
                            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) #create a dict of protein names with full path to the dir

                            for collectedProteins in proteinNames_path.values():
                                    for proteinName in collectedProteins:
                                            if userProtein==proteinName:
                                                datasets[proteinName] = glob.glob(proteinName+"/*master.h5") #create a dict of keys:proteinNames, values:master files - 


                            for key,value in datasets.items():     
                                    for i in value:
                                            n = images_collected(i)
                                            if n>4:
                                                    collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way
                        except:
                            print("No dataset with the given name was found. Please check the list of datasets with the provided acronym:")
                            for i in os.listdir(path+"/raw/"+userAcronym):
                                print(i)
                            break
                else:
                    print("Acronym given is not valid. Please check the list of acronyms available")
                    print("for you proposal and date\n")
                    for i in acronyms:
                        print(i)


            else:
                for key,value in datasets.items():     
                        for i in value:
                                n = images_collected(i)
                                if n>4:
                                        collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way

            return collectedImages




    def runFragMAX(useDIALS=True, path=path):
        # FragMAX running script
        prepareFolder() # create folder system for reprocessing files
        nodes=3 #nodes per pipeline

        images = processHDF5()

        dialsOut=create_headers()

        scriptList=list()

        for masterFile, totalFrames in images.items():    
            #output dir for each protein separate
            outdir=masterFile.split("raw")[0]+"fragmax/process"+masterFile.split("raw")[1].split("_master.h5")[0]        
            os.makedirs(outdir+"/xdsxscale",exist_ok=True)

            #get the real number of data existing in the directory
            dataN=outdir+"/"+outdir.split("/")[-1]

            #Create scripts for HPC for each dataset, with custom dataframe number and outdirs
            dialsScript=createScript(masterFile,outdir, 1, totalFrames,dataN)    
            scriptList.append(dialsScript)

        #Create partial HPC scripts to submmit to several nodes at same time
        nodes=3
        chunkScripts=[dialsOut+"".join(x) for x in list(split(scriptList,nodes) )]


        for num,chunk in enumerate(chunkScripts):
            with open(path+"/fragmax/scripts/xdsxscale_fragmax_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)
            script=path+"/fragmax/scripts/xdsxscale_fragmax_part"+str(num)+".sh"
            command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)

    runFragMAX()

def run_dials(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()



    def listdir_fullpath(d):
        return [os.path.join(d, f) for f in os.listdir(d)]


    ##Start up definitions



    proteinNames      = dict() 
    proteinNames_path = dict()
    datasets          = dict()
    scriptList        = list()

    acronyms=os.listdir(path+"/raw/") #list acronym for collected data

    acronyms=[x for x in acronyms if "DS_Store" not in x]


    for acronym in acronyms: 
            #creat a dict of protein names
            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) 
            #create a dict of protein names with full path to the dir
            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) 

    for collectedProteins in proteinNames_path.values():
            for proteinName in collectedProteins:
                    #create a dict of keys:proteinNames, values:master files - 
                    datasets[proteinName] = glob.glob(proteinName+"/*master.h5") 





    def images_collected(h5image):
        f=h5py.File(h5image,"r")
        return int(f.get("entry/sample/goniometer/omega_range_total").value/f.get("entry/sample/goniometer/omega_increment").value)




    def split(a, n):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))




    def createScript(ind, outd, fromImage, toImage,dataName):
            if "/Volumes/offline-visitors" in dataName:
                dataName =dataName.replace("/Volumes/offline-","/data/")
                ind      =ind.replace     ("/Volumes/offline-","/data/")
                outd     =outd.replace    ("/Volumes/offline-","/data/")

            fromImage=str(fromImage)
            toImage=str(toImage)
            #create empty string to start the script
            content=""
            content="\n"
            content="\n"

            dialscontent   = content



            #DIALS definitions


            dialscontent+="cd "+outd+"/dials "
            dialscontent+="\n"
            dialscontent+="xia2 goniometer.axes=0,1,0  "                
            dialscontent+="    pipeline=dials failover=true  nproc=48"                
            dialscontent+="    image="+ind+":"+fromImage+":"+toImage+"  "                
            dialscontent+="    multiprocessing.mode=serial  "                
            dialscontent+="    multiprocessing.njob=1  "                
            dialscontent+='    multiprocessing.nproc=auto'                
            dialscontent+="\n"

            return dialscontent





    def create_headers():
        #init variables
        dialsOut    = ""    

        #define env for script for DIALS
        dialsOut+= """#!/bin/bash\n"""
        dialsOut+= """#!/bin/bash\n"""
        dialsOut+= """#SBATCH -t 99:55:00\n"""
        dialsOut+= """#SBATCH -J DIALS\n"""
        dialsOut+= """#SBATCH --exclusive\n"""
        dialsOut+= """#SBATCH -N1\n"""
        dialsOut+= """#SBATCH --cpus-per-task=48\n"""
        dialsOut+= """#SBATCH --mem=220000\n""" 
        dialsOut+= """#SBATCH -o """+path+"""/fragmax/logs/dials_fragmax_%j.out\n"""
        dialsOut+= """#SBATCH -e """+path+"""/fragmax/logs/dials_fragmax_%j.err\n"""    
        dialsOut+= """module purge\n\n"""
        dialsOut+= """module load CCP4 DIALS/1.12.3-PReSTO\n\n"""

        return dialsOut


    def prepareFolder(proteinDict=proteinNames): 

            os.makedirs(path+"/fragmax/process", exist_ok=True)
            os.makedirs(path+"/fragmax/scripts", exist_ok=True)
            os.makedirs(path+"/fragmax/logs"   , exist_ok=True)


    def processHDF5(userAcronym=None, userProtein=None):
            collectedImages=dict()

            if userAcronym and userProtein:
                if userAcronym in acronyms:
                    for acronym in userAcronym: 
                        try:
                            proteinNames[acronym]=os.listdir(path+"/raw/"+acronym) #creat a dict of protein names
                            proteinNames_path[acronym]=listdir_fullpath(path+"/raw/"+acronym) #create a dict of protein names with full path to the dir

                            for collectedProteins in proteinNames_path.values():
                                    for proteinName in collectedProteins:
                                            if userProtein==proteinName:
                                                datasets[proteinName] = glob.glob(proteinName+"/*master.h5") #create a dict of keys:proteinNames, values:master files - 


                            for key,value in datasets.items():     
                                    for i in value:
                                            n = images_collected(i)
                                            if n>4:
                                                    collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way
                        except:
                            print("No dataset with the given name was found. Please check the list of datasets with the provided acronym:")
                            for i in os.listdir(path+"/raw/"+userAcronym):
                                print(i)
                            break
                else:
                    print("Acronym given is not valid. Please check the list of acronyms available")
                    print("for you proposal and date\n")
                    for i in acronyms:
                        print(i)


            else:
                for key,value in datasets.items():     
                        for i in value:
                                n = images_collected(i)
                                if n>4:
                                        collectedImages[i]=n #store in a dict how many images were collected. Maybe not optimal way

            return collectedImages




    def runFragMAX(useDIALS=True, path=path):
        # FragMAX running script
        prepareFolder() # create folder system for reprocessing files
        nodes=3 #nodes per pipeline

        images = processHDF5()

        dialsOut=create_headers()

        scriptList=list()

        for masterFile, totalFrames in images.items():    
            #output dir for each protein separate
            outdir=masterFile.split("raw")[0]+"fragmax/process"+masterFile.split("raw")[1].split("_master.h5")[0]        
            os.makedirs(outdir+"/dials",exist_ok=True)

            #get the real number of data existing in the directory
            dataN=outdir+"/"+outdir.split("/")[-1]

            #Create scripts for HPC for each dataset, with custom dataframe number and outdirs
            dialsScript=createScript(masterFile,outdir, 1, totalFrames,dataN)    
            scriptList.append(dialsScript)

        #Create partial HPC scripts to submmit to several nodes at same time
        nodes=3
        chunkScripts=[dialsOut+"".join(x) for x in list(split(scriptList,nodes) )]


        for num,chunk in enumerate(chunkScripts):
            with open(path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)
            
            script=path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh"
            command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)

    runFragMAX()



################ PANDDA #####################
def populate_missing():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    dataissuePaths=glob.glob(path+"/fragmax/results/pandda/*/final.mtz")
    

    def getRes(mtzfile):
        stdout = Popen('phenix.mtz.dump '+mtzfile, shell=True, stdout=PIPE).stdout
        output = stdout.read().decode("utf-8")
        for line in output.split("\n"):
            if "Resolution range" in line:
                lowres, highres=line.split()[-2],line.split()[-1]
        if "free" in "".join(output).lower():
            for line in output.split("\n"):
                if "free" in line.lower():
                    freeRflag=line.split()[0]
        else:  
            freeRflag="R-free-flags"
            
        return lowres, highres, freeRflag
    def splitsc(a, n):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

    def buildResDict(dataPaths):
        resdict=dict()
        Rflagdict=dict()
        for data in dataPaths:
            l,h,Rflag =getRes(data)
            resdict[data] = h
            Rflagdict[data] = Rflag
        return resdict,Rflagdict
    
    def fixData(key,value,rflag):
        #shutil.copyfile(key,key+".bak")
        outmtz=key.split("final.mtz")[0]+"final.mtz"
        
        #Start and move to data folder
        command=""
        command+="\n\ncd "+key.replace("/results/","/process/").replace("final.mtz","")       
        command+="\n\n"
        
        #Uniqueify dataset 

        command+="uniqueify -f "+rflag+" "+key+" "+key.replace("/results/","/process/")
        command+="\n\n"
        
        #CAD
        
        command+="cad hklin1 "+key+ " hklout " +outmtz+ " <<eof\n"
        command+=" monitor BRIEF\n"
        command+=" labin file 1 - \n"
        command+="  ALL\n"
        command+=" resolution file 1 999.0 "+ value+"\n"
        command+="eof\n\n"    
        
        #Phenix maps
        command+="phenix.maps "+key.replace(".mtz",".pdb")+" "+key+"\n\n"    
        

        #Move results back to original folder
        command+="mv -f "+key.replace("final.mtz","final_2mFo-DFc_map.ccp4 ")+" "+key.replace(".mtz",".ccp4")+"\n"
        command+="mv -f "+key.replace("final.mtz","final_map_coeffs.mtz"    )+" "+key+"\n\n"
        
        return command

    def rerunRefine(key,value):
        command=""
        command+="phenix.maps "+key.replace(".mtz",".pdb")+" "+key+"\n"    
        return command


    def makeScript():    
        #init variables
        resdict,Rflagdict=buildResDict(dataissuePaths)
        
        panddaOut    = ""    
    
        #define env for script for XDSAPP
        panddaOut+= """#!/bin/bash\n"""
        panddaOut+= """#!/bin/bash\n"""
        panddaOut+= """#SBATCH -t 99:55:00\n"""
        panddaOut+= """#SBATCH -J PanddaFix\n"""
        panddaOut+= """#SBATCH --exclusive\n"""
        panddaOut+= """#SBATCH -N1\n"""
        panddaOut+= """#SBATCH --cpus-per-task=48\n"""
        panddaOut+= """#SBATCH --mem=220000\n""" 
        panddaOut+= """#SBATCH -o """+path+"""/fragmax/logs/pandda_repopReflections_%j.out\n"""
        panddaOut+= """#SBATCH -e """+path+"""/fragmax/logs/pandda_repopReflections_%j.err\n"""    
        panddaOut+= """module load CCP4 Phenix PyMOL/2.1.0-PReSTO\n\n"""
        
        cmdList=list()
        for key, value in resdict.items():
            cmdList.append("\n"+fixData(key,value,Rflagdict[key]))
        
        nodes=5
        chunkScripts=[panddaOut+"".join(x) for x in list(splitsc(cmdList,nodes) )]
        
        
        for num,chunk in enumerate(chunkScripts):
            with open(path+"/fragmax/scripts/panddafix_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)

            script=path+"/fragmax/scripts/panddafix_part"+str(num)+".sh"
            command ='echo "module purge | module load CCP4 Phenix | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)
    
    #Run populate missing reflection in all dataset

    for key in dataissuePaths:
        os.makedirs(key.replace("/results/","/process/").replace("final.mtz",""), exist_ok=True)
    #
    makeScript()
    

def prepare_pandda_folder():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    ##
    
    pdbList=list()
    with open(path+"/fragmax/scripts/preparePanDDAfolder.sh","w") as outp:        
        outp.write("#!/bin/bash")
        outp.write("\n#!/bin/bash")
        outp.write("\n#SBATCH -t 99:55:00")
        outp.write("\n#SBATCH -J panFolders")
        outp.write("\n#SBATCH --exclusive")
        outp.write("\n#SBATCH -N1")
        outp.write("\n#SBATCH --cpus-per-task=40")
        outp.write("\n#SBATCH -o "+path+"/fragmax/logs/panddafolders_fragmax_%j.out")
        outp.write("\n#SBATCH -e "+path+"/fragmax/logs/panddafolders_fragmax_%j.err")
        outp.write("\n\n")

        resultsList=glob.glob(path+"/fragmax/results/"+acr+"*/*/*/*final*.pdb")
        for i in resultsList:

            lig=i.split("/")[-4].split(acr+"-")[-1].split("_")[0]
            srcpdb=i    
            srcmtz=i.replace(".pdb",".mtz")
            srcnat=i.replace(".pdb","_2mFo-DFc.ccp4")
            srcdif=i.replace(".pdb","_mFo-DFc.ccp4")


            srccif=path+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".cif"
            srclig=path+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".pdb"

            dstPath="/".join(i.split("/")[:8])+"/pandda/"+"_".join(i.split("/")[8:11])+"/"

            dstpdb ="/".join(i.split("/")[:8])+"/pandda/"+"_".join(i.split("/")[8:11])+"/final."+i.split("/")[-1][-3:]
            dstmtz=dstpdb.replace(".pdb",".mtz")
            dstnat=dstpdb.replace(".pdb","_2mFo-DFc.ccp4")
            dstdif=dstpdb.replace(".pdb","_mFo-DFc.ccp4")
            dstcif="/".join(i.split("/")[:8])+"/pandda/"+"_".join(i.split("/")[8:11])+"/"+lig+".cif"
            dstlig="/".join(i.split("/")[:8])+"/pandda/"+"_".join(i.split("/")[8:11])+"/"+lig+".pdb"

            os.makedirs(dstPath,exist_ok=True)
            outp.write("\nrsync --ignore-existing "+srcpdb+" "+dstpdb+" &")
            outp.write("\nrsync --ignore-existing "+srcmtz+" "+dstmtz+" &")
            outp.write("\nrsync --ignore-existing "+srcnat+" "+dstnat+" &")
            outp.write("\nrsync --ignore-existing "+srcdif+" "+dstdif+" &")
            outp.write("\nrsync --ignore-existing "+srccif+" "+dstcif+" &")
            outp.write("\nrsync --ignore-existing "+srclig+" "+dstlig+" &")
            outp.write("\n\n")

            
            pdbList.append(dstpdb)

    script=path+"/fragmax/scripts/run_CAD.sh"
    command ='echo "module purge | module load CCP4 Phenix | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(command,shell=True)


def fix_pandda_symlinks():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
    linksFolder=glob.glob(path+"/fragmax/results/pandda/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")
    for i in linksFolder:
        print(i)
        folder="/".join(i.split("/")[:-1])+"/"
        pdbs=os.listdir(folder)
        pdb=folder+sorted([x for x in pdbs if "fitted" in x])[-1]
        print(pdb)
        shutil.move(i,i+".bak")
        shutil.copyfile(pdb,i)
#############################################

def run_structure_solving(useDIMPLE, useFSP, useBUSTER, userPDB, spacegroup):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()
        

    def process2results(path):
        pyfile ='import os '
        pyfile+='\nimport glob'
        pyfile+='\nimport subprocess'
        pyfile+='\nimport shutil'
        pyfile+='\nimport sys'
        pyfile+='\n'
        pyfile+='\npath=sys.argv[1]'
        pyfile+='\nacr=sys.argv[2]'
        pyfile+='\nspg=sys.argv[3]'
        pyfile+='\n'
        pyfile+='\ndatasetList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/")'
        pyfile+='\nfor dataset in datasetList:    '
        pyfile+='\n    '
        pyfile+='\n    dataset_run=dataset.split("/")[-2]    '
        pyfile+='\n    dataset_original=dataset'
        pyfile+='\n    datasetfp=(dataset.replace("/fragmax/","/"))        '
        pyfile+='\n    datasetfp="/".join(datasetfp.split("/")[:-2])+"/xds_"+datasetfp.split("/")[-2]+"_1/"'
        pyfile+='\n    '
        pyfile+='\n    if os.path.exists(dataset+"autoproc/staraniso_alldata.mtz"):        '
        pyfile+='\n        shutil.copyfile(dataset+"autoproc/staraniso_alldata.mtz",dataset.split("process/")[0]+"results/"+dataset_run+"/autoproc/"+dataset_run+"_autoproc_merged.mtz")'
        pyfile+='\n        a=dataset.split("process/")[0]+"results/"+dataset_run+"/autoproc/"+dataset_run+"_autoproc_merged.mtz"'
        pyfile+='''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n        subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n    elif os.path.exists(dataset+"autoproc/aimless_alldata-unique.mtz"):        '
        pyfile+='\n        shutil.copyfile(dataset+"autoproc/aimless_alldata-unique.mtz",dataset.split("process/")[0]+"results/"+dataset_run+"/autoproc/"+dataset_run+"_autoproc_merged.mtz")'
        pyfile+='\n        a=dataset.split("process/")[0]+"results/"+dataset_run+"/autoproc/"+dataset_run+"_autoproc_merged.mtz"'
        pyfile+='''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n        subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n    elif os.path.exists(dataset+"autoproc/truncate-unique.mtz"):        '
        pyfile+='\n        shutil.copyfile(dataset+"autoproc/truncate-unique.mtz",dataset.split("process/")[0]+"results/"+dataset_run+"/autoproc/"+dataset_run+"_autoproc_merged.mtz")'
        pyfile+='\n        a=dataset.split("process/")[0]+"results/"+dataset_run+"/autoproc/"+dataset_run+"_autoproc_merged.mtz"'
        pyfile+='''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n        subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n    else:'
        pyfile+='\n        pass'
        pyfile+='\n  '
        pyfile+='\n'
        pyfile+='\n    if os.path.exists(dataset+"dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"):'
        pyfile+='\n        if not os.path.exists(dataset.split("process/")[0]+"results/"+dataset_run+"/dials/"+dataset_run+"_dials_merged.mtz"):            '
        pyfile+='\n            shutil.copyfile(dataset+"dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz",dataset.split("process/")[0]+"results/"+dataset_run+"/dials/"+dataset_run+"_dials_merged.mtz")'
        pyfile+='\n            a=dataset.split("process/")[0]+"results/"+dataset_run+"/dials/"+dataset_run+"_dials_merged.mtz"'
        pyfile+='''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n    else:'
        pyfile+='\n        pass'
        pyfile+='\n    '
        pyfile+='\n   '
        pyfile+='\n    '
        pyfile+='\n    if os.path.exists(dataset+"xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"):'
        pyfile+='\n        xsdat=dataset.split("process/")[0]+"results/"+dataset_run+"/xdsxscale/"+dataset_run+"_xdsxscale_merged.mtz"'
        pyfile+='\n        if not os.path.exists(dataset.split("process/")[0]+"results/"+dataset_run+"/xdsxscale/"+dataset_run+"_xdsxscale_merged.mtz"):'
        pyfile+='\n            print(dataset+"xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz",dataset.split("process/")[0]+"results/"+dataset_run+"/xdsxscale/"+dataset_run+"_xdsxscale_merged.mtz")'
        pyfile+='\n    else:'
        pyfile+='\n        pass'
        pyfile+='\n    '
        pyfile+='\n    '
        pyfile+='\n    if os.path.exists(dataset+"xdsapp/"+dataset_run+"_data_F.mtz"):'
        pyfile+='\n        '
        pyfile+='\n        if not os.path.exists(dataset.split("process/")[0]+"results/"+dataset_run+"/xdsapp/"+dataset_run+"_xdsapp_merged.mtz"):'
        pyfile+='\n            shutil.copyfile(dataset+"xdsapp/"+dataset_run+"_data_F.mtz",dataset.split("process/")[0]+"results/"+dataset_run+"/xdsapp/"+dataset_run+"_xdsapp_merged.mtz")'
        pyfile+='\n            a=dataset.split("process/")[0]+"results/"+dataset_run+"/xdsapp/"+dataset_run+"_xdsapp_merged.mtz"'
        pyfile+='''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n    else:'
        pyfile+='\n        pass'
        pyfile+='\n    '
        pyfile+='\n   '
        pyfile+='\n    '
        pyfile+='\n    if os.path.exists(dataset+"EDNA_proc/results/ep_"+dataset_run+"_noanom_aimless.mtz"):'
        pyfile+='\n        if not os.path.exists(dataset_original.split("process/")[0]+"results/"+dataset_run+"/EDNA_proc/"+dataset_run+"_EDNA_proc_merged.mtz"):'
        pyfile+='\n            shutil.copyfile(dataset+"EDNA_proc/results/ep_"+dataset_run+"_noanom_aimless.mtz",dataset_original.split("process/")[0]+"results/"+dataset_run+"/EDNA_proc/"+dataset_run+"_EDNA_proc_merged.mtz")'
        pyfile+='\n            a=dataset_original.split("process/")[0]+"results/"+dataset_run+"/EDNA_proc/"+dataset_run+"_EDNA_proc_merged.mtz"'
        pyfile+='''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n    else:'
        pyfile+='\n        pass'
        pyfile+='\n    '
        pyfile+='\n'
        pyfile+='\n    '
        pyfile+='\n    if os.path.exists(datasetfp+"fastdp/results/ap_"+dataset_run[:-1]+"run1_noanom_fast_dp.mtz.gz"):        '
        pyfile+='\n        if not os.path.exists(dataset.split("process/")[0]+"results/"+dataset_run+"/fastdp/"+dataset_run+"_fastdp_unmerged.mtz"):'
        pyfile+='\n            shutil.copyfile(datasetfp+"fastdp/results/ap_"+dataset_run[:-1]+"run1_noanom_fast_dp.mtz.gz",dataset.split("process/")[0]+"results/"+dataset_run+"/fastdp/"+dataset_run+"_fastdp_unmerged.mtz.gz")'
        pyfile+='\n            try:'
        pyfile+='''\n                subprocess.check_call(['gunzip', dataset.split("process/")[0]+"results/"+dataset_run+"/fastdp/"+dataset_run+"_fastdp_unmerged.mtz.gz"])'''
        pyfile+='\n            except:'
        pyfile+='\n                pass'
        pyfile+='\n            a=dataset.split("process/")[0]+"results/"+dataset_run+"/fastdp/"+dataset_run+"_fastdp_unmerged.mtz"'
        pyfile+='''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
        pyfile+='\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'
        pyfile+='\n'
        pyfile+='\n    else:'
        pyfile+='\n        pass'

        
        
        
        with open(path+"/fragmax/scripts/process2results.py","w") as outp:
            outp.write(pyfile)
        #Creates HPC script to run dimple on all mtz files provided.
        #PDB file can be provided in the header of the python script and parse to all 
        #pipelines (Dimple, pipedream, bessy)


        ##This line will make dimple run on unscaled unmerged files. It seems that works 
        ##better sometimes
        #mtzlist=[x.split("_merged")[0]+"_unmerged_unscaled.mtz" for x in mtzlist]


        proc2resOut=""

        #define env for script for dimple
        proc2resOut+= """#!/bin/bash\n"""
        proc2resOut+= """#!/bin/bash\n"""
        proc2resOut+= """#SBATCH -t 99:55:00\n"""
        proc2resOut+= """#SBATCH -J ScaleMerge\n"""
        proc2resOut+= """#SBATCH --exclusive\n"""
        proc2resOut+= """#SBATCH -N1\n"""
        proc2resOut+= """#SBATCH --cpus-per-task=48\n"""
        proc2resOut+= """#SBATCH --mem=220000\n""" 
        proc2resOut+= """#SBATCH -o """+path+"""/fragmax/logs/process2results_%j.out\n"""
        proc2resOut+= """#SBATCH -e """+path+"""/fragmax/logs/process2results_%j.err\n"""    
        proc2resOut+= """module purge\n"""
        proc2resOut+= """module load CCP4 Phenix\n\n"""



        #dimpleOut+=" & ".join(dimp)
        proc2resOut+="\n\n"
        proc2resOut+="python "+path+"/fragmax/scripts/process2results.py "+path+" "+acr+" P1211"
        with open(path+"/fragmax/scripts/run_proc2res.sh","w") as outp:
            outp.write(proc2resOut)
        
    def dimple_hpc(PDB):
        #Creates HPC script to run dimple on all mtz files provided.
        #PDB file can be provided in the header of the python script and parse to all 
        #pipelines (Dimple, pipedream, bessy)


        ##This line will make dimple run on unscaled unmerged files. It seems that works 
        ##better sometimes

        outDirs=list()
        inputData=list()
        dimpleOut=""

        #define env for script for dimple
        dimpleOut+= """#!/bin/bash\n"""
        dimpleOut+= """#!/bin/bash\n"""
        dimpleOut+= """#SBATCH -t 99:55:00\n"""
        dimpleOut+= """#SBATCH -J dimple\n"""
        dimpleOut+= """#SBATCH --exclusive\n"""
        dimpleOut+= """#SBATCH -N1\n"""
        dimpleOut+= """#SBATCH --cpus-per-task=48\n"""
        dimpleOut+= """#SBATCH --mem=220000\n""" 
        dimpleOut+= """#SBATCH -o """+path+"""/fragmax/logs/dimple_fragmax_%j.out\n"""
        dimpleOut+= """#SBATCH -e """+path+"""/fragmax/logs/dimple_fragmax_%j.err\n"""    
        dimpleOut+= """module purge\n"""
        dimpleOut+= """module load CCP4 Phenix \n\n"""

        for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):
            mtzList=glob.glob(proc+"*mtz")
            if mtzList:
                inputData.append("'"+sorted(glob.glob(proc+"*mtz"))[0]+"'")
        
        with open(path+"/fragmax/scripts/run_dimple.py","w") as pyout:
            pyout.write("import multiprocessing\n")
            pyout.write("import time\n")
            pyout.write("import os\n")
            pyout.write("import shutil\n")
            pyout.write("import subprocess\n")
            pyout.write("outDirs=["+"',\n".join(["/".join(x.split("/")[:-1])+"/dimple" for x in inputData])+"']\n\n")
            pyout.write("mtzList=["+",\n".join(inputData)+"]\n\n")
            pyout.write("inpdata=list()\n")
            pyout.write("for a,b in zip(outDirs,mtzList):\n")
            pyout.write("    inpdata.append([a,b])\n")
            pyout.write("def fragmax_worker((di, mtz)):\n")
            pyout.write("    command='dimple -s %s %s %s ; cd %s ; phenix.mtz2map final.mtz' %(mtz, '"+PDB+"', di,di)\n")
            pyout.write("    subprocess.call(command, shell=True) \n")
            pyout.write("def mp_handler():\n")
            pyout.write("    p = multiprocessing.Pool(48)\n")
            pyout.write("    p.map(fragmax_worker, inpdata)\n")
            pyout.write("if __name__ == '__main__':\n")
            pyout.write("    mp_handler()\n")
            
        dimpleOut+="python "+path+"/fragmax/scripts/run_dimple.py"
        dimpleOut+="\n\n"
        with open(path+"/fragmax/scripts/run_dimple.sh","w") as outp:
            outp.write(dimpleOut)
        
    def fspipeline_hpc(PDB):
        #This pipeline will run bessy fspipeline on all mtz files under the current directory
        #for now, results are not exported in a convenient way. I will have to fix this in the future

        
        fsp_exec_path="/data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py"

        fspOut=""

        #define env for script for fspipeline
        fspOut+= """#!/bin/bash\n"""
        fspOut+= """#!/bin/bash\n"""
        fspOut+= """#SBATCH -t 99:55:00\n"""
        fspOut+= """#SBATCH -J fsp\n"""
        fspOut+= """#SBATCH --exclusive\n"""
        fspOut+= """#SBATCH -N1\n"""
        fspOut+= """#SBATCH --cpus-per-task=48\n"""
        fspOut+= """#SBATCH --mem=220000\n""" 
        fspOut+= """#SBATCH -o """+path+"""/fragmax/logs/fsp_fragmax_%j.out\n"""
        fspOut+= """#SBATCH -e """+path+"""/fragmax/logs/fsp_fragmax_%j.err\n"""    
        fspOut+= """module purge\n"""
        fspOut+= """module load CCP4 Phenix\n\n"""
        fspOut+= "cd "+path+"/fragmax/results/"+"\n\n"
        fspOut+="python "
        fspOut+=fsp_exec_path
        fspOut+=" --refine="
        fspOut+=PDB
        fspOut+=" --exclude='unscaled unmerged scaled final'"
        fspOut+=" --cpu=48"
        fspOut+=" --dir="+path+"/fragmax/results/"+"fspipeline\n\n"
        fspOut+="python "+path+"/fragmax/scripts/run_fspipeline.py "+path
        
        
        with open(path+"/fragmax/scripts/run_fspipeline.sh","w") as outp:
            outp.write(fspOut)
        with open(path+"/fragmax/scripts/run_fspipeline.py","w") as pyOut:
            pyOut.write("import multiprocessing\n")
            pyOut.write("import time\n")
            pyOut.write("import os\n")
            pyOut.write("import shutil\n")
            pyOut.write("import subprocess\n")
            pyOut.write("import sys\n")
            pyOut.write("import glob\n")

            pyOut.write("path=sys.argv[1]\n")
                
            pyOut.write('fsp_list =glob.glob("'+path+'/fragmax/results/*fspipeline*")\n')
            pyOut.write('path_list=list()\n')
            pyOut.write('for fsp_run in fsp_list:\n')
            pyOut.write('    for roots, dirs, files in os.walk(fsp_run):\n')
            pyOut.write('        if "mtz2map.log" in files:      \n')
            pyOut.write('            path_list.append(roots)\n')
            pyOut.write('success_list=[x.split("/")[-2].split("_merged")[0] for x in path_list]    \n')
            pyOut.write('softwares = ["autoproc","EDNA_proc","dials","fastdp","xdsapp","xdsxscale"]\n')
            pyOut.write('for file,fpath in zip(success_list,path_list):\n')
            pyOut.write('    outdir=path+"/fragmax/results/"\n')
            pyOut.write('    for sw in softwares:\n')
            pyOut.write('        if sw in file:\n')
            pyOut.write('            outp=outdir+file.split("_"+sw)[0]+"/"+sw\n')
            pyOut.write('            copy_string="rsync --ignore-existing -raz "+fpath+"/* "+outp+"/fspipeline"\n')
            pyOut.write('            subprocess.call(copy_string, shell=True)\n')


    def BUSTER_hpc(path, PDB):
        #Creates HPC script to run dimple on all mtz files provided.
        #PDB file can be provided in the header of the python script and parse to all 
        #pipelines (Dimple, pipedream, bessy)


        ##This line will make dimple run on unscaled unmerged files. It seems that works 
        ##better sometimes
        mtzlist=[x.split("_merged")[0]+"_unmerged_unscaled.mtz" for x in mtzlist]


        busterOut=""

        #define env for script for dimple
        busterOut+= """#!/bin/bash\n"""
        busterOut+= """#!/bin/bash\n"""
        busterOut+= """#SBATCH -t 99:55:00\n"""
        busterOut+= """#SBATCH -J BUSTER\n"""
        busterOut+= """#SBATCH --exclusive\n"""
        busterOut+= """#SBATCH -N1\n"""
        busterOut+= """#SBATCH --cpus-per-task=48\n"""
        busterOut+= """#SBATCH --mem=220000\n""" 
        busterOut+= """#SBATCH -o """+path+"""/fragmax/logs/buster_fragmax_%j.out\n"""
        busterOut+= """#SBATCH -e """+path+"""/fragmax/logs/buster_fragmax_%j.err\n"""    
        busterOut+= """module purge \n"""
        busterOut+= """module load autoPROC BUSTER Phenix \n\n"""


        #dimple doesnt play well with many jobs sent at the same time to HPC. not sure why though           


        busterOut+="\n\n"

        return busterOut

    dimple_hpc(userPDB)
    fspipeline_hpc(userPDB)
    process2results(path)

    slurmqueue="RES=$(sbatch "+path+"/fragmax/scripts/run_proc2res.sh)  "
    # if useBUSTER:
    #     script=path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh"
    #     command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    #     subprocess.call(command,shell=True)
    if useFSP:
        slurmqueue+=" && sbatch --dependency=afterok:${RES##* } "+path+"/fragmax/scripts/run_fspipeline.sh "
    if useDIMPLE:
        slurmqueue+=" && sbatch --dependency=afterok:${RES##* } "+path+"/fragmax/scripts/run_dimple.sh "
    
    
    command ='echo "module purge | module load CCP4 Phenix | '+slurmqueue+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(command,shell=True)
   

def ligandToSVG():
    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    lib="F2XEntry"
    ligPDBlist=glob.glob(path+"/fragmax/process/fragment/"+lib+"/*/*.pdb")
    for ligPDB in ligPDBlist:
        
        inp=ligPDB
        out=ligPDB.replace(".pdb",".svg")
        if not os.path.exists(out):
            subprocess.call("babel "+inp+" "+out+" -d",shell=True)
            with open(out,"r") as outr:
                content=outr.readlines()
            with open(out,"w") as outw:
                content="".join(content).replace(inp,"").replace("- Open Babel Depiction", "FragMAX")
                content=content.replace('fill="white"', 'fill="none"').replace('stroke-width="2.0"','stroke-width="3.5"').replace('stroke-width="1.0"','stroke-width="1.75"')
                outw.write(content)

def autoLigandFit(useLigFit,useRhoFit,fraglib):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    pdbList=list()
    with open(path+"/fragmax/scripts/prepareLigfitDataset.sh","w") as outp:        
        outp.write("#!/bin/bash")
        outp.write("\n#!/bin/bash")
        outp.write("\n#SBATCH -t 99:55:00")
        outp.write("\n#SBATCH -J ligFolders")
        outp.write("\n#SBATCH --exclusive")
        outp.write("\n#SBATCH -N1")
        outp.write("\n#SBATCH --cpus-per-task=40")
        outp.write("\n#SBATCH -o "+path+"/fragmax/logs/ligfitfolders_fragmax_%j.out")
        outp.write("\n#SBATCH -e "+path+"/fragmax/logs/ligfitfolders_fragmax_%j.err")

        resultsList=glob.glob(path+"/fragmax/results/"+acr+"*/*/*/*final*.pdb")

        for i in resultsList:

            lig=i.split("/")[-4].split(acr+"-")[-1].split("_")[0]
            srcpdb=i    
            srcmtz=i.replace(".pdb",".mtz")
            srcnat=i.replace(".pdb","_2mFo-DFc.ccp4")
            srcdif=i.replace(".pdb","_mFo-DFc.ccp4")


            srccif=path+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".cif"
            srclig=path+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".pdb"

            dstPath="/".join(i.split("/")[:8])+"/ligandfit/"+"_".join(i.split("/")[8:11])+"/"

            dstpdb ="/".join(i.split("/")[:8])+"/ligandfit/"+"_".join(i.split("/")[8:11])+"/final."+i.split("/")[-1][-3:]
            dstmtz=dstpdb.replace(".pdb",".mtz")
            dstnat=dstpdb.replace(".pdb","_2mFo-DFc.ccp4")
            dstdif=dstpdb.replace(".pdb","_mFo-DFc.ccp4")
            dstcif="/".join(i.split("/")[:8])+"/ligandfit/"+"_".join(i.split("/")[8:11])+"/"+lig+".cif"
            dstlig="/".join(i.split("/")[:8])+"/ligandfit/"+"_".join(i.split("/")[8:11])+"/"+lig+".pdb"

            os.makedirs(dstPath,exist_ok=True)
            outp.write("\nrsync --ignore-existing "+srcpdb+" "+dstpdb+" &")
            outp.write("\nrsync --ignore-existing "+srcmtz+" "+dstmtz+" &")
            outp.write("\nrsync --ignore-existing "+srcnat+" "+dstnat+" &")
            outp.write("\nrsync --ignore-existing "+srcdif+" "+dstdif+" &")
            outp.write("\nrsync --ignore-existing "+srccif+" "+dstcif+" &")
            outp.write("\nrsync --ignore-existing "+srclig+" "+dstlig+" &")

            
            pdbList.append(dstpdb)
        
    mtzList=[x.replace("/final.pdb","/final.mtz") for x in pdbList]
    outListrh=[x.replace("/final.pdb","/rhofit") for x in pdbList]
    cifList=[x.replace("final.mtz",x.split(acr+"-")[-1].split("_")[0]+".cif") for x in mtzList]

    nthreads=str(48)


    rhofitScript=list()
    rhopythonOut=""

    rhopythonOut+='import multiprocessing\n'
    rhopythonOut+='import time\n'
    rhopythonOut+='import subprocess\n\n\n'

    rhopythonOut+='cifList=["'+'",\n"'.join(cifList)+'"]\n\n'
    rhopythonOut+='mtzList=["'+'",\n"'.join(mtzList)+'"]\n\n'
    rhopythonOut+='pdbList=["'+'",\n"'.join(pdbList)+'"]\n\n'
    rhopythonOut+='outList=["'+'",\n"'.join(outListrh)+'"]\n\n'


    rhopythonOut+='inpdata=list()\n'
    rhopythonOut+='for a,b,c,d in zip(cifList,mtzList,pdbList,outList):\n'
    rhopythonOut+='    inpdata.append([a,b,c,d])\n'
    rhopythonOut+='\n'
    rhopythonOut+='def rhofit_worker((cif, mtz, pdb, out)):\n'
    rhopythonOut+='    command="rhofit -l %s -m %s -p %s -d %s" %(cif, mtz, pdb, out)\n'
    rhopythonOut+='    print " Processs %s\tsubmitted" % cif\n'
    rhopythonOut+='    subprocess.call(command, shell=True) \n'
    rhopythonOut+='    \n'
    rhopythonOut+='\n'
    rhopythonOut+='def mp_handler():\n'
    rhopythonOut+='    p = multiprocessing.Pool('+nthreads+')\n'
    rhopythonOut+='    p.map(rhofit_worker, inpdata)\n'
    rhopythonOut+='\n'
    rhopythonOut+="""if __name__ == '__main__':\n"""
    rhopythonOut+='    mp_handler()\n'

    if "True" in useRhoFit:
        with open(path+"/fragmax/scripts/rhofit.py", "w") as outfile:
            outfile.write(rhopythonOut)
        with open(path+"/fragmax/scripts/run_rhofit.sh","w") as outp:        
            outp.write("#!/bin/bash")
            outp.write("\n#!/bin/bash")
            outp.write("\n#SBATCH -t 99:55:00")
            outp.write("\n#SBATCH -J rhofit")
            outp.write("\n#SBATCH --exclusive")
            outp.write("\n#SBATCH -N1")
            outp.write("\n#SBATCH --cpus-per-task=40")
            outp.write("\n#SBATCH -o "+path+"/fragmax/logs/rhofit_fragmax_%j.out")
            outp.write("\n#SBATCH -e "+path+"/fragmax/logs/rhofit_fragmax_%j.err")
            outp.write("\nmodule purge")
            outp.write("\nmodule load autoPROC BUSTER Phenix")
            outp.write("\npython "+path+"/fragmax/scripts/rhofit.py")


        
        
    outListlf=[x.replace("/final.pdb","/LigandFit_Run_1_") for x in pdbList]
    cifList=[x.replace("final.mtz",x.split(acr+"-")[-1].split("_")[0]+".cif") for x in mtzList]
    nthreads=str(48)


    rhofitScript=list()
    rhopythonOut=""

    rhopythonOut+='import multiprocessing\n'
    rhopythonOut+='import time\n'
    rhopythonOut+='import subprocess\n\n\n'

    rhopythonOut+='cifList=["'+'",\n"'.join(cifList)+'"]\n\n'
    rhopythonOut+='mtzList=["'+'",\n"'.join(mtzList)+'"]\n\n'
    rhopythonOut+='pdbList=["'+'",\n"'.join(pdbList)+'"]\n\n'
    rhopythonOut+='outList=["'+'",\n"'.join(outListlf)+'"]\n\n'


    rhopythonOut+='inpdata=list()\n'
    rhopythonOut+='for a,b,c,d in zip(cifList,mtzList,pdbList,outList):\n'
    rhopythonOut+='    inpdata.append([a,b,c,d])\n'
    rhopythonOut+='\n'
    rhopythonOut+='def ligandfit_worker((cif, mtz, pdb, out)):\n'    
    rhopythonOut+='    out="/".join(out.split("/")[:-1])\n'
    rhopythonOut+='    command="cd %s && phenix.ligandfit data=%s model=%s ligand=%s fill=True clean_up=True" %(out,mtz, pdb, cif)\n'
    rhopythonOut+='    print " Processs %s\tsubmitted" % cif\n'
    rhopythonOut+='    subprocess.call(command, shell=True) \n'


    rhopythonOut+='\n'
    rhopythonOut+='def mp_handler():\n'
    rhopythonOut+='    p = multiprocessing.Pool('+nthreads+')\n'
    rhopythonOut+='    p.map(ligandfit_worker, inpdata)\n'
    rhopythonOut+='\n'
    rhopythonOut+="""if __name__ == '__main__':\n"""
    rhopythonOut+='    mp_handler()\n'
    if "True" in useLigFit:
        with open(path+"/fragmax/scripts/ligandfit.py", "w") as outfile:
            outfile.write(rhopythonOut)
        with open(path+"/fragmax/scripts/run_ligfit.sh","w") as outp:        
            outp.write("#!/bin/bash")
            outp.write("\n#!/bin/bash")
            outp.write("\n#SBATCH -t 99:55:00")
            outp.write("\n#SBATCH -J phenixligfit")
            outp.write("\n#SBATCH --exclusive")
            outp.write("\n#SBATCH -N1")
            outp.write("\n#SBATCH --cpus-per-task=40")
            outp.write("\n#SBATCH -o "+path+"/fragmax/logs/rhofit_fragmax_%j.out")
            outp.write("\n#SBATCH -e "+path+"/fragmax/logs/rhofit_fragmax_%j.err")
            outp.write("\nmodule purge")
            outp.write("\nmodule load autoPROC BUSTER Phenix")
            outp.write("\npython "+path+"/fragmax/scripts/ligandfit.py")


    slurmqueue="RES=$(sbatch "+path+"/fragmax/scripts/prepareLigfitDataset.sh)  "

    if "True" in useRhoFit:
        slurmqueue+=" && sbatch --dependency=afterok:${RES##* } "+path+"/fragmax/scripts/run_rhofit.sh "
    if "True" in useLigFit:
        slurmqueue+=" && sbatch --dependency=afterok:${RES##* } "+path+"/fragmax/scripts/run_ligfit.sh "
    
    
    command ='echo "module purge | module load CCP4 Phenix | '+slurmqueue+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(command,shell=True)
   
        
def project_dif_svg():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    xmlDict=dict()
    for x in glob.glob(path+"/fragmax/process/"+acr+"/*/*.xml"):
        xmlDict[x.split("/")[9]]=x
    

    for key,value in xmlDict.items():
        paramDict=retrieveParameters(value)
        try:
            t = threading.Thread(target=hdf2jpg, args=(paramDict,))
            t.start()
            
        except:
            print("No data for "+key) 

    t = threading.Thread(target=ligandToSVG,args=(lib))
    t.daemon = True
    t.start()
        
def merge_project():
    srcprj="20190401"
    dstprj="20190330"
    srcacr="/mxn/groups/ispybstorage/pyarch/visitors/proposal/shift/raw/srcacr/"
    dstacr="/mxn/groups/ispybstorage/pyarch/visitors/proposal/shift/raw/dstacr/"
    ### Symlink raw folder

    ### Symlink process folder
    
    ### Symlink snapshots



def get_project_status():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,panddaprocessed,fraglib=project_definitions()

    dataProcStatusDict=dict()
    dataRefStatusDict=dict()
    dataLigStatusDict=dict()
    dp=["autoproc","dials","xdsxscale","EDNA_proc","fastdp","xdsapp"]
    rf=["BUSTER","fspipeline","dimple"]
    sampleList=[x for x in glob.glob(path+"/fragmax/results/*/") if "pandda" not in x and "ligandfit" not in x]
    psampleList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/")
    for sample in psampleList:
        if os.path.exists(sample+"/autoproc/"):
            if os.path.exists(sample+"/autoproc/summary.html"):
                dataProcStatusDict[sample.split("/")[-2]]=";autoproc:full"
            else:
                dataProcStatusDict[sample.split("/")[-2]]=";autoproc:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]=";autoproc:none"
            
        if os.path.exists(sample+"/dials/"):
            if os.path.exists(sample+"/dials/xia2.html"):
                dataProcStatusDict[sample.split("/")[-2]]+=";dials:full"
            else:
                dataProcStatusDict[sample.split("/")[-2]]+=";dials:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";dials:none"
            
        if os.path.exists(sample+"/xdsxscale/"):
            if os.path.exists(sample+"/xdsxscale/xia2.html"):
                dataProcStatusDict[sample.split("/")[-2]]+=";xdsxscale:full"
            else:
                dataProcStatusDict[sample.split("/")[-2]]+=";xdsxscale:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";xdsxscale:none"
            
        autosample="/".join(sample.split("/")[:-2]).replace("/fragmax/","/")+"/"+"xds_"+sample.split("/")[-2]+"_1/"
        if os.path.exists(autosample+"EDNA_proc/results/"):
            if os.path.exists(autosample+"EDNA_proc/results/ep_INTEGRATE.HKL"):
                dataProcStatusDict[autosample.split("/")[-2][4:-2]]+=";EDNA_proc:full"
            else:
                dataProcStatusDict[autosample.split("/")[-2][4:-2]]+=";EDNA_proc:partial"
        else:
            dataProcStatusDict[autosample.split("/")[-2][4:-2]]+=";EDNA_proc:none"

        #### XDSAPP
        if os.path.exists(sample+"xdsapp/"):
            if os.path.exists(sample+"xdsapp/results_"+sample.split("/")[-2]+"_data.txt"):                
                dataProcStatusDict[sample.split("/")[-2]]+=";xdsapp:full"                
            else:
                dataProcStatusDict[sample.split("/")[-2]]+=";xdsapp:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";xdsapp:none"

        #### FASTDP
        if os.path.exists(autosample+"fastdp/results/"):
            if os.path.exists(autosample+"fastdp/results/ap_"+sample.split("/")[-2][:-1]+"run1_noanom_fast_dp.mtz.gz"):
                dataProcStatusDict[sample.split("/")[-2]]+=";fastdp:full"
            else:
                dataProcStatusDict[sample.split("/")[-2]]+=";fastdp:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";fastdp:none"

        with open(path+"/fragmax/process/dpstatus.csv","w") as outp:
            for key,value in dataProcStatusDict.items():
                outp.write(key+":"+value+"\n")
            

        ### STRUCTURE REFINEMENT
        #### DIMPLE
    for sample in sampleList:

        if os.path.exists(sample+"/autoproc/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]=";autoproc_dimple:full"
        elif os.path.exists(sample+"/autoproc/dimple/") and not os.path.exists(sample+"/autoproc/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]=";autoproc_dimple:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]=";autoproc_dimple:none"

        if os.path.exists(sample+"/dials/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_dimple:full"
        elif os.path.exists(sample+"/dials/dimple/") and not os.path.exists(sample+"/dials/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_dimple:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_dimple:none"

        if os.path.exists(sample+"/xdsxscale/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_dimple:full"
        elif os.path.exists(sample+"/xdsxscale/dimple/") and not os.path.exists(sample+"/xdsxscale/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_dimple:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_dimple:none"

        if os.path.exists(sample+"/xdsapp/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_dimple:full"
        elif os.path.exists(sample+"/xdsapp/dimple/") and not os.path.exists(sample+"/xdsapp/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_dimple:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_dimple:none"

        if os.path.exists(sample+"/EDNA_proc/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_dimple:full"
        elif os.path.exists(sample+"/EDNA_proc/dimple/") and not os.path.exists(sample+"/EDNA_proc/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_dimple:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_dimple:none"

        if os.path.exists(sample+"/fastdp/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_dimple:full"
        elif os.path.exists(sample+"/fastdp/dimple/") and not os.path.exists(sample+"/fastdp/dimple/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_dimple:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_dimple:none"



        #### FSPipeline    



        if os.path.exists(sample+"/autoproc/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";autoproc_fspipeline:full"
        elif os.path.exists(sample+"/autoproc/fspipeline/") and not os.path.exists(sample+"/autoproc/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";autoproc_fspipeline:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";autoproc_fspipeline:none"

        if os.path.exists(sample+"/dials/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_fspipeline:full"
        elif os.path.exists(sample+"/dials/fspipeline/") and not os.path.exists(sample+"/dials/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_fspipeline:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_fspipeline:none"

        if os.path.exists(sample+"/xdsxscale/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_fspipeline:full"
        elif os.path.exists(sample+"/xdsxscale/fspipeline/") and not os.path.exists(sample+"/xdsxscale/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_fspipeline:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_fspipeline:none"

        if os.path.exists(sample+"/xdsapp/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_fspipeline:full"
        elif os.path.exists(sample+"/xdsapp/fspipeline/") and not os.path.exists(sample+"/xdsapp/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_fspipeline:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_fspipeline:none"

        if os.path.exists(sample+"/EDNA_proc/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_fspipeline:full"
        elif os.path.exists(sample+"/EDNA_proc/fspipeline/") and not os.path.exists(sample+"/EDNA_proc/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_fspipeline:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_fspipeline:none"

        if os.path.exists(sample+"/fastdp/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_fspipeline:full"
        elif os.path.exists(sample+"/fastdp/fspipeline/") and not os.path.exists(sample+"/fastdp/fspipeline/mtz2map.log"):
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_fspipeline:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_fspipeline:none"



        ### BUSTER


        if os.path.exists(sample+"/autoproc/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";autoproc_BUSTER:full"
        elif os.path.exists(sample+"/autoproc/BUSTER/") and not os.path.exists(sample+"/autoproc/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";autoproc_BUSTER:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";autoproc_BUSTER:none"

        if os.path.exists(sample+"/dials/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_BUSTER:full"
        elif os.path.exists(sample+"/dials/BUSTER/") and not os.path.exists(sample+"/dials/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_BUSTER:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";dials_BUSTER:none"

        if os.path.exists(sample+"/xdsxscale/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_BUSTER:full"
        elif os.path.exists(sample+"/xdsxscale/BUSTER/") and not os.path.exists(sample+"/xdsxscale/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_BUSTER:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsxscale_BUSTER:none"

        if os.path.exists(sample+"/xdsapp/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_BUSTER:full"
        elif os.path.exists(sample+"/xdsapp/BUSTER/") and not os.path.exists(sample+"/xdsapp/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_BUSTER:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";xdsapp_BUSTER:none"

        if os.path.exists(sample+"/EDNA_proc/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_BUSTER:full"
        elif os.path.exists(sample+"/EDNA_proc/BUSTER/") and not os.path.exists(sample+"/EDNA_proc/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_BUSTER:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";EDNA_proc_BUSTER:none"

        if os.path.exists(sample+"/fastdp/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_BUSTER:full"
        elif os.path.exists(sample+"/fastdp/BUSTER/") and not os.path.exists(sample+"/fastdp/BUSTER/final.pdb"):
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_BUSTER:partial"
        else:
            dataRefStatusDict[sample.split("/")[-2]]+=";fastdp_BUSTER:none"

        with open(path+"/fragmax/process/rfstatus.csv","w") as outp:
            for key,value in dataRefStatusDict.items():
                outp.write(key+":"+value+"\n")
            

        ### LIGAND FITTING
        if "Apo" not in sample:
            for d in dp:
                for r in rf:
                    ligset=sample.split("/")[-2]+"_"+d+"_"+r
                    #### RHOFIT
                    if os.path.exists(path+"/fragmax/results/ligandfit"+"/"+ligset+"/rhofit/best.pdb"):
                            try:
                                dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_rhofit:full"
                            except:
                                dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_rhofit:full"
                    elif os.path.exists(path+"/fragmax/results/ligandfit"+"/"+ligset+"/rhofit/") and not os.path.exists(path+"/fragmax/results/ligandfit"+"/"+ligset+"/rhofit/best.pdb"):
                            try:
                                dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_rhofit:partial"
                            except:
                                dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_rhofit:partial"
                    else:
                            try:
                                dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_rhofit:none"
                            except:
                                dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_rhofit:none"


                    #### PHENIX LIGFIT
                    if os.path.exists(path+"/fragmax/results/ligandfit"+"/"+ligset+"/LigandFit_run_1_/ligand_fit_1.pdb"):
                            try:
                                dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_ligandfit:full"
                            except:
                                dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_ligandfit:full"
                    elif os.path.exists(path+"/fragmax/results/ligandfit"+"/"+ligset+"/rhofit/") and not os.path.exists(path+"/fragmax/results/ligandfit"+"/"+ligset+"/LigandFit_run_1_/ligand_fit_1.pdb"):
                            try:
                                dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_ligandfit:partial"
                            except:
                                dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_ligandfit:partial"
                    else:
                            try:
                                dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_ligandfit:none"
                            except:
                                dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_ligandfit:none"
        else:
            for d in dp:
                for r in rf:
                    ligset=sample.split("/")[-2]+"_"+d+"_"+r
                    try:
                        dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_rhofit:none"
                    except:
                        dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_rhofit:none"
                    try:
                        dataLigStatusDict[sample.split("/")[-2]]+=";"+d+"_"+r+"_ligandfit:none"
                    except:
                        dataLigStatusDict[sample.split("/")[-2]]=";"+d+"_"+r+"_ligandfit:none"

        with open(path+"/fragmax/process/lgstatus.csv","w") as outp:
            for key,value in dataLigStatusDict.items():
                outp.write(key+":"+value+"\n")
            
def get_project_status_initial():
    dataProcStatusDict=dict()
    dp=["autoproc","dials","xdsxscale","EDNA_proc","fastdp","xdsapp"]
    sampleList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/") 
    for sample in sampleList:
        
        
        ### DATA PROCESSING
        #### AUTOPROC
        if os.path.exists(sample+"autoproc/"):
            if os.path.exists(sample+"autoproc/summary.html"):
                dataProcStatusDict[sample.split("/")[-2]]=";autoproc:full"
            else:
                dataProcStatusDict[sample.split("/")[-2]]=";autoproc:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]=";autoproc:none"

        #### DIALS
        if os.path.exists(sample+"dials/xia2.html"):
            dataProcStatusDict[sample.split("/")[-2]]+=";dials:full"
        elif os.path.exists(sample+"dials/xia2.error"):
            dataProcStatusDict[sample.split("/")[-2]]+=";dials:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";dials:none"

        #### XDSXSCALE
        if os.path.exists(sample+"xdsxscale/xia2.html"):
            dataProcStatusDict[sample.split("/")[-2]]+=";xdsxscale:full"
        elif os.path.exists(sample+"xdsxscale/xia2.error"):
            dataProcStatusDict[sample.split("/")[-2]]+=";xdsxscale:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";xdsxscale:none"

        #### EDNA_PROC
        autosample="/".join(sample.split("/")[:-2])+"/"+"xds_"+sample.split("/")[-2]+"_1/".replace("/fragmax/","/")
        if os.path.exists(autosample+"EDNA_proc/results/"):
            if os.path.exists(autosample+"EDNA_proc/results/ep_"+autosample.split("/")[-2]+"_noanom.mtz"):
                dataProcStatusDict[autosample.split("/")[-2][4:-2]]+=";EDNA_proc:full"
            else:
                dataProcStatusDict[autosample.split("/")[-2][4:-2]]+=";EDNA_proc:partial"
        else:
            dataProcStatusDict[autosample.split("/")[-2][4:-2]]+=";EDNA_proc:none"

        #### XDSAPP
        if os.path.exists(sample+"xdsapp/"):
            if os.path.exists(sample+"xdsapp/results_"+sample.split("/")[-2]+"_data.txt"):                
                dataProcStatusDict[sample.split("/")[-2]]+=";xdsapp:full"                
            else:
                dataProcStatusDict[sample.split("/")[-2]]+=";xdsapp:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";xdsapp:none"

        #### FASTDP
        if os.path.exists(autosample+"fastdp/results/"):
            if os.path.exists(autosample+"fastdp/results/ap_"+sample.split("/")[-2][:-1]+"_run1_noanom_fast_dp.mtz.gz"):
                dataProcStatusDict[sample.split("/")[-2]]+=";fastdp:full"
            else:
                dataProcStatusDict[sample.split("/")[-2]]+=";fastdp:partial"
        else:
            dataProcStatusDict[sample.split("/")[-2]]+=";fastdp:none"
            
        with open(path+"/fragmax/process/dpstatus.csv","w") as outp:
            for key,value in dataProcStatusDict.items():
                outp.write(key+":"+value+"\n")
###############################

#################################
