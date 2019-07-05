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
import csv
import subprocess
import h5py
import itertools
from time import sleep
import time
import threading
import pypdb
import ast
import sys 
import xmltodict
from subprocess import Popen, PIPE
import datetime
from collections import Counter





################################
#User specific data
#Changing this parameters for different projects based on user credentials



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
    proposal_type = prjset.split(";")[4].split(":")[-1]
    fraglib  = prjset.split(";")[5].split(":")[-1].replace("\n","") 


    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
    static_datapath="/static/biomax/"+proposal+"/"+shift
    #fraglib="F2XEntry"
    #fraglib="JBS"
    os.makedirs(path+"/fragmax/process/",exist_ok=True)
    os.makedirs(path+"/fragmax/scripts/",exist_ok=True)
    os.makedirs(path+"/fragmax/results/",exist_ok=True)
    os.makedirs(path+"/fragmax/logs/",exist_ok=True)

    

    
    return proposal, shift, acronym, proposal_type, path, subpath, static_datapath,fraglib


proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

if len(proposal)<7 or len(shift)<7 or len(acr)<1 or len(proposal_type)<5:

    acr="ProteinaseK"
    proposal="20180479"
    shift="20190323"
    proposal_type="visitors"
    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
    static_datapath="/static/biomax/"+proposal+"/"+shift

################################

def index(request):
    return render(request, "fragview/index.html")

def error_page(request):
    return render(request, "fragview/error.html")

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

def load_project_summary(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
    

####NOT used anymore
def project_summary_load(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    a=str(request.GET.get('submitProc')) 
    out="No option selected"
    if "colParam" in a:
        create_dataColParam(acr,path)
        out="Data collection parameters synced"    
        out="PanDDA result summary synced"
    elif "procRef" in a:
        resultSummary()    
        out="Data processing and Refinement results synced"
    elif "ligfitting" in a:
        out="Ligand fitting results synced"
    return render(request,'fragview/project_summary_load.html', {'option': out})
##############


def dataset_info(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    dataset=str(request.GET.get('proteinPrefix'))     
    prefix=dataset.split(";")[0]
    images=dataset.split(";")[1]
    run=dataset.split(";")[2]

    images=str(int(images)/2)
    xmlfile=path+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+".xml"
    datainfo=retrieveParameters(xmlfile)    

    energy=format(12.4/float(datainfo["wavelength"]),".2f")
    totalExposure=str(float(datainfo["exposureTime"])*float(datainfo["numberOfImages"]))
    edgeResolution=str(float(datainfo["resolution"])*0.75625)
    ligpng="/static/img/nolig.png"
    if "Apo" not in prefix.split("-"):
        ligpng=prefix.split("-")[-1]

    fragConc="100 mM"
    solventConc="15%"
    soakTime="24h"

    snapshot1=datainfo["snapshot1"].replace("/mxn/groups/ispybstorage/","/static/")
    if datainfo["snapshot2"]=="None":
        snapshot2=datainfo["snapshot1"].replace("/mxn/groups/ispybstorage/","/static/")
    else:
        snapshot2=datainfo["snapshot2"].replace("/mxn/groups/ispybstorage/","/static/")

    diffraction1=path.replace("/data/visitors/","/static/")+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_1.jpeg"
    if not os.path.exists(diffraction1):    
        h5data=path+"/raw/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_data_0000"
        cmd="adxv -sa "+h5data+"01.h5 "+diffraction1.replace("/static/","/data/visitors/")
        subprocess.call(cmd,shell=True)
        
    diffraction2=path.replace("/data/visitors/","/static/")+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_2.jpeg"
    if not os.path.exists(diffraction2):        
        half=int(float(images)/200)
        if half<10:
            half="0"+str(half)
        h5data=path+"/raw/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_data_0000"
        cmd="adxv -sa "+h5data+half+".h5 "+diffraction2.replace("/static/","/data/visitors/")
        subprocess.call(cmd,shell=True)
    

    if "Apo" in prefix:
        soakTime="Soaking not performed"
        fragConc="-"
        solventConc="-"
    

    return render(request,'fragview/dataset_info.html', {
        "proposal":proposal,
        "shift":shift,
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
        "snapshot1":snapshot1,
        "snapshot2":snapshot2,    
        "diffraction1":diffraction1,
        "diffraction2":diffraction2,    
        "ybeampos":datainfo["ybeampos"],        
        "energy":energy,
        "totalExposure":totalExposure,
        "edgeResolution":edgeResolution,
        "acr":prefix.split("-")[0],
        "fraglib":fraglib
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    resyncAction=str(request.GET.get("resyncdsButton"))
    resyncImages=str(request.GET.get("resyncImgButton"))
    resyncStatus=str(request.GET.get("resyncstButton"))
    create_dataColParam(acr,path) 

    if "resyncDataset" in resyncAction:
        shutil.move(path+"/fragmax/process/"+acr+"/datacollections.csv",path+"/fragmax/process/"+acr+"/datacollectionsold.csv")
        create_dataColParam(acr,path)
    
    if "resyncStatus" in resyncStatus:
        get_project_status()
        if not os.path.exists(path+"/fragmax/results/"):
            get_project_status_initial()
        
    
    with open(path+"/fragmax/process/"+acr+"/datacollections.csv","r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)
        acr_list=[x[3] for x in lines[1:]]
        smp_list=[x[1] for x in lines[1:]]
        prf_list=[x[0] for x in lines[1:]]
        res_list=[x[6] for x in lines[1:]]
        img_list=[x[5] for x in lines[1:]]
        path_list=[x[2] for x in lines[1:]]
        snap_list=[x[7].split(",")[0].replace("/mxn/groups/ispybstorage/","/static/") for x in lines[1:]]
        png_list=[x[8] for x in lines[1:]]
        run_list=[x[4] for x in lines[1:]]
    dpentry=list()
    rfentry=list()
    lgentry=list()




    ##Proc status
    if os.path.exists(path+"/fragmax/process/"+acr+"/dpstatus.csv"):
        with open(path+"/fragmax/process/"+acr+"/dpstatus.csv") as inp:
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
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/DIALS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDSAPP</font></p>
                    <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> fastdp</font></p>
                    <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> EDNA_proc</font></p>    
                </td>""")
    else:
        for i in prf_list:
            dpentry.append("""<td>
                    <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> autoPROC</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/DIALS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDSAPP</font></p>
                    <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> fastdp</font></p>
                    <p align="left"><font size="2" color="green">&#9679;</font><font size="2"> EDNA_proc</font></p>    
                </td>""")
    ##Ref status
    if os.path.exists(path+"/fragmax/process/"+acr+"/rfstatus.csv"):
        with open(path+"/fragmax/process/"+acr+"/rfstatus.csv") as inp:
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
    if os.path.exists(path+"/fragmax/process/"+acr+"/lgstatus.csv"):
        with open(path+"/fragmax/process/"+acr+"/lgstatus.csv") as inp:
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
                        lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>'
                        lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
                        lgentry.append(lge)     
                else:
                        lge="<td>"
                        lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>'
                        lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
                        lgentry.append(lge)        
                                
            else:
                lge="<td>"
                lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>'
                lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
                lgentry.append(lge)
    else:
        for i,j in zip(prf_list,run_list):
            lge="<td>"
            lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>'
            lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
            lgentry.append(lge)
    
    results = zip(img_list,prf_list,res_list,path_list,snap_list,acr_list,png_list,run_list,smp_list,dpentry,rfentry,lgentry)
    return render(request,'fragview/datasets.html', {'files': results})
    # except:
    #     return render_to_response('fragview/datasets_notready.html')    
    
def results(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    resync=str(request.GET.get("resync"))
    if "resyncresults" in resync:
        resultSummary()
    if not os.path.exists(path+"/fragmax/process/"+acr+"/results.csv"):
        resultSummary()
    try:
        with open(path+"/fragmax/process/"+acr+"/results.csv","r") as readFile:
            reader = csv.reader(readFile)
            lines = list(reader)[1:]
        return render(request, "fragview/results.html",{"csvfile":lines})    
    except:
        return render_to_response('fragview/results_notready.html')

def results_density(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    value=str(request.GET.get('structure'))     
    with open(path+"/fragmax/process/"+acr+"/results.csv","r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]
    result_info=list(filter(lambda x:x[0]==value,lines))[0]
    usracr,pdbout,nat_map,dif_map,spg,resolution,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,ligfit_dataset,pipeline,rhofitscore,ligfitscore,ligblob=result_info        
    
    if os.path.exists(path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final.mtz"):
        if not os.path.exists(path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final_2mFo-DFc.ccp4"):
            cmd="cd "+path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/ ;"
            cmd+="phenix.mtz2map "+path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final.mtz"
            subprocess.call(cmd,shell=True)


    refineM        = pipeline.split("_")[1]
    processM       = pipeline.split("_")[0]


    if "apo" not in usracr.lower():
        ligbox    = "block"
        ligfitbox = "block"
        rhofitbox = "block"
        rpos      = 0
        lpos      = 0
        lig       = usracr.split("-")[-1].split("_")[0]
        ligsvg    = path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".svg"    
        if os.path.exists(path+"/fragmax/results/"+ligfit_dataset+"/"+processM+"/"+refineM+"/rhofit/best.pdb"):
            rhofit=path+"/fragmax/results/"+ligfit_dataset+"/"+processM+"/"+refineM+"/rhofit/best.pdb"
            lpos=1        
            with open(rhofit,"r") as rhofitfile:
                for line in rhofitfile.readlines():
                    if line.startswith("HETATM"):
                        rhocenter="["+",".join(line[32:54].split())+"]"
                        break
        else:
            rhofit=""
            rhocenter="[0,0,0]"
            rhofitbox="none"
        try:
            ligfit=sorted(glob.glob(path+"/fragmax/results/"+ligfit_dataset+"/"+processM+"/"+refineM+"/ligfit/LigandFit_run_*/ligand*.pdb"))[-1]
            with open(ligfit,"r") as ligfitfile:
                for line in ligfitfile.readlines():
                    if line.startswith("HETATM"):
                        ligcenter="["+",".join(line[32:54].split())+"]"
                        break
        except:
            ligfit=""
            ligcenter="[0,0,0]"
            ligfitbox="none"
        
        
    else:
        ligfit=""
        rhofit=""
        rhofitscore="-"
        ligfitscore="-"
        ligcenter="[]"
        rhocenter="[]"
        ligsvg="/static/img/apo.png"
        ligbox="none"
        rhofitbox="none"
        ligfitbox="none"
        rpos=0
        lpos=0

    try:
        currentpos=[n for n,line in enumerate(lines) if usracr in line[0]][0]
        if currentpos==len(lines)-1:
            prevstr=lines[currentpos-1][0]
            nextstr=lines[0][0]
        elif currentpos==0:
            prevstr=lines[-1][0]
            nextstr=lines[currentpos+1][0]

        else:
            prevstr=lines[currentpos-1][0]
            nextstr=lines[currentpos+1][0]

    except:
        currentpos=0
        prevstr=usracr
        nextstr=usracr

    ##fix paths
    rpath=path.replace("/data/visitors/","")
    pdbout=pdbout.replace("/data/visitors/","/static/")
    ligfit=ligfit.replace("/data/visitors/","/static/")
    rhofit=rhofit.replace("/data/visitors/","/static/")
    ##get xyz for ligands
    blist=blist.replace(" ","")
    center=blist[1:blist.index("]")+1]

    if rhofitbox=="none" or ligfitbox=="none":
        dualviewbox="none"
    else:
        dualviewbox="block"

    return render(request,'fragview/density.html', {
        "name":usracr,
        "pdb":pdbout,
        "nat":nat_map,
        "dif":dif_map,
        "xyzlist":blist,
        "center":center,
        "ligand":ligsvg,
        "rscore":rhofitscore,
        "lscore":ligfitscore,
        "rwork":r_work,
        "rfree":r_free,
        "resolution":resolution,
        "spg":spg,
        'ligfit_dataset': ligfit_dataset,
        "process":processM,
        "refine":refineM,
        'blob': ligblob, 
        "path":rpath,
        "rhofitcenter":rhocenter,
        "ligfitcenter":ligcenter, 
        "ligbox":ligbox,
        "prevstr":prevstr,
        "nextstr":nextstr,
        "ligfitbox":ligfitbox,
        "rhofitbox":rhofitbox,
        "dualviewbox":dualviewbox,
        "lpos":lpos,
        "rpos":rpos,
        "ligfitpdb":ligfit,
        "rhofitpdb":rhofit
        })

def testfunc(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    
    return render(request, "fragview/testpage.html",{"files":"results"})    
    
def ugly(request):
    return render(request,'fragview/ugly.html')

def dual_ligand(request):
    try:
        a="load maps and pdb"
        return render(request,'fragview/dual_ligand.html', {'Report': a})
    except:
        return render(request,'fragview/dual_ligand_notready.html', {'Report': a})

def compare_poses(request):   
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    a=str(request.GET.get('ligfit_dataset')) 
    data=a.split(";")[0]
    blob=a.split(";")[1]
    lig=data.split("-")[-1].split("_")[0]
    ligpng=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".svg"    
    

    rhofit=path+"/fragmax/results/"+"_".join(data.split("_")[:2])+"/"+data.split("_")[2]+"/"+data.split("_")[3]+"/rhofit/best.pdb"
    ligfit=sorted(glob.glob(path+"/fragmax/results/"+"_".join(data.split("_")[:2])+"/"+data.split("_")[2]+"/"+data.split("_")[3]+"/ligfit/LigandFit*/ligand_fit*pdb"))[-1]
    pdb   =path.replace("/data/visitors/","/static/")+"/fragmax/results/"+"_".join(data.split("_")[:2])+"/"+data.split("_")[2]+"/"+data.split("_")[3]+"/final.pdb"
    nat   =path.replace("/data/visitors/","/static/")+"/fragmax/results/"+"_".join(data.split("_")[:2])+"/"+data.split("_")[2]+"/"+data.split("_")[3]+"/final_mFo-DFc.ccp4"
    dif   =path.replace("/data/visitors/","/static/")+"/fragmax/results/"+"_".join(data.split("_")[:2])+"/"+data.split("_")[2]+"/"+data.split("_")[3]+"/final_2mFo-DFc.ccp4"
 
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
    rhofit=rhofit.replace("/data/visitors/","/static/")
    ligfit=ligfit.replace("/data/visitors/","/static/")
    return render(request,'fragview/dual_density.html', {
        'ligfit_dataset': data,
        'blob': blob, 
        'png':ligpng, 
        "path":path,
        "rhofitcenter":rhocenter,
        "ligandfitcenter":ligcenter, 
        "ligand":fraglib+"_"+lig,
        "pdb":pdb,
        "dif":dif,
        "nat":nat,
        "rhofit":rhofit,
        "ligfit":ligfit
        })

def ligfit_results(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
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

################ PIPEDREAM #####################

def pipedream(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()   

    datasetPathList=glob.glob(path+"/raw/"+acr+"/*/*master.h5")
    datasetPathList=natsort.natsorted(datasetPathList)
    datasetNameList= [i.split("/")[-1].replace("_master.h5","") for i in datasetPathList if "ref-" not in i] 
    datasetList=zip(datasetPathList,datasetNameList)
    return render(request, "fragview/pipedream.html",{"data":datasetList})

def pipedream_results(request):

    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()   

    resync=str(request.GET.get("resync"))
    if "resyncresults" in resync:
        get_pipedream_results()
    if not os.path.exists(path+"/fragmax/process/"+acr+"/pipedream.csv"):
            get_pipedream_results()
    try:       
        with open(path+"/fragmax/process/"+acr+"/pipedream.csv","r") as readFile:
            reader = csv.reader(readFile)
            lines = list(reader)[1:]
        return render_to_response('fragview/pipedream_results.html', {'files': lines})
    except:
        #return render_to_response('fragview/index.html')
        pass
    return render(request, "fragview/pipedream_results.html")

def submit_pipedream(request):

    #Function definitions
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
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
        ppdoutdir=path+"/fragmax/process/"+acr+"/"+input_data.split(acr+"/")[-1].replace("_master.h5","")+"/pipedream"

        os.makedirs("/".join(ppdoutdir.split("/")[:-1]),exist_ok=True)
        if os.path.exists(ppdoutdir):
            shutil.rmtree(ppdoutdir)
        #     try:
        #         int(ppdoutdir[-1])
        #     except ValueError:
        #         run="1"
        #     else:
        #         run=str(int(ppdoutdir[-1])+1)
            

        #     ppdoutdir=ppdoutdir+"_run"+run
        
        if len(b_userPDBcode.replace("b_userPDBcode:",""))==4:
            userPDB=b_userPDBcode.replace("b_userPDBcode:","")
            userPDBpath=path+"/fragmax/process/"+userPDB+".pdb"
            
            ## Download and prepare PDB _file - remove waters and HETATM
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
            ligand = input_data.split("/")[8].split("-")[-1]
                            
        elif "false" in rho_ligandfromname:
            if len(rho_ligandcode)>15:
                ligand=rho_ligandcode.replace("rho_ligandcode:","")
            elif len(rho_ligandsmiles)>17:
                ligand=rho_ligandsmiles.replace("rho_ligandsmiles:","")
        
        rhofitINPUT=" -rhofit "+path+"/fragmax/process/fragment/"+fraglib+"/"+ligand+"/"+ligand+".cif"
        
            
        


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
                if ncluster=="":
                    ncluster=1
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            if ncluster=="":
                    ncluster=1
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
        ppdoutdirList=[path+"/fragmax/process/"+acr+"/"+x.split(acr+"/")[-1].replace("_master.h5","")+"/pipedream" for x in ppddatasetList]
        
        
        if len(b_userPDBcode.replace("b_userPDBcode:",""))==4:
            userPDB=b_userPDBcode.replace("b_userPDBcode:","")
            userPDBpath=path+"/fragmax/process/"+userPDB+".pdb"
            
            ## Download and prepare PDB _file - remove waters and HETATM
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
                if ncluster=="":
                    ncluster=1
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            if ncluster=="":
                    ncluster=1
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
        
        header=""
        header+= """#!/bin/bash\n"""
        header+= """#!/bin/bash\n"""
        header+= """#SBATCH -t 99:55:00\n"""
        header+= """#SBATCH -J pipedream\n"""
        header+= """#SBATCH --exclusive\n"""
        header+= """#SBATCH -N1\n"""
        header+= """#SBATCH --cpus-per-task=40\n"""
        #header+= """#SBATCH --mem=220000\n""" 
        header+= """#SBATCH -o """+path+"""/fragmax/logs/pipedream_allDatasets_%j.out\n"""
        header+= """#SBATCH -e """+path+"""/fragmax/logs/pipedream_allDatasets_%j.err\n"""    
        header+= """module purge\n"""
        header+= """module load autoPROC BUSTER\n\n"""
        scriptList=list()

        for ppddata,ppdout in zip(ppddatasetList,ppdoutdirList):            
            chdir="cd "+"/".join(ppdout.split("/")[:-1])
            if "apo" not in ppddata.lower():
                ligand = ppddata.split("/")[8].split("-")[-1]
                rhofitINPUT=" -rhofit "+path+"/fragmax/process/fragment/"+fraglib+"/"+ligand+"/"+ligand+".cif "+keepH+clusterSearch+fitrefineMode+postrefineMode+scanChirals+occRef
            if "apo" in ppddata.lower():
                rhofitINPUT=""
            ppd="pipedream -h5 "+ppddata+" -d "+ppdout+" -xyzin "+userPDBpath+rhofitINPUT+useANISO+refineMode+pdbREDO+" -nofreeref -nthreads -1 -v"
        
            allPipedreamOut=chdir+"\n"
            allPipedreamOut+=ppd+"\n\n"
            
            scriptList.append(allPipedreamOut)
        chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,35) )]

        for num,chunk in enumerate(chunkScripts):
            time.sleep(0.2)
            with open(path+"/fragmax/scripts/pipedream_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)
                    
            script=path+"/fragmax/scripts/pipedream_part"+str(num)+".sh"
            command ='echo "module purge | module load autoPROC BUSTER | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)

        
    return render(request, "fragview/submit_pipedream.html",{"command":"<br>".join(ppdCMD.split(";;"))})
    
def get_pipedream_results():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    with open(path+"/fragmax/process/"+acr+"/pipedream.csv","w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["sample","summaryFile","fragment","fragmentLibrary","symmetry","resolution","rwork","rfree","rhofitscore","a","b","c","alpha","beta","gamma"])
        for summary in glob.glob(path+"/fragmax/process/"+acr+"/*/*/pipedream/summary.xml"):
            xmlDict=dict()
            with open(summary) as fd:
                doc=fd.read()

            for p in pList:
                try:
                    for i in doc[doc.index("<"+p+">")+len("<"+p+">"):doc.index("</"+p+">")].split():
                        key=i.split(">")[0][1:]
                        value=i.split(">")[1].split("<")[0]
                        if value != "":
                            xmlDict[key]=value
                except:
                    pass
            for n,i in enumerate(doc.split()):
                if "<R>" in i:            
                    xmlDict["R"]=i[3:9]
                if "<Rfree>" in i:
                    xmlDict["Rfree"]=i[7:13]
                if "id=" in i:
                    xmlDict["ligand"]=i.split('"')[1]               
                if "correlationcoefficient" in i:    
                    xmlDict["rhofitscore"]=i[24:30]                
                if "reshigh" in i:            
                    xmlDict["resolution"]=i[9:13]
            xmlDict["sample"]=summary.replace("/data/visitors/","/static/").split("/")[-3]
            if xmlDict!={}:        
                if "rhofitscore" not in xmlDict:
                    xmlDict["rhofitscore"]="-"
                if "ligand" not in xmlDict:
                    xmlDict["ligand"]="Apo"
                if "resolution" in xmlDict:
                    writer.writerow([xmlDict["sample"],summary.replace("/data/visitors/","/static/").replace(".xml",".out"),xmlDict["ligand"],fraglib,xmlDict["symm"],xmlDict["resolution"],xmlDict["R"],xmlDict["Rfree"],xmlDict["rhofitscore"],xmlDict["a"],xmlDict["b"],xmlDict["c"],xmlDict["alpha"],xmlDict["beta"],xmlDict["gamma"]])
        
def load_pipedream_density(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    sample=str(request.GET.get('structure')) 

    with open(path+"/fragmax/process/"+acr+"/pipedream.csv","r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]
    
    for n,line in enumerate(lines):
        if line[0]==sample:
            ligand      =line[4]
            symmetry    =sym2spg(line[5])
            resolution  =line[6]
            rwork       =line[7]
            rfree       =line[8]
            rhofitscore =line[10]
            currentpos=n
            if currentpos==len(lines)-1:
                prevstr=lines[currentpos-1][0]
                nextstr=lines[0][0]
            elif currentpos==0:
                prevstr=lines[-1][0]
                nextstr=lines[currentpos+1][0]

            else:
                prevstr=lines[currentpos-1][0]
                nextstr=lines[currentpos+1][0]
            
    

    if "Apo" not in sample:
        files = glob.glob(path+"/fragmax/process/"+acr+"/*/"+sample+"/pipedream/rhofit*/")
        files.sort(key=lambda x: os.path.getmtime(x))
        if files!=[]:
            pdb=files[-1]+"refine.pdb"
            dif=files[-1]+"refine_mFo-DFc.ccp4"
            nat=files[-1]+"refine_2mFo-DFc.ccp4"
            mtz=files[-1]+"refine.mtz"
            rhofit=files[-1]+"best.pdb"
        with open(rhofit,"r") as inp:
            for line in inp.readlines():
                if line.startswith("HETATM"):
                    center="["+",".join(line[32:54].split())+"]"
        cE="true"

    else:
        files = glob.glob(path+"/fragmax/process/"+acr+"/*/"+sample+"/pipedream/refine*/")
        files.sort(key=lambda x: os.path.getmtime(x))
        if files!=[]:
            pdb=files[-1]+"refine.pdb"
            dif=files[-1]+"refine_mFo-DFc.ccp4"
            nat=files[-1]+"refine_2mFo-DFc.ccp4"
            mtz=files[-1]+"refine.mtz"
            rhofit=""
            rhofitscore="-"
            center="[0,0,0]"
            cE="false"
            
            
    if os.path.exists(mtz):
        if not os.path.exists(dif):
            cmd="cd "+files[-1]+";"
            cmd+="phenix.mtz2map "+mtz
            subprocess.call(cmd,shell=True)

        #name,pdb,nat,dif,frag,center=a.split(";")
    
                    
       
        
        return render(request,'fragview/pipedream_density.html', {
            "name":sample.replace("/data/visitors/","/static/"),
            "pdb":pdb.replace("/data/visitors/","/static/"),
            "nat":nat.replace("/data/visitors/","/static/"),
            "dif":dif.replace("/data/visitors/","/static/"),
            "rhofit":rhofit.replace("/data/visitors/","/static/"),
            "center":center,
            "symmetry":symmetry,
            "resolution":resolution,
            "rwork":rwork,
            "rfree":rfree,
            "rhofitscore":rhofitscore,
            "ligand":ligand.replace("/data/visitors/","/static/"),
            "prevstr":prevstr,
            "nextstr":nextstr,
            "cE":cE,
            # "name":name,

            # "frag":frag,
            # "prevst":prevst,
            # "nextst":nextst,
            
        })

################ PANDDA #####################

def pandda_density(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    panddaInput=str(request.GET.get('structure'))     
    
    if len(panddaInput.split(";"))==5:
        method,dataset,event,site,nav=panddaInput.split(";")
    if len(panddaInput.split(";"))==3:
        method,dataset,nav=panddaInput.split(";")
    
    mdl=[x.split("/")[-3] for x in sorted(glob.glob(path+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/*/modelled_structures/*model.pdb'))]
    if len(mdl)!=0:
        indices = [i for i, s in enumerate(mdl) if dataset in s][0]
        
        if "prev" in nav:  
                
            try:
                dataset=mdl[indices-1]
            except IndexError:
                dataset=mdl[-1]

        if "next" in nav:
            try:
                dataset=mdl[indices+1]
            except IndexError:
                dataset=mdl[0]



        ligand=dataset.split("-")[-1].split("_")[0]
        modelledDir=path+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/'+dataset+'/modelled_structures/'
        pdb=sorted(glob.glob(modelledDir+"*fitted*"))[-1]
        
        center="[0,0,0]"
        rwork=""
        rfree=""
        resolution=""
        spg=""

        with open(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/pandda_inspect_events.csv","r") as inp:
            inspect_events=inp.readlines()
        for i in inspect_events:
            if dataset in i:
                k=i.split(",")
                break
        headers=inspect_events[0].split(",")
        bdc=k[2]    
        center="["+k[12]+","+k[13]+","+k[14]+"]"
        resolution=k[18]
        rfree=k[20]
        rwork=k[21]
        spg=k[35]
        analysed=k[headers.index("analysed")]
        interesting=k[headers.index("Interesting")]
        ligplaced=k[headers.index("Ligand Placed")]
        ligconfid=k[headers.index("Ligand Confidence")]
        comment=k[headers.index("Comment")]     

        if len(panddaInput.split(";"))==3:
            event=k[1]
            site=k[11]
            
        if "true" in ligplaced.lower():
            ligplaced="lig_radio"
        else:
            ligplaced="nolig_radio"
        
        if "true" in interesting.lower():
            interesting="interesting_radio"
        else:
            interesting="notinteresting_radio"

        if "high" in ligconfid.lower():
            ligconfid="high_conf_radio"
        elif "medium" in ligconfid.lower():
            ligconfid="medium_conf_radio"
        else:
            ligconfid="low_conf_radio"
        

        pdb=pdb.replace("/data/visitors/","")
        map1='biomax/'+proposal+'/'+shift+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/'+dataset+'/'+dataset+'-z_map.native.ccp4'
        map2=glob.glob('/data/visitors/biomax/'+proposal+'/'+shift+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/'+dataset+'/*BDC*ccp4')[0].replace("/data/visitors/","")
        summarypath=('biomax/'+proposal+'/'+shift+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/"+dataset+"/html/"+dataset+".html")
        return render(request,'fragview/pandda_density.html', {
            "siten":site,
            "event":event,
            "dataset":dataset,
            "method":method,
            "rwork":rwork,
            "rfree":rfree,
            "resolution":resolution,
            "spg":spg,
            "shift":shift,
            "proposal": proposal,
            "dataset":dataset,
            "pdb":pdb,
            "2fofc":map2,
            "fofc":map1,
            "fraglib":fraglib,
            "ligand":ligand,
            "center":center,
            "analysed":analysed,
            "interesting":interesting,
            "ligplaced":ligplaced,
            "ligconfid":ligconfid,
            "comment":comment,
            "bdc":bdc,
            "summary":summarypath

            })
    else:
        return render(request,"fragview/error.html",{"issue":"No modelled structure for "+method+"_"+dataset+" was found."})

def pandda_densityC(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    panddaInput=str(request.GET.get('structure'))     
    
    

    
    dataset,site_idx,event_idx,method,ddtag,run=panddaInput.split(";")
    
    
    map1='biomax/'+proposal+'/'+shift+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/'+dataset+ddtag+"_"+run+'/'+dataset+ddtag+"_"+run+'-z_map.native.ccp4'
    map2=glob.glob(path+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/'+dataset+ddtag+"_"+run+'/*BDC*ccp4')[0].replace("/data/visitors/","")
    summarypath=('biomax/'+proposal+'/'+shift+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/"+dataset+ddtag+"_"+run+"/html/"+dataset+ddtag+"_"+run+".html")

    allEventDict, eventDict,low_conf, medium_conf, high_conf = panddaEvents([])
          




    ligand=dataset.split("-")[-1].split("_")[0]+ddtag
    modelledDir=path+'/fragmax/results/pandda/'+method+'/pandda/processed_datasets/'+dataset+ddtag+"_"+run+'/modelled_structures/'
    pdb=sorted(glob.glob(modelledDir+"*fitted*"))[-1]
    pdb=pdb.replace("/data/visitors/","")
    center="[0,0,0]"
    rwork=""
    rfree=""
    resolution=""
    spg=""

    with open(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/pandda_inspect_events.csv","r") as inp:
        inspect_events=inp.readlines()
    for i in inspect_events:
        if dataset+ddtag+"_"+run in i:
            line=i.split(",")
            if dataset+ddtag+"_"+run == line[0] and event_idx==line[1] and site_idx==line[11]:
                k=line
            
    headers=inspect_events[0].split(",")
    bdc=k[2]    
    center="["+k[12]+","+k[13]+","+k[14]+"]"
    resolution=k[18]
    rfree=k[20]
    rwork=k[21]
    spg=k[35]
    analysed=k[headers.index("analysed")]
    interesting=k[headers.index("Interesting")]
    ligplaced=k[headers.index("Ligand Placed")]
    ligconfid=k[headers.index("Ligand Confidence")]
    comment=k[headers.index("Comment")]     

    if len(panddaInput.split(";"))==3:
        event=k[1]
        site=k[11]
        
    if "true" in ligplaced.lower():
        ligplaced="lig_radio"
    else:
        ligplaced="nolig_radio"
    
    if "true" in interesting.lower():
        interesting="interesting_radio"
    else:
        interesting="notinteresting_radio"

    if "high" in ligconfid.lower():
        ligconfid="high_conf_radio"
    elif "medium" in ligconfid.lower():
        ligconfid="medium_conf_radio"
    else:
        ligconfid="low_conf_radio"
        
    
    
    with open(path+"/fragmax/process/"+acr+"/panddainspects.csv","r") as csvFile:        
        reader = csv.reader(csvFile)
        lines = list(reader)
    lines=lines[1:]
    for n,i in enumerate(lines):
        if panddaInput.split(";")==i[:-1]:
            if n==len(lines)-1:
                prevstr=(";".join(lines[n-1][:-1]))
                nextstr=(";".join(lines[0][:-1]))
            elif n==0:
                prevstr=(";".join(lines[-1][:-1]))
                nextstr=(";".join(lines[n+1][:-1]))
            else:
                prevstr=(";".join(lines[n-1][:-1]))
                nextstr=(";".join(lines[n+1][:-1]))
    return render(request,'fragview/pandda_densityC.html', {
        "siten":site_idx,
        "event":event_idx,
        "dataset":dataset+ddtag+"_"+run,
        "method":method,
        "rwork":rwork,
        "rfree":rfree,
        "resolution":resolution,
        "spg":spg,
        "shift":shift,
        "proposal": proposal,
        "dataset":dataset,
        "pdb":pdb,
        "2fofc":map2,
        "fofc":map1,
        "fraglib":fraglib,
        "ligand":ligand,
        "center":center,
        "analysed":analysed,
        "interesting":interesting,
        "ligplaced":ligplaced,
        "ligconfid":ligconfid,
        "comment":comment,
        "bdc":bdc,
        "summary":summarypath,
        "prevstr":prevstr,
        "nextstr":nextstr

        })
    #else:
    #    return render(request,"fragview/error.html",{"issue":"No modelled structure for "+method+"_"+dataset+" was found."})

def pandda_inspect(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    proc_methods=[x.split("/")[-5] for x in glob.glob(path+"/fragmax/results/pandda/*/pandda/analyses/html_summaries/*inspect.html")]
    if proc_methods==[]:
        localcmd="cd "+path+"/fragmax/results/pandda/xdsapp_fspipeline/pandda/; pandda.inspect"
        return render(request,'fragview/pandda_notready.html', {"cmd":localcmd})
    newest=0
    newestpath=""
    newestmethod=""
    filters=[]
    eventscsv=[x for x in glob.glob(path+"/fragmax/results/pandda/*/pandda/analyses/pandda_inspect_events.csv")]
    filterform=request.GET.get("filterForm")
    if not filterform is None:
        if ";" in filterform:
            AP,DI,FD,ED,XD,XA,BU,DP,FS=filterform.split(";")
            xdsapp      =(1 if "true" in XA else 0)
            autoproc    =(1 if "true" in AP else 0)
            dials       =(1 if "true" in DI else 0)
            edna        =(1 if "true" in ED else 0)
            fastdp      =(1 if "true" in FD else 0)
            xdsxscale   =(1 if "true" in XD else 0)
            dimple      =(1 if "true" in DP else 0)
            fspipeline  =(1 if "true" in FS else 0)
            buster      =(1 if "true" in BU else 0)
            filters=list()
            filters.append("autoproc"  )  if AP=="true" else ""
            filters.append("dials"     )  if DI=="true" else ""
            filters.append("fastdp"    )  if FD=="true" else ""
            filters.append("EDNA_proc" )  if ED=="true" else ""
            filters.append("xdsapp"    )  if XA=="true" else ""
            filters.append("xdsxscale" )  if XD=="true" else ""
            filters.append("dimple"    )  if DP=="true" else ""
            filters.append("fspipeline")  if FS=="true" else ""
            filters.append("buster"    )  if BU=="true" else ""
        else:    
            flat_filters=set([j for sub in [x.split("/")[9].split("_") for x in eventscsv] for j in sub])
            xdsapp      =(1 if "xdsapp" in flat_filters else 0)
            autoproc    =(1 if "autoproc" in flat_filters else 0)
            dials       =(1 if "dials" in flat_filters else 0)
            edna        =(1 if "edna" in flat_filters else 0)
            fastdp      =(1 if "fastdp" in flat_filters else 0)
            xdsxscale   =(1 if "xdsxscale" in flat_filters else 0)
            dimple      =(1 if "dimple" in flat_filters else 0)
            fspipeline  =(1 if "fspipeline" in flat_filters else 0)
            buster      =(1 if "buster" in flat_filters else 0)
            
    else:    
        flat_filters=set([j for sub in [x.split("/")[9].split("_") for x in eventscsv] for j in sub])
        xdsapp      =(1 if "xdsapp" in flat_filters else 0)
        autoproc    =(1 if "autoproc" in flat_filters else 0)
        dials       =(1 if "dials" in flat_filters else 0)
        edna        =(1 if "edna" in flat_filters else 0)
        fastdp      =(1 if "fastdp" in flat_filters else 0)
        xdsxscale   =(1 if "xdsxscale" in flat_filters else 0)
        dimple      =(1 if "dimple" in flat_filters else 0)
        fspipeline  =(1 if "fspipeline" in flat_filters else 0)
        buster      =(1 if "buster" in flat_filters else 0)
       


    
    method=request.GET.get("methods")
    if method is None or "panddaSelect" in method or ";" in method:
        
        
        if len(eventscsv)!=0:
            if method is not None and ";" in method:
                filters=list()
                AP,DI,FD,ED,XD,XA,BU,DP,FS=method.split(";")
                filters.append("autoproc"  )  if AP=="true" else ""
                filters.append("dials"     )  if DI=="true" else ""
                filters.append("fastdp"    )  if FD=="true" else ""
                filters.append("EDNA_proc" )  if ED=="true" else ""
                filters.append("xdsapp"    )  if XA=="true" else ""
                filters.append("xdsxscale" )  if XD=="true" else ""
                filters.append("dimple"    )  if DP=="true" else ""
                filters.append("fspipeline")  if FS=="true" else ""
                filters.append("buster"    )  if BU=="true" else ""
            allEventDict,eventDict,low_conf, medium_conf, high_conf =panddaEvents(filters)
            # flat_filters=set([j for sub in [x.split("_") for x in filters] for j in sub])
            # xdsapp      =(1 if "xdsapp" in flat_filters else 0)
            # autoproc    =(1 if "autoproc" in flat_filters else 0)
            # dials       =(1 if "dials" in flat_filters else 0)
            # edna        =(1 if "edna" in flat_filters else 0)
            # fastdp      =(1 if "fastdp" in flat_filters else 0)
            # xdsxscale   =(1 if "xdsxscale" in flat_filters else 0)
            # dimple      =(1 if "dimple" in flat_filters else 0)
            # fspipeline  =(1 if "fspipeline" in flat_filters else 0)
            # buster      =(1 if "buster" in flat_filters else 0)

                    
            sitesL=list() 
            for k,v in eventDict.items():
                sitesL+=[k1 for k1,v1 in v.items()]               
                

            siteN=Counter(sitesL)
            ligEvents=sum(siteN.values())
            siteP=dict()
            for k,v in natsort.natsorted(siteN.items()):
                siteP[k]=100*v/ligEvents
                        
                        
            totalEvents=high_conf+medium_conf+low_conf
            uniqueEvents=str(len(allEventDict.items()))
            
            with open(path+"/fragmax/process/"+acr+"/panddainspects.csv","w") as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(["dataset","site_idx","event_idx","proc_method","ddtag","run","bdc"])
                for k,v in natsort.natsorted(eventDict.items()):
                    for k1,v1 in v.items():
                        dataset=k
                        site_idx=k1.split("_")[0]
                        event_idx=k1.split("_")[1]
                        proc_method="_".join(v1[0].split("_")[0:2])
                        ddtag=v1[0].split("_")[2]
                        run=v1[0].split("_")[3]
                        bdc=v1[1]
                        writer.writerow([dataset,site_idx,event_idx,proc_method,ddtag,run,bdc])


            html =''
            #HTML Head
            html+='    <!DOCTYPE html>\n'
            html+='    <html lang="en">\n'
            html+='      <head>\n'
            html+='        <meta charset="utf-8">\n'
            html+='        <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            html+='        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css">\n'
            html+='        <link rel="stylesheet" href="https://cdn.datatables.net/1.10.11/css/dataTables.bootstrap.min.css">\n'
            html+='        <script src="https://code.jquery.com/jquery-1.12.0.min.js"></script>\n'
            html+='        <script src="https://cdn.datatables.net/1.10.11/js/jquery.dataTables.min.js"></script>\n'
            html+='        <script src="https://cdn.datatables.net/1.10.11/js/dataTables.bootstrap.min.js"></script>\n'
            html+='          <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>\n'
            html+='          <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>\n'
            html+='        <script type="text/javascript" class="init">\n'
            html+='    $(document).ready(function() {\n'
            html+="        $('#main-table').DataTable();\n"
            html+='    } );\n'
            html+='        </script>   \n'
            html+='    <title>PANDDA Inspect Summary</title>\n'
            html+='</head>\n'
            html+='<body>\n'
            html+='    <div class="container">\n'
            html+='      <h1>Consensus of PANDDA Inspect Summaries '+"_".join(filters)+'</h1>\n'
            html+='      <h2>Summary of Inspection of Datasets</h2>\n'
            html+='      \n'
            
            # Styles CSS
            html+='<style>\n'   
            html+='    .container {\n'
            html+='        max-width: 100% !important;\n'
            html+='        margin: 0 50px 50px 150px !important;\n'
            html+='        width: calc(100% - 200px) !important;\n'
            html+='    }\n'
            html+='    .col-md-8 {\n'
            html+='    width: 100% !important;\n'
            html+='    }\n'   
            html+='    </style>\n'
            
            
            #Fitting process plot (necessary?)
            html+='      <div class="row">\n'
            html+='        <div class="col-xs-12">\n'
            html+='          <p>Fitting Progress</p>\n'
            html+='          <div class="progress">\n'
            html+='            <div class="progress-bar progress-bar-success" style="width:100%">\n'
            html+='              <span class="sr-only">Fitted - '+str(ligEvents)+' Events</span>\n'
            html+='              <strong>Fitted - '+str(ligEvents)+' Events (100%)</strong>\n'
            html+='            </div>\n'
            html+='            <div class="progress-bar progress-bar-warning" style="width:0.0%">\n'
            html+='              <span class="sr-only">Unviewed - 0 Events</span>\n'
            html+='              <strong>Unviewed - 0 Events (0%)</strong>\n'
            html+='            </div>\n'
            html+='            <div class="progress-bar progress-bar-danger" style="width:0.0%">\n'
            html+='              <span class="sr-only">No Ligand Fitted - 10 Events</span>\n'
            html+='              <strong>No Ligand Fitted - 10 Events (16%)</strong>\n'
            html+='            </div>\n'
            html+='            </div>\n'
            html+='        </div>\n'
            
            
            #Site distribution plot
            html+='        <div class="col-xs-12">\n'
            html+='          <p>Identified Ligands by Site</p>\n'
            html+='          <div class="progress">\n'
            colour="progress-bar-info"
            for k,v1 in siteP.items():
                
                v=siteN[k]
                html+='            <div class="progress-bar '+colour+'" style="width:'+str(siteP[k])+'%">\n'
                html+='              <span class="sr-only">S'+k+': '+str(v)+' hits</span>\n'
                html+='              <strong>S'+k+': '+str(v)+' hits ('+str(int(siteP[k]))+'%)</strong>\n'
                html+='            </div>\n'
                if colour=="progress-bar-info":
                    colour="progress-bar-default"
                else:
                    colour="progress-bar-info"
            
            
            
            #Inspections facts
            
            html+='            </div>\n'
            html+='        </div>\n'
            html+='        </div>\n'
            html+='      \n'
            html+='      \n'
            html+='      <div class="row">\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert"><strong>Datasets w. ligands: '+str(ligEvents)+' (of #dataset collected)</strong></div></div>\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-success" role="alert"><strong>Sites w. ligands: '+str(len(siteP))+' (of 10)</strong></div></div>\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-4"><div class="alert alert-info" role="alert"><strong>Unique fragments: '+uniqueEvents+'</strong></div></div>\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-info" role="alert"><strong>Total number of events: '+str(totalEvents)+'</strong></div></div>\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-success" role="alert"><strong>High confidence hits:   '+str(high_conf)+'</strong></div></div>\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-warning" role="alert"><strong>Medium confidence hits: '+str(medium_conf)+'</strong></div></div>\n'
            html+='        <div class="col-xs-12 col-sm-12 col-md-3"><div class="alert alert-danger" role="alert"><strong>Low confidence hits:    '+str(low_conf)+'</strong></div></div>\n'
            html+='        </div>\n'
            html+='      \n'
            html+='      \n'
            html+='      <div class="row">\n'
            html+='        </div>\n'
            html+='<hr>\n'
            
            
            
            #Table header
            html+='<div class="table-responsive">\n'
            html+='<table id="main-table" class="table table-bordered table-striped" data-page-length="50">\n'
            html+='    <thead>\n'
            html+='    <tr>\n'
            html+='        <th class="text-nowrap"></th>\n'

            html+='        <th class="text-nowrap">Dataset</th>\n'
            html+='        <th class="text-nowrap">Method</th>\n'
            #html+='        <th class="text-nowrap">Interesting</th>\n'
            #html+='        <th class="text-nowrap">Lig. Placed</th>\n'
            html+='        <th class="text-nowrap">Event</th>\n'
            html+='        <th class="text-nowrap">Site</th>\n'
            html+='        <th class="text-nowrap">1 - BDC</th>\n'
            html+='        <th class="text-nowrap">Z-Peak</th>\n'
            html+='        <th class="text-nowrap">Map Res.</th>\n'
            html+='        <th class="text-nowrap">Map Unc.</th>\n'
            html+='        <th class="text-nowrap">Confidence</th>\n'
            html+='        <th class="text-nowrap">Comment</th>\n'
            html+='        <th class="text-nowrap"></th>\n'
            html+='        </tr>\n'
            html+='    </thead>\n'
            
            
            
            #Table body
            html+='<tbody>\n'
            
            for k,v in natsort.natsorted(eventDict.items()):
                for k1,v1 in v.items():
                    #print(k,k1,v1[0][:-2])
                    detailsDict=datasetDetails(k,k1,v1[0][:-4])
                    #ds=method;dataset;event_id;site_id
                    
                    dataset=k
                    site_idx=k1.split("_")[0]
                    event_idx=k1.split("_")[1]
                    proc_method="_".join(v1[0].split("_")[0:2])
                    ddtag=v1[0].split("_")[2]
                    run=v1[0].split("_")[3]

                    ds=dataset+";"+site_idx+";"+event_idx+";"+proc_method+";"+ddtag+";"+run
                    #ds=v1[0][:-4]+";"+k+v1[0][-3:]+";"+detailsDict['event_idx']+";"+k1
                    #datasetDetails(dataset,site_idx,method)
                    
                    
                    if detailsDict['viewed']=="False\n" or detailsDict['ligplaced']=="False" or detailsDict['interesting']=="False":
                        html+='        <tr class=info>\n'
                    else:
                        html+='        <tr class=success>\n'
                    html+='          <th class="text-nowrap" scope="row" style="text-align: center;"><form action="/pandda_densityC/" method="get" id="pandda_form" target="_blank"><button class="btn" type="submit" value="'+ds+'" name="structure" size="1">Open</button></form></th>\n'
                    html+='          <th class="text-nowrap" scope="row">'+k+v1[0][-3:]+'</th>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span>'+v1[0][:-4]+'</td>\n'
                                        
                    #if detailsDict['interesting']=="True":
                    #    html+='          <td class="text-nowrap text-success"><span class="glyphicon glyphicon-ok" aria-hidden="true"></span> True</td>\n'
                    #else:
                    #    html+='          <td class="text-nowrap text-danger"><span class="glyphicon glyphicon-remove" aria-hidden="true"></span> False</td>\n'
                    #
                    #if detailsDict['ligplaced']=="True":
                    #    html+='          <td class="text-nowrap text-success"><span class="glyphicon glyphicon-ok" aria-hidden="true"></span> True</td>\n'
                    #else:
                    #    html+='          <td class="text-nowrap text-danger"><span class="glyphicon glyphicon-remove" aria-hidden="true"></span> False</td>\n'
                        
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict['event_idx']+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["site_idx"]+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["bdc"]+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["z_peak"]+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["map_res"]+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["map_unc"]+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["ligconfid"]+'</td>\n'
                    html+='          <td class="text-nowrap "><span class="glyphicon " aria-hidden="true"></span> '+detailsDict["comment"]+'</td>\n'
                    html+='          <td><span class="label label-success">Hit</span></td></tr>\n'
            html+='\n'
            html+='</tbody>\n'
            html+='</table>\n'
            html+='</div>\n'
            html+='\n'
            html+='</body>\n'
            html+='</html>\n'
            
            return render(request,'fragview/pandda_inspect.html', {
            'proc_methods':proc_methods, 
            'Report': html,
            'xdsapp':xdsapp,
            'autoproc':autoproc,
            'dials':dials,
            'edna':edna,
            'fastdp':fastdp,
            'xdsxscale':xdsxscale,
            'dimple':dimple,
            'fspipeline':fspipeline,
            'buster':buster,
            })



    else:
        if os.path.exists(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/html_summaries/pandda_inspect.html"):
            with open(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/html_summaries/pandda_inspect.html","r") as inp:
                inspectfile=inp.readlines()
                html=""
                for n,line in enumerate(inspectfile):
                    if '<th class="text-nowrap" scope="row">' in line:
                        
                        event= inspectfile[n+4].split("/span>")[-1].split("</td>")[0].replace(" ","")
                        site = inspectfile[n+5].split("/span>")[-1].split("</td>")[0].replace(" ","")
                        ds=method+";"+line.split('row">')[-1].split('</th')[0]+";"+event+";"+site
                        
                        html+='<td><form action="/pandda_density/" method="get" id="pandda_form" target="_blank"><button class="btn" type="submit" value="'+ds+';stay" name="structure" size="1">Open</button></form>'
                        html+=line
                    else:
                        html+=line
                
                #a=a.replace('class="table-responsive"','').replace('id="main-table" class="table table-bordered table-striped"','id="resultsTable"')
                html="".join(html)
                html=html.replace('<th class="text-nowrap">Dataset</th>','<th class="text-nowrap">Open</th><th class="text-nowrap">Dataset</th>')
                flat_filters=method.split("_")
                xdsapp      =(1 if "xdsapp" in flat_filters else 0)
                autoproc    =(1 if "autoproc" in flat_filters else 0)
                dials       =(1 if "dials" in flat_filters else 0)
                edna        =(1 if "edna" in flat_filters else 0)
                fastdp      =(1 if "fastdp" in flat_filters else 0)
                xdsxscale   =(1 if "xdsxscale" in flat_filters else 0)
                dimple      =(1 if "dimple" in flat_filters else 0)
                fspipeline  =(1 if "fspipeline" in flat_filters else 0)
                buster      =(1 if "buster" in flat_filters else 0)
                return render(request,'fragview/pandda_inspect.html', {'proc_methods':proc_methods, 'Report': html.replace("PANDDA Inspect Summary","PANDDA Inspect Summary for "+method),'xdsapp':xdsapp,
                'autoproc':autoproc,
                'dials':dials,
                'edna':edna,
                'fastdp':fastdp,
                'xdsxscale':xdsxscale,
                'dimple':dimple,
                'fspipeline':fspipeline,
                'buster':buster})
        else:
            a="<div style='padding-left:300px;'> <h5>PanDDA inspect not available yet</h5></div>"
            return render(request,'fragview/pandda.html', {'proc_methods':proc_methods,
            'xdsapp':0,
            'autoproc':0,
            'dials':0,
            'edna':0,
            'fastdp':0,
            'xdsxscale':0,
            'dimple':0,
            'fspipeline':0,
            'buster':0})

def pandda(request):
    return render(request, "fragview/pandda.html")

def submit_pandda(request):

    #Function definitions
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    panddaCMD=str(request.GET.get("panddaform"))
    proc,ref,complete,use_apo,use_dmso,use_cryo,use_CAD,ref_CAD,ign_errordts,keepup_last,ign_symlink=panddaCMD.split(";")
    
    method=proc+"_"+ref
    with open(path+"/fragmax/scripts/pandda_worker.py","w") as outp:
        outp.write('''import os \n'''
        '''import glob\n'''
        '''import sys\n'''
        '''import subprocess \n'''
        '''import shutil\n'''
        '''import multiprocessing \n'''
        '''path=sys.argv[1]\n'''
        '''method=sys.argv[2]\n'''
        '''acr=sys.argv[3]\n'''
        '''fraglib=sys.argv[4]\n'''
        '''if not os.path.exists(path+"/fragmax/results/pandda/"+method):\n'''    
        '''    os.makedirs(path+"/fragmax/results/pandda/"+method)\n'''    
        '''def prepare_pandda_files(method):\n'''        
        '''    proc,ref=method.split("_")\n'''
        '''    missing=list()\n'''
        '''    optionsDict=dict()\n'''
        '''    copypdb=dict()\n'''
        '''    copymtz=dict()\n'''
        '''    copylig=dict()\n'''
        '''    copycif=dict()\n'''
        '''    datasets=sorted([x.split("/")[-2] for x in glob.glob(path+"/raw/"+acr+"/*/*master.h5") if "ref-" not in x])\n'''
        '''    refresults=sorted([x for x in glob.glob(path+"/fragmax/results/*/*/*/final*.pdb" ) if "/pandda/" not in x])\n'''
        '''    selected=sorted([x for x in refresults if proc in x and ref in x and acr in x])\n'''
        '''    for i in datasets:\n'''
        '''        for j in selected:\n'''
        '''            if i in j:\n'''
        '''                missing.append(i)\n'''
        '''    missing=list(set(datasets)-set(missing))\n'''
        '''    for i in missing:\n'''
        '''        options=list()\n'''
        '''        for j in refresults:\n'''
        '''            if i in j:\n'''
        '''                options.append(j)\n'''
        '''        if len(options)>0:\n'''
        '''            optionsDict[i]=options\n'''
        '''    for key,value in optionsDict.items():  \n'''
        '''        for opt in value:             \n'''
        '''            if "xdsapp" in opt or "dials" in opt or "autoproc" in opt:\n'''
        '''                selected.append(opt)\n'''
        '''                break            \n'''
        '''    for i in selected:\n'''
        '''        a=i.split(acr)[0]+"pandda/"+"_".join(i.split("/")[-3:-1])+"/"+i.split("/")[8]+"/final.pdb"\n'''
        '''        copypdb[i]=a\n'''
        '''        copymtz[i.replace(".pdb",".mtz")]=a.replace(".pdb",".mtz")\n'''
        '''        b=i.split("/")[8].split("-")[-1].split("_")[0]\n'''
        '''        if "Apo" not in b:\n'''
        '''            copylig[path+"/fragmax/process/fragment/"+fraglib+"/"+b+"/"+b+".pdb"]="/".join(a.split("/")[:-1])+"/"+b+".pdb"\n'''
        '''            copycif[path+"/fragmax/process/fragment/"+fraglib+"/"+b+"/"+b+".cif"]="/".join(a.split("/")[:-1])+"/"+b+".cif"\n'''
        '''    for src,dst in copypdb.items():\n'''
        '''        if not os.path.exists(dst):\n'''
        '''            if not os.path.exists("/".join(dst.split("/")[:-1])):\n'''
        '''                os.makedirs("/".join(dst.split("/")[:-1]))            \n'''
        '''            shutil.copyfile(src,dst)\n'''
        '''    for src,dst in copymtz.items():\n'''
        '''        if not os.path.exists(dst):\n'''
        '''            if not os.path.exists("/".join(dst.split("/")[:-1])):\n'''
        '''                os.makedirs("/".join(dst.split("/")[:-1]))\n'''
        '''            shutil.copyfile(src,dst)\n'''
        '''    for src,dst in copylig.items():\n'''
        '''        if not os.path.exists(dst):\n'''
        '''            if not os.path.exists("/".join(dst.split("/")[:-1])):\n'''
        '''                os.makedirs("/".join(dst.split("/")[:-1]))\n'''
        '''            shutil.copyfile(src,dst)\n'''
        '''    for src,dst in copycif.items():\n'''
        '''        if not os.path.exists(dst):\n'''
        '''            if not os.path.exists("/".join(dst.split("/")[:-1])):\n'''
        '''                os.makedirs("/".join(dst.split("/")[:-1]))\n'''
        '''            shutil.copyfile(src,dst)\n'''
        '''def pandda_run(method):\n'''
        '''    os.chdir(path+"/fragmax/results/pandda/"+method)\n'''
        '''    command="pandda.analyse data_dirs='"+path+"/fragmax/results/pandda/"+method+"/*' cpus=32"\n'''
        '''    subprocess.call(command, shell=True)\n'''
        '''    if len(glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/logs/*.log"))>0:\n'''
        '''        lastlog=sorted(glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/logs/*.log"))[-1]\n'''
        '''        with open(lastlog,"r") as logfile:\n'''
        '''            log=logfile.readlines()\n'''
        '''        badDataset=dict()\n'''
        '''        for line in log:\n'''
        '''            if "Structure factor column"  in line:\n'''
        '''                bd=line.split(" has ")[0].split("in dataset ")[-1]        \n'''
        '''                bdpath=glob.glob(path+"/fragmax/results/pandda/"+method+"/"+bd+"*")\n'''
        '''                badDataset[bd]=bdpath\n'''
        '''            if "Failed to align dataset" in line:\n'''
        '''                bd=line.split("Failed to align dataset ")[1].rstrip()\n'''
        '''                bdpath=glob.glob(path+"/fragmax/results/pandda/"+method+"/"+bd+"*")\n'''
        '''                badDataset[bd]=bdpath\n'''
        '''        for k,v in badDataset.items():\n'''
        '''            if len(v)>0:\n'''
        '''                if os.path.exists(v[0]):\n'''
        '''                    if os.path.exists(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k):\n'''
        '''                        shutil.rmtree(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k)\n'''
        '''                        shutil.move(v[0], path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k)\n'''
        '''                pandda_run(method)\n'''
        '''def fix_symlinks(method):\n'''
        '''    linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")\n'''
        '''    for i in linksFolder:        \n'''
        '''        folder="/".join(i.split("/")[:-1])+"/"\n'''
        '''        pdbs=os.listdir(folder)\n'''
        '''        pdb=folder+sorted([x for x in pdbs if "fitted" in x])[-1]        \n'''
        '''        shutil.move(i,i+".bak")\n'''
        '''        shutil.copyfile(pdb,i)\n'''
        '''    linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")+glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/*")\n'''
        '''    for _file in linksFolder:       \n'''
        '''        dst=os.path.realpath(_file)    \n'''
        '''        if _file!=dst:  \n'''
        '''            shutil.move(_file,_file+".bak")\n'''
        '''        \n'''
        '''    linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")+glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/*.bak")\n'''
        '''    for _file in linksFolder:       \n'''
        '''        dst=os.path.realpath(_file)    \n'''
        '''        if _file!=dst: \n'''
        '''            shutil.copyfile(dst,_file.replace(".bak",""))\n'''
        '''def CAD_worker(mtzfile):\n'''
        '''    stdout = subprocess.Popen('phenix.mtz.dump '+mtzfile, shell=True, stdout=subprocess.PIPE).stdout\n'''
        '''    output = stdout.read().decode("utf-8")\n'''
        '''    for line in output.split("\\n"):\n'''
        '''        if "Resolution range" in line:\n'''
        '''            highres=line.split()[-1]\n'''
        '''    if "free" in "".join(output).lower():\n'''
        '''        for line in output.split("\\n"):\n'''
        '''            if "free" in line.lower():\n'''
        '''                freeRflag=line.split()[0]\n'''
        '''    else:  \n'''
        '''        freeRflag="R-free-flags"        \n'''
        '''    outmtz=mtzfile.split("final.mtz")[0]+"final.mtz"    \n'''
        '''    os.chdir(mtzfile.replace("/results/","/process/").replace("final.mtz",""))       \n'''
        '''    subprocess.call("uniqueify -f "+freeRflag+" "+mtzfile+" "+mtzfile.replace("/results/","/process/"),shell=True)\n'''
        '''    cadCommand="""cad hklin1 """+mtzfile+ """ hklout """ +outmtz+ """ <<eof\n'''
        ''' monitor BRIEF\n'''
        ''' labin _file 1 - \n'''
        '''  ALL"\n'''
        ''' resolution _file 1 999.0 """+ highres+"""\n'''
        '''eof"""\n'''
        '''    subprocess.call(cadCommand,shell=True)\n'''
        '''    subprocess.call("phenix.maps "+mtzfile.replace(".mtz",".pdb")+" "+mtzfile,shell=True    )\n'''
        '''    subprocess.call("mv -f "+mtzfile.replace("final.mtz","final_2mFo-DFc_map.ccp4 ")+" "+mtzfile.replace(".mtz",".ccp4"),shell=True)\n'''
        '''    subprocess.call("mv -f "+mtzfile.replace("final.mtz","final_map_coeffs.mtz"    )+" "+mtzfile,shell=True)\n'''
        '''    return mtzfile, highres, freeRflag\n'''
        '''def run_CAD():    \n'''
        '''    dataPaths=glob.glob(path+"/fragmax/results/pandda/"+method+"/*/final.mtz")\n'''
        '''    for key in dataPaths:\n'''
        '''        if not os.path.exists(key.replace("/results/","/process/").replace("final.mtz","")):\n'''
        '''            os.makedirs(key.replace("/results/","/process/").replace("final.mtz",""))            \n'''
        '''    nproc=multiprocessing.cpu_count()\n'''
        '''    multiprocessing.Pool(nproc).map(CAD_worker, dataPaths)    \n'''
        '''prepare_pandda_files(method)\n'''
        '''run_CAD()\n'''
        '''pandda_run(method)\n'''
        '''fix_symlinks(method)\n'''
        '''os.system('chmod -R g+rwx path+"/fragmax/results/pandda/"')\n'''
        )

    
    with open(path+"/fragmax/scripts/panddaRUN_"+method+".sh","w") as outp:
            outp.write('#!/bin/bash\n')
            outp.write('#!/bin/bash\n')
            outp.write('#SBATCH -t 99:55:00\n')
            outp.write('#SBATCH -J PanDDA\n')
            outp.write('#SBATCH --exclusive\n')
            outp.write('#SBATCH -N1\n')
            outp.write('#SBATCH --cpus-per-task=48\n')
            outp.write('#SBATCH --mem=220000\n')
            outp.write('#SBATCH -o '+path+'/fragmax/logs/panddarun_%j.out\n')
            outp.write('#SBATCH -e '+path+'/fragmax/logs/panddarun_%j.err\n')
            outp.write('module purge\n')
            outp.write('module load PReSTO\n')
            outp.write('\n')
            outp.write('python '+path+'/fragmax/scripts/pandda_worker.py '+path+' '+method+' '+acr+' '+fraglib+'\n')
    
    script=path+"/fragmax/scripts/panddaRUN_"+method+".sh"
    command ='echo "module purge | module load PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(command,shell=True)
    
    return render(request, "fragview/submit_pandda.html",{"command":panddaCMD})

def pandda_analyse(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    fixsl=request.GET.get("fixsymlinks")
    if not fixsl is None and "FixSymlinks" in fixsl:
        t1 = threading.Thread(target=fix_pandda_symlinks,args=())
        t1.daemon = True
        t1.start()
    proc_methods=[x.split("/")[-2] for x in glob.glob(path+"/fragmax/results/pandda/*/pandda")]
    newest=datetime.datetime.strptime("2000-01-01-1234", '%Y-%m-%d-%H%M')
    newestpath=""
    newestmethod=""
    for methods in proc_methods:
        if len(glob.glob(path+"/fragmax/results/pandda/"+methods+"/pandda/analyses-*"))>0:
            last=sorted(glob.glob(path+"/fragmax/results/pandda/"+methods+"/pandda/analyses-*"))[-1]
            if os.path.exists(last+"/html_summaries/pandda_analyse.html"):
                time = datetime.datetime.strptime(last.split("analyses-")[-1], '%Y-%m-%d-%H%M')
                if time>newest:
                    newest=time
                    newestpath=last
                    newestmethod=methods
    
    method=request.GET.get("methods")

    if method is None or "panddaSelect" in method:
        if os.path.exists(newestpath+"/html_summaries/pandda_analyse.html"):
            with open(newestpath+"/html_summaries/pandda_analyse.html","r") as inp:
                a="".join(inp.readlines())
                localcmd="cd "+path+"/fragmax/results/pandda/"+newestmethod+"/pandda/; pandda.inspect"

                return render(request,'fragview/pandda_analyse.html', {"opencmd":localcmd,'proc_methods':proc_methods, 'Report': a.replace("PANDDA Processing Output","PANDDA Processing Output for "+newestmethod)})
        else:
            running=[x.split("/")[9] for x in glob.glob(path+"/fragmax/results/pandda/*/pandda/*running*")]    
            return render(request,'fragview/pandda_notready.html', {'Report': "<br>".join(running)})

    else:
        if os.path.exists(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/html_summaries/pandda_analyse.html"):
            with open(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/html_summaries/pandda_analyse.html","r") as inp:
                a="".join(inp.readlines())
                localcmd="cd "+path+"/fragmax/results/pandda/"+method+"/pandda/; pandda.inspect"                    
            return render(request,'fragview/pandda_analyse.html', {"opencmd":localcmd,'proc_methods':proc_methods, 'Report': a.replace("PANDDA Processing Output","PANDDA Processing Output for "+method)})
        else:
            running=[x.split("/")[9] for x in glob.glob(path+"/fragmax/results/pandda/*/pandda/*running*")]    
            return render(request,'fragview/pandda_notready.html', {'Report': "<br>".join(running)})

def datasetDetails(dataset,site_idx,method):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    detailsDict=dict()
    with open(path+"/fragmax/results/pandda/"+method+"/pandda/analyses/pandda_inspect_events.csv","r") as inp:
        a=inp.readlines()
    
    for i in a:
        if dataset in i:
            if i.split(",")[11]+"_"+i.split(",")[1]==site_idx:
                k=i.split(",")

    headers=a[0].split(",")
    detailsDict['event_idx']=k[1]
    detailsDict['bdc']=k[2]    
    detailsDict['site_idx']=k[11]
    detailsDict['center']="["+k[12]+","+k[13]+","+k[14]+"]"
    detailsDict['z_peak']=k[16]
    detailsDict['resolution']=k[18]
    detailsDict['rfree']=k[20]
    detailsDict['rwork']=k[21]
    detailsDict['spg']=k[35]
    detailsDict['map_res']=k[headers.index("analysed_resolution")]
    detailsDict['map_unc']=k[headers.index("map_uncertainty")]
    detailsDict['analysed']=k[headers.index("analysed")]
    detailsDict['interesting']=k[headers.index("Interesting")]
    detailsDict['ligplaced']=k[headers.index("Ligand Placed")]
    detailsDict['ligconfid']=k[headers.index("Ligand Confidence")]
    detailsDict['comment']=k[headers.index("Comment")]     
    detailsDict['viewed']=k[headers.index("Viewed\n")]  
    return detailsDict

def panddaEvents(filters):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    eventscsv=[x for x in glob.glob(path+"/fragmax/results/pandda/*/pandda/analyses/pandda_inspect_events.csv") ]
    if len(filters)!=0:
        eventscsv=[x for x in eventscsv if  any(xs in x for xs in filters)]
    eventDict=dict()
    allEventDict=dict()

    high_conf=0
    medium_conf=0
    low_conf=0

    for eventcsv in eventscsv:
        method=eventcsv.split("/")[9]
        with open(eventcsv,"r") as inp:
            a=inp.readlines()
        a=[x.split(",") for x in a]
        headers=a[0]
        for line in a:
            
            if line[headers.index("Ligand Placed")]=="True":
                
                dtag=line[0][:-3]
                event_idx=line[1]
                site_idx=line[11]
                bdc=line[2]
                intersting=line[headers.index("Ligand Confidence")]
                if intersting=="High":
                    high_conf+=1
                if intersting=="Medium":
                    medium_conf+=1
                if intersting=="Low":
                    low_conf+=1
                    
                if dtag not in eventDict:
                    
                    eventDict[dtag]={site_idx+"_"+event_idx:{method+"_"+line[0][-3:]:bdc}}
                    allEventDict[dtag]={site_idx+"_"+event_idx:{method+"_"+line[0][-3:]:bdc}}
                else: 

                    if site_idx not in eventDict[dtag]:
                        eventDict[dtag].update({site_idx+"_"+event_idx:{method+"_"+line[0][-3:]:bdc}})
                        allEventDict[dtag].update({site_idx+"_"+event_idx:{method+"_"+line[0][-3]:bdc}})
                    else:
                        eventDict[dtag][site_idx+"_"+event_idx].update({method+"_"+line[0][-3:]:bdc})
                        allEventDict[dtag][site_idx+"_"+event_idx].update({method+"_"+line[0][-3:]:bdc})


    for k,v in eventDict.items():
        for k1,v1 in v.items():
            v[k1]=sorted(v1.items(), key=lambda t:t[1])[0]
    return allEventDict, eventDict, low_conf, medium_conf, high_conf

def fix_pandda_symlinks():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    for method in [x.split("/")[-1] for x in glob.glob(path+"/fragmax/results/pandda/*")]:
        linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")
        for i in linksFolder:        
            folder="/".join(i.split("/")[:-1])+"/"
            pdbs=os.listdir(folder)
            pdb=folder+sorted([x for x in pdbs if "fitted" in x])[-1]        
            shutil.move(i,i+".bak")
            shutil.copyfile(pdb,i)
        linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")+glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/*")
        for _file in linksFolder:       
            dst=os.path.realpath(_file)    
            if _file!=dst:  
                if ".bak" not in _file:
                    shutil.move(_file,_file+".bak")
            
        linksFolder=glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")+glob.glob(path+"/fragmax/results/pandda/"+method+"/pandda/processed_datasets/*/*.bak")
        for _file in linksFolder:       
            dst=os.path.realpath(_file)    
            if _file!=dst: 
                shutil.copyfile(dst,_file.replace(".bak",""))

    os.system("chmod -R g+rw "+path+"/fragmax/results/pandda/")

#############################################

def procReport(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
        if os.path.exists(a):
            with open(a,"r") as inp:
                html="<br>".join(inp.readlines())
        else:
            html='<h5 style="padding-left:260px;" >XDSAPP report for this dataset is not available</h5>'

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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    outinfo=str(request.GET.get("mergeprocinput")).replace("static","data/visitors")
    
    runList="<br>".join(glob.glob(outinfo+"*/*"))
    
    return render(request,'fragview/dataproc_merge.html', {'datasetsRuns': runList})

def reproc_web(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    dataproc = str(request.GET.get("submitProc"))
    strcrefine=str(request.GET.get("submitRefine"))
    
    if "runProc" in dataproc :       
        runProc,procSW, spg, CellPar, Friedel, DRange, numImgs, ResCutoff, CCCutoff, Isigma, custom, imgdir, dataset = dataproc.split(";")
    
        with open(path+"/fragmax/scripts/man_dataproc.sh","w") as outp:
            outputdir=imgdir.replace("/raw/","/fragmax/process/")+dataset
            outp.write('#!/bin/bash')
            outp.write('\n#!/bin/bash')
            outp.write('\n#SBATCH -t 99:55:00')
            outp.write('\n#SBATCH -J manProc')
            outp.write('\n#SBATCH --exclusive')
            outp.write('\n#SBATCH -N1')
            outp.write('\n#SBATCH --cpus-per-task=40')            
            outp.write('\n#SBATCH -o '+path+'/fragmax/logs/manual_proc_'+procSW+'_%j.out')
            outp.write('\n#SBATCH -e '+path+'/fragmax/logs/manual_proc_'+procSW+'_%j.err')
            outp.write('\n\nmodule purge')
            outp.write('\nmodule load CCP4 XDSAPP autoPROC Phenix BUSTER XDS')


            if "xdsapp" in procSW:
                if Friedel=="":
                    Friedel="True"
                
                if DRange=="":
                    DRange="1\\ "+numImgs
                elif "-" in DRange:
                    DRange=DRange.replace("-","\\ ")
                if spg!="" and CellPar!="":
                    spg=' --spacegroup="'+spg+" "+" ".join(CellPar.split(","))+'"'
                else:
                    spg=""
                if ResCutoff!="":
                    ResCutoff=" --res="+ResCutoff
                dataprocCommand = "xdsapp --cmd --dir "+outputdir+"/xdsapp -j 8 -c 6 -i "+imgdir+dataset+"_master.h5 --fried="+Friedel+spg+ResCutoff+" --range="+DRange+" "+custom
                os.makedirs(outputdir+"/xdsapp",exist_ok=True)
                outp.write('\n'+"cd "+outputdir+"/xdsapp")
                outp.write('\n'+dataprocCommand) 
            if "autoproc" in procSW:
                if Friedel=="" or "true" in Friedel:
                    Friedel=" -ANO "
                else:
                    Friedel=" -noANO "
                if DRange=="":
                    DRange="1\\ "+numImgs
                elif "-" in DRange:
                    DRange=DRange.replace("-","\\ ")
                if spg!="":
                    spg=' symm="'+spg+'" '
                if CellPar!="":
                    CellPar=' cell="'+CellPar+'" '                
            
                dataprocCommand = 'process -h5 '+imgdir+dataset+'_master.h5 -d '+outputdir+'/autoproc '+Friedel+spg+CellPar+'autoPROC_XdsKeyword_LIB=\\$EBROOTNEGGIA/lib/dectris-neggia.so autoPROC_XdsKeyword_ROTATION_AXIS="0 -1 0" autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=6 autoPROC_XdsKeyword_DATA_RANGE='+DRange+' autoPROC_XdsKeyword_SPOT_RANGE='+DRange+' '+custom
                os.makedirs(outputdir,exist_ok=True)
                if os.path.exists(outputdir+"/autoproc"):
                    shutil.move(outputdir+"/autoproc",outputdir+"/autoproc_last")
                outp.write('\n'+"cd "+outputdir)
                outp.write('\n'+dataprocCommand) 

            
            if "dials" in procSW or "xdsxscale" in procSW:
                if "xdsxscale" in procSW:
                    pipeline="3dii"
                else:
                    pipeline=procSW
                if DRange=="":
                    DRange="1:"+numImgs
                elif "-" in DRange:                    
                    DRange=DRange.replace("-",":")
                if spg!="":
                    spg=' space_group="'+spg+'"'
                if CellPar!="":
                    CellPar=' unit_cell="'+CellPar+'"'
                
                dataprocCommand = 'xia2 goniometer.axes=0,1,0 pipeline='+pipeline+' failover=true '+spg+' '+CellPar+' nproc=48  image='+imgdir+dataset+'_master.h5:'+DRange+' multiprocessing.mode=serial  multiprocessing.njob=1  multiprocessing.nproc=auto'+" "+custom
                outp.write('\n'+"cd "+outputdir+"/"+procSW)
                outp.write('\n'+dataprocCommand) 


        command ='echo "module purge | module load CCP4 XDSAPP | sbatch '+path+'/fragmax/scripts/man_dataproc.sh " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
        return render(request,'fragview/reproc_web.html', {'command': dataprocCommand})
    if "runRefine" in strcrefine: 
        refineCommand=strcrefine
        runRefine,procSW,refineSW,refineMode,spg,ResCutoff,mrthresh,pdbmodel,custom,imgdir,dataset=strcrefine.split(";")
        if procSW=="" or refineSW=="":
            return render(request,'fragview/reproc_web.html', {'command': "Please select data processing software AND refine software for this step"})    
        else:
            with open(path+"/fragmax/scripts/man_refine.sh","w") as outp:
                processdir=imgdir.replace("/raw/","/fragmax/process/")+dataset
                dpresdir=path+"/fragmax/results/"+dataset+"/"+procSW
                dprespathmer=dpresdir+"/"+dataset+"_"+procSW+"_merged.mtz"
                dprespathsca=dpresdir+"/"+dataset+"_"+procSW+"_scaled.mtz"
                outp.write('#!/bin/bash') 
                outp.write('\n#!/bin/bash')
                outp.write('\n#SBATCH -t 99:55:00')
                outp.write('\n#SBATCH -J manRefine')
                outp.write('\n#SBATCH --exclusive')
                outp.write('\n#SBATCH -N1')
                outp.write('\n#SBATCH --cpus-per-task=40')            
                outp.write('\n#SBATCH -o '+path+'/fragmax/logs/manual_refine_'+procSW+'_'+refineSW+'_%j.out')
                outp.write('\n#SBATCH -e '+path+'/fragmax/logs/manual_refine_'+procSW+'_'+refineSW+'_%j.err')
                outp.write('\n\nmodule purge')
                outp.write('\nmodule load CCP4 Phenix BUSTER')
                
                if "dimple" in refineSW:
                    refineCommand="\n\ncd "+dpresdir
                    if os.path.exists(dprespathmer):
                        refineCommand+="\ndimple "+dprespathmer+" "+pdbmodel+" "+dpresdir+"/dimple/"
                        outp.write(refineCommand)
                    elif os.path.exists(dprespathsca):
                        refineCommand+="\ndimple "+dprespathsca+" "+pdbmodel+" "+dpresdir+"/dimple/"
                        outp.write(refineCommand)
                    else:
                        return render(request,'fragview/reproc_web.html', {'command': "No mtz _file found. Please make sure you have processed this dataset first."})    
                if "fspipeline" in refineSW:
                    refineCommand="\n\ncd "+dpresdir
                    if os.path.exists(dprespathmer):
                        refineCommand+="\npython /data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py --refine="+pdbmodel+" --exclude='unscaled unmerged scaled final dimple ligfit rhofit' --cpu=40"
                        outp.write(refineCommand)

                    elif os.path.exists(dprespathsca):
                        refineCommand+="\npython /data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py --refine="+pdbmodel+" --exclude='unscaled unmerged scaled final dimple ligfit rhofit' --cpu=40"
                        outp.write(refineCommand)

                    else:
                        return render(request,'fragview/reproc_web.html', {'command': "No mtz _file found. Please make sure you have processed this dataset first."})    
            command ='echo "module purge | module load CCP4 XDSAPP | sbatch '+path+'/fragmax/scripts/man_refine.sh " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)
            return render(request,'fragview/reproc_web.html', {'command': refineCommand})
    return render(request,'fragview/reproc_web.html', {'command': "No valid method selected"})

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
    #if len(userPDB)<20:
    pdbmodel=userPDB.replace("pdbmodel:","")
    # if "ATOM" in userPDB:
    #     userPDB=userPDB.replace("pdbmodel:","")
    #     pdbmodel=path+"fragmax/process/userPDB.pdb"
    #     with open(path+"fragmax/process/userPDB.pdb","w") as pdbfile:
    #         pdbfile.write(userPDB)
    spacegroup=refspacegroup.replace("refspacegroup:","")
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    allprc  = str(request.GET.get("submitallProc"))
    dtprc   = str(request.GET.get("submitdtProc"))
    refprc  = str(request.GET.get("submitrfProc"))
    ligproc = str(request.GET.get("submitligProc"))
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
        pnodes=30
        with open(path+"/fragmax/scripts/processALL.sh","w") as outp:
            outp.write("""#!/bin/bash \n"""
                    """#!/bin/bash \n"""
                    """#SBATCH -t 99:55:00 \n"""
                    """#SBATCH -J FragMAX \n"""
                    """#SBATCH --exclusive \n"""
                    """#SBATCH -N1 \n"""
                    """#SBATCH --cpus-per-task=40 \n"""
                    """#SBATCH -o """+path+"""/fragmax/logs/analysis_workflow_%j.out \n"""
                    """#SBATCH -e """+path+"""/fragmax/logs/analysis_workflow_%j.err \n"""
                    """module purge \n"""
                    """module load DIALS/1.12.3-PReSTO	CCP4 autoPROC BUSTER XDSAPP PyMOL \n"""
                    """python """+path+"/fragmax/scripts/processALL.py"+""" '"""+path+"""' '"""+fraglib+"""' '"""+PDBID+"""' '"""+spg+"""' $1 $2 '"""+",".join(dpSW)+"""' '"""+",".join(rfSW)+"""' '"""+",".join(lfSW)+"""' \n""")
        for node in range(pnodes):
            script=path+"/fragmax/scripts/processALL.sh"
            command ='echo "module purge | module load CCP4 autoPROC DIALS/1.12.3-PReSTO XDSAPP | sbatch '+script+" "+str(node)+" "+str(pnodes)+' " | ssh -F ~/.ssh/ clu0-fe-1'
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
        sbatch_script_list=list()
        nodes=12
        if usexdsapp=="true":
            t = threading.Thread(target=run_xdsapp,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes))
            t.daemon = True
            t.start()
        if usedials=="true":
            t = threading.Thread(target=run_dials,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes))
            t.daemon = True
            t.start()
            
        if useautproc=="true":
            t = threading.Thread(target=run_autoproc,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes))
            t.daemon = True
            t.start()
          
        if usexdsxscale=="true":
            t = threading.Thread(target=run_xdsxscale,args=(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes))
            t.daemon = True
            t.start()
            
        return render(request,'fragview/dataproc_datasets.html', {'allproc': "Jobs submitted using "+str(nodes)+" per method"})

    
    if refprc!="None":
        pass

    if ligproc!="None":
        pass
    return render(request,'fragview/dataproc_datasets.html', {'allproc': "\n"+"\n".join(sbatch_script_list)})

def kill_HPC_job(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()


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

def add_run_DP(outdir):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    if os.path.exists(path+"/fragmax/process/"+acr+"/datacollections.csv"):
        return
    else:        
        os.makedirs(path+"/fragmax/process/"+acr,exist_ok=True)
        with open(path+"/fragmax/process/"+acr+"/datacollections.csv","w") as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(["imagePrefix","SampleName","dataCollectionPath","Acronym","dataCollectionNumber","numberOfImages","resolution","snapshot","ligsvg"])
            
            for xml in natsort.natsorted(glob.glob(path+"/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"), key=lambda x: ("Apo" in x, x)):    
                outdirxml=xml.replace("/process/","/fragmax/process/").split("fastdp")[0].replace("xds_","")[:-3]
                if not os.path.exists(outdirxml+".xml"):
                    if not os.path.exists("/".join(outdirxml.split("/")[:-1])):
                        os.makedirs("/".join(outdirxml.split("/")[:-1]))
                    shutil.copyfile(xml,outdirxml+".xml")        


                with open(xml,"r") as fd:
                    doc = xmltodict.parse(fd.read())

                nIMG       = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["numberOfImages"]
                resolution = "%.2f" % float(doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["resolution"])
                run        = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["dataCollectionNumber"]
                dataset    = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["imagePrefix"]
                sample     = dataset.split("-")[-1]
                snaps      = ",".join([doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["xtalSnapshotFullPath"+i] for i in ["1","2","3","4"] if doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["xtalSnapshotFullPath"+i]!= "None"])
                if len(snaps)<1:
                    snaps="noSnapshots"
                colPath    = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["imageDirectory"]

                if "Apo" in doc["XSDataResultRetrieveDataCollection"]["dataCollection"]["imagePrefix"]:
                    ligsvg="/static/img/apo.png"                
                else:
                    ligsvg=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+sample+"/"+sample+".svg"
                
                writer.writerow([dataset,sample,colPath,acr,run,nIMG,resolution,snaps,ligsvg])
                                                                      
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

def get_results_info(entry):
    usracr="_".join(entry.split("/")[8:11])

    if "dimple" in usracr:
        with open(entry,"r") as inp:
            dimple_log=inp.readlines()
        blist=list()
        for n,line in enumerate(dimple_log):
            if "data_file: " in line:
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
            if line.startswith("blobs: "):            
                blist=[x.replace(" ","")+"]" for x in line.split(":")[-1][2:-2].split("],")]
            if line.startswith("#     RMS: "):
                bonds,angles=line.split()[5],line.split()[9]
            if line.startswith("info: resol. "):
                res=line.split()[2]
                res=str("{0:.2f}".format(float(res)))


        pdbout="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final.pdb"
        event1="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_2mFo-DFc.ccp4"
        ccp4_nat="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_mFo-DFc.ccp4"

    if "fspipeline" in usracr:

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
            blist=list()
            for line in inp.readlines():
                if "INFO:: cluster at xyz = " in line:
                    blob=line.split("(")[-1].split(")")[0].replace("  ","").replace("\n","")
                    blob="["+blob+"]"
                    blist.append(blob)
                

        with open("/".join(entry.split("/")[:-1])+"/mtz2map.log","r") as inp:
            for mline in inp.readlines():
                if "_2mFo-DFc.ccp4" in mline:
                    pdbout  ="/".join(entry.split("/")[:-1])[15:]+"/"+mline.split("/")[-1].replace("\n","").replace("_2mFo-DFc.ccp4",".pdb")
                    event1  ="/".join(entry.split("/")[:-1])[15:]+"/"+mline.split("/")[-1].replace("\n","")
                    ccp4_nat="/".join(entry.split("/")[:-1])[15:]+"/"+mline.split("/")[-1].replace("\n","").replace("_2mFo-DFc.ccp4","_mFo-DFc.ccp4")

def resultSummary():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    
    resultsList=glob.glob(path+"*/fragmax/results/"+acr+"**/*/dimple/dimple.log")+glob.glob(path+"*/fragmax/results/"+acr+"**/*/fspipeline/final**pdb")
    resultsList=sorted(resultsList, key=lambda x: ("Apo" in x, x))
    with open(path+"/fragmax/process/"+acr+"/results.csv","w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["usracr","pdbout","dif_map","nat_map","spg","resolution","r_work","r_free","bonds","angles","a","b","c","alpha","beta","gamma","blist","dataset","pipeline","rhofitscore","ligfitscore","ligblob"])

        
        for entry in sorted(resultsList):
            pdbout   = ""
            usracr   = "_".join(entry.split("/")[8:11])
            pipeline = "_".join(entry.split("/")[9:11])

            if "dimple" in usracr:
                with open(entry,"r") as inp:
                    dimple_log=inp.readlines()
                blist=list()
                for n,line in enumerate(dimple_log):
                    if "data_file: " in line:
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
                    if line.startswith("blobs: "):                     
                        blist=line.split(":")[-1].rstrip()
                    if line.startswith("#     RMS: "):
                        bonds,angles=line.split()[5],line.split()[9]
                    if line.startswith("info: resol. "):
                        resolution=line.split()[2]
                        resolution=str("{0:.2f}".format(float(resolution)))
                pdbout  ="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final.pdb"
                dif_map ="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_2mFo-DFc.ccp4"
                nat_map ="/".join(usrpdbpath.split("/")[3:-1])+"/dimple/final_mFo-DFc.ccp4"

            if "fspipeline" in usracr:

                if os.path.exists("/".join(entry.split("/")[:-1])+"/mtz2map.log") and os.path.exists("/".join(entry.split("/")[:-1])+"/blobs.log"):
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
                            resolution=line.split(":")[-1].replace(" ","").replace("\n","")
                            resolution=str("{0:.2f}".format(float(resolution)))
                        if "CRYST1" in line:
                            a=line[9:15]
                            b=line[18:24]
                            c=line[27:33]
                            alpha=line[34:40].replace(" ","")
                            beta=line[41:47].replace(" ","")
                            gamma=line[48:54].replace(" ","")
                            a=str("{0:.2f}".format(float(a)))
                            b=str("{0:.2f}".format(float(b)))
                            c=str("{0:.2f}".format(float(c)))
                            spg="".join(line.split()[-4:])

                    with open("/".join(entry.split("/")[:-1])+"/blobs.log","r") as inp:    
                        readFile=inp.readlines()
                        blist=list()
                        for line in readFile:
                            if "INFO:: cluster at xyz = " in line:
                                blob=line.split("(")[-1].split(")")[0].replace("  ","").rstrip()
                                blob="["+blob+"]"
                                blist.append(blob)
                                blist=[",".join(blist).replace(" ","")]
                        try:
                            blist="["+blist[0]+"]"
                        except:
                            blist="[]"
                    with open("/".join(entry.split("/")[:-1])+"/mtz2map.log","r") as inp:
                        readFile=inp.readlines()
                        for mline in readFile:
                            if "_2mFo-DFc.ccp4" in mline:                            
                                pdbout  ="/".join(entry.split("/")[3:-1])+"/final.pdb"
                                dif_map ="/".join(entry.split("/")[3:-1])+"/final_2mFo-DFc.ccp4"
                                nat_map ="/".join(entry.split("/")[3:-1])+"/final_mFo-DFc.ccp4"

            rhofitscore="-"
            ligfitscore="-"
            ligblob=[0,0,0]
            if os.path.exists("/data/visitors/"+pdbout) and "Apo" not in pdbout: 
                lig=usracr.split("_")[0].split("-")[-1]            
                ligpng=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+lig+"/"+lig+".svg"            
                ligfitPath=path+"/fragmax/results/"+"_".join(usracr.split("_")[0:2])+"/"+"/".join(pipeline.split("_"))+"/ligfit/"            
                rhofitPath=path+"/fragmax/results/"+"_".join(usracr.split("_")[0:2])+"/"+"/".join(pipeline.split("_"))+"/rhofit/"            

                     
                if os.path.exists(rhofitPath):
                    if os.path.exists(rhofitPath+"Hit_corr.log"):
                        with open(rhofitPath+"Hit_corr.log","r") as inp:
                            rhofitscore=inp.readlines()[0].split()[1]   
                if os.path.exists(ligfitPath):
                    try:
                        ligfitRUNPath=sorted(glob.glob(path+"/fragmax/results/"+"_".join(usracr.split("_")[0:2])+"/"+"/".join(pipeline.split("_"))+"/ligfit/LigandFit*"))[-1]                
                        if glob.glob(path+"/fragmax/results/"+"_".join(usracr.split("_")[0:2])+"/"+"/".join(pipeline.split("_"))+"/ligfit/LigandFit*")!=[]:
                            if glob.glob(ligfitRUNPath+"/LigandFit*.log") !=[]:                        
                                if os.path.exists(ligfitRUNPath+"/LigandFit_summary.dat"):
                                    with open(ligfitRUNPath+"/LigandFit_summary.dat","r") as inp:                    
                                        ligfitscore=inp.readlines()[6].split()[2]

                                ligfitlog=glob.glob(ligfitRUNPath+"/LigandFit*.log")[0]
                                if os.path.exists(ligfitlog):
                                    with open(ligfitlog,"r") as inp:
                                        for line in inp.readlines():
                                            if line.startswith(" lig_xyz"):
                                                ligblob=line.split("lig_xyz ")[-1].replace("\n","")
                    except:
                        pass
            
            ligfit_dataset="_".join(usracr.split("_")[:-2])
            if "fragmax/results" in pdbout:
                writer.writerow([usracr,pdbout,dif_map,nat_map,spg,resolution,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,ligfit_dataset,pipeline,rhofitscore,ligfitscore,ligblob])
        
def run_xdsapp(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()


    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J XDSAPP\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n""" 
    header+= """#SBATCH -o """+path+"""/fragmax/logs/xdsapp_fragmax_%j.out\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/xdsapp_fragmax_%j.err\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDSAPP\n\n"""

    scriptList=list()


    for xml in sorted(glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]

        script="cd "+outdir+"/xdsapp\n"
        script+='xdsapp --cmd --dir='+outdir+'/xdsapp -j 8 -c 5 -i '+h5master+' --delphi=10 --fried=True --range=1\ '+nImg+' \n\n'
        scriptList.append(script)
        os.makedirs(outdir,exist_ok=True)
        os.makedirs(outdir+"/xdsapp",exist_ok=True)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]
    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)
        with open(path+"/fragmax/scripts/xdsapp_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
                
        script=path+"/fragmax/scripts/xdsapp_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_autoproc(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J autoPROC\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n""" 
    header+= """#SBATCH -o """+path+"""/fragmax/logs/autoproc_fragmax_%j.out\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/autoproc_fragmax_%j.err\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 autoPROC\n\n"""

    scriptList=list()


    for xml in natsort.natsorted(glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,exist_ok=True)
        script="cd "+outdir+"\n"
        script+='''process -h5 '''+h5master+''' -noANO autoPROC_XdsKeyword_LIB=\$EBROOTNEGGIA/lib/dectris-neggia.so autoPROC_XdsKeyword_ROTATION_AXIS='0  -1 0' autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_JOBS=8 autoPROC_XdsKeyword_MAXIMUM_NUMBER_OF_PROCESSORS=5 autoPROC_XdsKeyword_DATA_RANGE=1\ '''+nImg+''' autoPROC_XdsKeyword_SPOT_RANGE=1\ '''+nImg+''' -d '''+outdir+'''/autoproc\n\n'''
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]

    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)
        with open(path+"/fragmax/scripts/autoproc_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
        script=path+"/fragmax/scripts/autoproc_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 autoPROC DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_xdsxscale(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J xdsxscale\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""       
    #header+= """#SBATCH --mem=220000\n""" 
    header+= """#SBATCH --mem-per-cpu=2000\n""" 
    header+= """#SBATCH -o """+path+"""/fragmax/logs/xdsxscale_fragmax_%j.out\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/xdsxscale_fragmax_%j.err\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDS\n\n"""

    scriptList=list()

    

    for xml in natsort.natsorted(glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,exist_ok=True)
        os.makedirs(outdir+"/xdsxscale",exist_ok=True)

        
        script="cd "+outdir+"/xdsxscale \n"
        script+="xia2 goniometer.axes=0,1,0  pipeline=3dii failover=true  nproc=40 image="+h5master+":1:"+nImg+" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n\n"
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]


    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)
        with open(path+"/fragmax/scripts/xdsxscale_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
        script=path+"/fragmax/scripts/xdsxscale_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_dials(usedials,usexdsxscale,usexdsapp,useautproc,spacegroup,cellparam,friedel,datarange,rescutoff,cccutoff,isigicutoff,nodes):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    

    header= """#!/bin/bash\n"""
    header+= """#!/bin/bash\n"""
    header+= """#SBATCH -t 99:55:00\n"""
    header+= """#SBATCH -J DIALS\n"""
    header+= """#SBATCH --exclusive\n"""
    header+= """#SBATCH -N1\n"""
    header+= """#SBATCH --cpus-per-task=40\n"""
    #header+= """#SBATCH --mem=220000\n""" 
    header+= """#SBATCH --mem-per-cpu=2000\n""" 

    header+= """#SBATCH -o """+path+"""/fragmax/logs/dials_fragmax_%j.out\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/dials_fragmax_%j.err\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDS DIALS/1.12.3-PReSTO\n\n"""

    scriptList=list()

    

    for xml in natsort.natsorted(glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,exist_ok=True)
        os.makedirs(outdir+"/dials",exist_ok=True)

        
        script="cd "+outdir+"/dials \n"
        script+="xia2 goniometer.axes=0,1,0 pipeline=dials failover=true  nproc=40 image="+h5master+":1:"+nImg+" multiprocessing.mode=serial multiprocessing.njob=1 multiprocessing.nproc=auto\n\n"
        scriptList.append(script)

    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]


    for num,chunk in enumerate(chunkScripts):
        time.sleep(0.2)
        with open(path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
        script=path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def process2results():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    with open(path+"/fragmax/scripts/process2results.py","w") as writeFile:
        writeFile.write('''import os '''
                '''\nimport glob'''
                '''\nimport subprocess'''
                '''\nimport shutil'''
                '''\nimport sys'''
                '''\npath=sys.argv[1]'''
                '''\nacr=sys.argv[2]'''
                '''\nspg=sys.argv[3]'''
                '''\ndatasetList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/")'''
                '''\nfor dataset in datasetList:    '''
                '''\n    for srcmtz in glob.glob(dataset+"autoproc/*mtz"):'''
                '''\n        if "staraniso_alldata" in srcmtz:'''
                '''\n            break'''
                '''\n        elif "aimless_alldata" in srcmtz:'''
                '''\n            break'''
                '''\n        elif "truncate" in srcmtz:'''
                '''\n            break'''
                '''\n    dstmtz=path+"/fragmax/results/"+dataset.split("/")[-2]+"/autoproc/"+dataset.split("/")[-2]+"_autoproc_merged.mtz"'''
                '''\n    shutil.copyfile(srcmtz,dstmtz)'''
                '''\n    cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log"'''
                '''\n    subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    srcmtz=dataset+"dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"'''
                '''\n    if os.path.exists(srcmtz):'''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/dials/"+dataset.split("/")[-2]+"_dials_merged.mtz"'''
                '''\n        if not os.path.exists(dstmtz):            '''
                '''\n            shutil.copyfile(srcmtz,dstmtz)            '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log"'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'''
                '''\n    srcmtz=dataset+"xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"'''
                '''\n    if os.path.exists(srcmtz):'''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsxscale/"+dataset.split("/")[-2]+"_xdsxscale_merged.mtz"'''
                '''\n        if not os.path.exists(dstmtz):            '''
                '''\n            shutil.copyfile(srcmtz,dstmtz)            '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log"'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)    '''
                '''\n    mtzoutList=glob.glob(dataset+"xdsapp/*F.mtz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]    '''
                '''\n    if os.path.exists(srcmtz):                '''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsapp/"+dataset.split("/")[-2]+"_xdsapp_merged.mtz"        '''
                '''\n        if not os.path.exists(dstmtz):'''
                '''\n            shutil.copyfile(srcmtz,dstmtz)        '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log"'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)    '''
                '''\n    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/EDNA_proc/results/*_noanom_aimless.mtz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]    '''
                '''\n    dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/EDNA/"+dataset.split("/")[-2]+"_EDNA_merged.mtz"        '''
                '''\n    if not os.path.exists(dstmtz):'''
                '''\n        shutil.copyfile(srcmtz,dstmtz)        '''
                '''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+dstmtz.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+dstmtz.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log"'''
                '''\n        subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'''
                '''\n    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/fastdp/results/*_noanom_fast_dp.mtz.gz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]        '''
                '''\n    if os.path.exists(srcmtz):                '''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/fastdp/"+dataset.split("/")[-2]+"_fastdp_merged.mtz"        '''
                '''\n        if not os.path.exists(dstmtz):'''
                '''\n            shutil.copyfile(srcmtz,dstmtz)'''
                '''\n            try:'''
                '''\n                subprocess.check_call(['gunzip', dstmtz+".gz"])'''
                '''\n            except:'''
                '''\n                pass'''
                '''\n            a=dataset.split("process/")[0]+"results/"+dataset_run+"/fastdp/"+dataset_run+"_fastdp_unmerged.mtz"'''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+a+" HKLOUT "+a.replace("_unmerged.mtz","_scaled.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/pointless.log ; wait 1 ; echo 'START' | aimless HKLIN "+a.replace("_unmerged.mtz","_scaled.mtz")+" HKLOUT "+a.replace("_unmerged.mtz","_merged.mtz")+" | tee "+'/'.join(a.split('/')[:-1])+"/aimless.log"'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'''
                '''\n    ''')


            
    #Creates HPC script to run dimple on all mtz files provided.
    #PDB _file can be provided in the header of the python script and parse to all 
    #pipelines (Dimple, pipedream, bessy)


    ##This line will make dimple run on unscaled unmerged files. It seems that works 
    ##better sometimes
    #mtzlist=[x.split("_merged")[0]+"_unmerged_unscaled.mtz" for x in mtzlist]


    proc2resOut=""

    #define env for script for dimple
    proc2resOut+= """#!/bin/bash\n"""
    proc2resOut+= """#!/bin/bash\n"""
    proc2resOut+= """#SBATCH -t 99:55:00\n"""
    proc2resOut+= """#SBATCH -J aimless\n"""
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
    
def run_structure_solving(useDIMPLE, useFSP, useBUSTER, userPDB, spacegroup):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()
    process2results() 
    with open(path+'/fragmax/scripts/run_queueREF.py',"w") as writeFile:
        writeFile.write('''\nimport commands, os, sys, glob, time, subprocess'''
            '''\n'''
            '''\nargsfit=sys.argv[1]'''
            '''\npath=sys.argv[2]'''
            '''\n'''
            '''\n# submit the first job'''
            '''\ncmd = "sbatch "+path+"/fragmax/scripts/run_proc2res.sh"'''
            '''\nstatus, jobnum1 = commands.getstatusoutput(cmd)'''
            '''\njobnum1=jobnum1.split("batch job ")[-1]'''
            '''\nPDB=path+"/fragmax/process/"+sys.argv[3]+".pdb"'''
            '''\n'''
            '''\ndef scrsplit(a, n):'''
            '''\n    k, m = divmod(len(a), n)'''
            '''\n    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))'''
            '''\nif "dimple" in argsfit:'''
            '''\n    # submit the second job to be dependent on the first'''
            '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/run_dimple.sh" % (jobnum1,path)'''
            '''\n    '''
            '''\n    status,jobnum2 = commands.getstatusoutput(cmd)'''
            '''\n    '''
            '''\nif "fspipeline" in argsfit:'''
            '''\n    # submit the third job (a swarm) to be dependent on the second'''
            '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/run_fspipeline.sh" % (jobnum1,path)    '''
            '''\n    status,jobnum3 = commands.getstatusoutput(cmd)'''
            '''\n    '''
            '''\n'''
            '''\nif "buster" in argsfit:'''
            '''\n    # submit the third job (a swarm) to be dependent on the second'''
            '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/run_buster.sh" % (jobnum1,path)    '''
            '''\n    status,jobnum3 = commands.getstatusoutput(cmd)'''
            '''\nif "buster" in argsfit:'''
            '''\n    # submit the third job (a swarm) to be dependent on the second'''
            '''\n    '''
            '''\n    '''
            '''\n'''
            '''\n    header= """#!/bin/bash\n"""'''
            '''\n    header+= """#!/bin/bash\n"""'''
            '''\n    header+= """#SBATCH -t 99:55:00\n"""'''
            '''\n    header+= """#SBATCH -J BUSTER\n"""'''
            '''\n    header+= """#SBATCH --exclusive\n"""'''
            '''\n    header+= """#SBATCH -N1\n"""'''
            '''\n    header+= """#SBATCH --cpus-per-task=40\n"""'''
            '''\n    header+= """#SBATCH -o """+path+"""/fragmax/logs/buster_fragmax_%j.out\n"""'''
            '''\n    header+= """#SBATCH -e """+path+"""/fragmax/logs/buster_fragmax_%j.err\n"""    '''
            '''\n    header+= """module purge\n"""'''
            '''\n    header+= """module load autoPROC BUSTER\n\n"""'''

            '''\n    inputData=list()'''
            '''\n    for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):'''
            '''\n        mtzList=glob.glob(proc+"*mtz")'''
            '''\n        if mtzList:'''
            '''\n            inputData.append(sorted(glob.glob(proc+"*mtz"))[0])'''
            '''\n    scriptList=['echo "truncate yes \labout F=FP SIGF=SIGFP" | truncate hklin '+mtzin+' hklout '+mtzin.replace("merged","truncate")+" ; refine -p "+PDB+" -m "+mtzin.replace("merged","truncate")+" -TLS -nthreads 40 -d "+"/".join(mtzin.split("/")[:-1])+"/buster\n\n" for mtzin in inputData]'''
            '''\n    chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,int(nodes)) )]'''

            '''\n    for num,chunk in enumerate(chunkScripts):'''
            '''\n        time.sleep(0.2)'''
            '''\n        with open(path+"/fragmax/scripts/buster_part"+str(num)+".sh", "w") as outfile:'''
            '''\n            outfile.write(chunk)        '''
            '''\n        cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/buster_part%s.sh" % (jobnum1,path,str(num))'''
            '''\n        status,jobnum3 = commands.getstatusoutput(cmd)''')


    def dimple_hpc(PDB):
        #Creates HPC script to run dimple on all mtz files provided.
        #PDB _file can be provided in the header of the python script and parse to all 
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
        fspOut+=" --exclude='unscaled unmerged scaled final dimple ligfit rhofit'"
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
            pyOut.write('softwares = ["autoproc","EDNA","dials","fastdp","xdsapp","xdsxscale"]\n')
            pyOut.write('for _file,fpath in zip(success_list,path_list):\n')
            pyOut.write('    outdir=path+"/fragmax/results/"\n')
            pyOut.write('    for sw in softwares:\n')
            pyOut.write('        if sw in _file:\n')
            pyOut.write('            outp=outdir+_file.split("_"+sw)[0]+"/"+sw\n')
            pyOut.write('            copy_string="rsync --ignore-existing -raz "+fpath+"/* "+outp+"/fspipeline"\n')
            pyOut.write('            subprocess.call(copy_string, shell=True)\n')

    

    dimple_hpc(userPDB)
    fspipeline_hpc(userPDB)

    #slurmqueue="RES=$(sbatch "+path+"/fragmax/scripts/run_proc2res.sh)  "
    # if useBUSTER:
    #     script=path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh"
    #     command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    #     subprocess.call(command,shell=True)
    #if useFSP:
    #    slurmqueue+=" && sbatch --dependency=afterok:${RES##* } "+path+"/fragmax/scripts/run_fspipeline.sh "
    #if useDIMPLE:
    #    slurmqueue+=" && sbatch --dependency=afterok:${RES##* } "+path+"/fragmax/scripts/run_dimple.sh " 
    #
    #
    #command ='echo "module purge | module load CCP4 Phenix | '+slurmqueue+' " | ssh -F ~/.ssh/ clu0-fe-1'
    #subprocess.call(command,shell=True)


    argsfit="none"
    if useFSP:
        argsfit="fspipeline"
    if useDIMPLE:
        argsfit+="dimple"
    if useBUSTER:
        argsfit+="buster"
    nodes=5
    command ='echo "python '+path+'/fragmax/scripts/run_queueREF.py '+argsfit+' '+path+' '+userPDB+' '+acr+' '+nodes+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(command,shell=True)
    

def ligandToSVG():
    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

    with open(path+"/fragmax/scripts/autoligand.py","w") as writeFile:
        writeFile.write('''import multiprocessing\n'''
                '''import time\n'''
                '''import subprocess\n'''
                '''import sys\n'''
                '''import glob\n'''
                '''import os\n'''
                '''path=sys.argv[1]\n'''
                '''fraglib=sys.argv[2]\n'''
                '''acr=sys.argv[3]\n'''
                '''fitmethod=sys.argv[4]\n'''
                '''pdbList=[x for x in glob.glob(path+"/fragmax/results/"+acr+"*/*/*/final.pdb") if "Apo" not in x]\n'''
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
                    
    


    
    script=path+"/fragmax/scripts/autoligand.sh"
    if "True" in useRhoFit:
        with open(path+"/fragmax/scripts/autoligand.sh","w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                    '''#!/bin/bash\n'''
                    '''#SBATCH -t 99:55:00\n'''
                    '''#SBATCH -J autoRhofit\n'''
                    '''#SBATCH --exclusive\n'''
                    '''#SBATCH -N1\n'''
                    '''#SBATCH --cpus-per-task=48\n'''
                    '''#SBATCH -o '''+path+'''/fragmax/logs/auto_rhofit_%j.out\n'''
                    '''#SBATCH -e '''+path+'''/fragmax/logs/auto_rhofit_%j.err\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+path+'''/fragmax/scripts/autoligand.py '''+path+''' '''+fraglib+''' '''+acr+''' rhofit\n''')
        command ='echo "module purge | module load BUSTER CCP4 | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
    if "True" in useLigFit:
        with open(path+"/fragmax/scripts/autoligand.sh","w") as writeFile:
            writeFile.write('''#!/bin/bash\n'''
                    '''#!/bin/bash\n'''
                    '''#SBATCH -t 3:00:00\n'''
                    '''#SBATCH -J autoLigfit\n'''
                    '''#SBATCH --exclusive\n'''
                    '''#SBATCH -N1\n'''
                    '''#SBATCH --cpus-per-task=48\n'''
                    '''#SBATCH -o '''+path+'''/fragmax/logs/auto_ligfit_%j.out\n'''
                    '''#SBATCH -e '''+path+'''/fragmax/logs/auto_ligfit_%j.err\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+path+'''/fragmax/scripts/autoligand.py '''+path+''' '''+fraglib+''' '''+acr+''' ligfit\n''')
        command ='echo "module purge | module load CCP4 Phenix | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)
    
def merge_project():
    srcprj="20190401"
    dstprj="20190330"
    srcacr="/mxn/groups/ispybstorage/pyarch/visitors/proposal/shift/raw/srcacr/"
    dstacr="/mxn/groups/ispybstorage/pyarch/visitors/proposal/shift/raw/dstacr/"
    ### Symlink raw folder

    ### Symlink process folder
    
    ### Symlink snapshots

def get_project_status():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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

        with open(path+"/fragmax/process/"+acr+"/dpstatus.csv","w") as outp:
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

        with open(path+"/fragmax/process/"+acr+"/rfstatus.csv","w") as outp:
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

        with open(path+"/fragmax/process/"+acr+"/lgstatus.csv","w") as outp:
            for key,value in dataLigStatusDict.items():
                outp.write(key+":"+value+"\n")
          
def scrsplit(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

def get_project_status_initial():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib=project_definitions()

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
        if os.path.exists(autosample+"EDNA/results/"):
            if os.path.exists(autosample+"EDNA/results/ep_"+autosample.split("/")[-2]+"_noanom.mtz"):
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
            
        with open(path+"/fragmax/process/"+acr+"/dpstatus.csv","w") as outp:
            for key,value in dataProcStatusDict.items():
                outp.write(key+":"+value+"\n")
###############################

#################################
def split_b(target,ini,end):
    return target.split(ini)[-1].split(end)[0]

def sym2spg(sym):
    spgDict={"1": "P 1","2":" P -1","3":" P 2    ","4":"P 21"    ,"5":"C 2",
            "6": "P m","7":" P c    ","8":" C m    ","9":"C c"    ,"10":"P 2/m",
            "11": "P 21/m","12":" C 2/m","13":" P 2/c","14":"P 21/c","15":"C 2/c",
            "16": "P 2 2 2","17":" P 2 2 21    ","18":" P 21 21 2 ","19":"P 21 21 21" ,"20":"C 2 2 21",
            "21": "C 2 2 2","22":" F 2 2 2","23":" I 2 2 2","24":"I 21 21 21" ,"25":"P m m 2",
            "26": "P m c 21 ","27":" P c c 2","28":" P m a 2","29":"P c a 21" ,"30":"P n c 2",
            "31": "P m n 21 ","32":" P b a 2","33":" P n a 21    ","34":"P n n 2","35":"C m m 2",
            "36": "C m c 21 ","37":" C c c 2","38":" A m m 2","39":"A b m 2","40":"A m a 2",
            "41": "A b a 2","42":" F m m 2","43":" F d d 2","44":"I m m 2","45":"I b a 2",
            "46": "I m a 2","47":" P m m m","48":" P n n n","49":"P c c m","50":"P b a n",
            "51": "P m m a","52":" P n n a","53":" P m n a","54":"P c c a","55":"P b a m",
            "56": "P c c n","57":" P b c m","58":" P n n m","59":"P m m n","60":"P b c n",
            "61": "P b c a","62":" P n m a","63":" C m c m","64":"C m c a","65":"C m m m",
            "66": "C c c m","67":" C m m a","68":" C c c a","69":"F m m m","70":"F d d d",
            "71": "I m m m","72":" I b a m","73":" I b c a","74":"I m m a","75":"P 4",
            "76": "P 41","77":" P 42","78":" P 43","79":"I 4"    ,"80":"I 41",
            "81": "P -4","82":" I -4","83":" P 4/m","84":"P 42/m","85":"P 4/n",
            "86": "P 42/n","87":" I 4/m","88":" I 41/a","89":"P 4 2 2","90":"P 4 21 2",
            "91": "P 41 2 2 ","92":" P 41 21 2 ","93":" P 42 2 2 ","94":"P 42 21 2" ,"95":"P 43 2 2",
            "96": "P 43 21 2 ","97":" I 4 2 2","98":" I 41 2 2 ","99":"P 4 m m","100":"P 4 b m",
            "101": "P 42 c m ","102":" P 42 n m ","103":" P 4 c c","104":"P 4 n c","105":"P 42 m c",
            "106": "P 42 b c ","107":" I 4 m m","108":" I 4 c m","109":"I 41 m d" ,"110":"I 41 c d",
            "111": "P -4 2 m ","112":" P -4 2 c ","113":" P -4 21 m ","114":"P -4 21 c" ,"115":"P -4 m 2",
            "116": "P -4 c 2 ","117":" P -4 b 2 ","118":" P -4 n 2 ","119":"I -4 m 2" ,"120":"I -4 c 2",
            "121": "I -4 2 m ","122":" I -4 2 d ","123":" P 4/m m m ","124":"P 4/m c c" ,"125":"P 4/n b m",
            "126": "P 4/n n c ","127":" P 4/m b m ","128":" P 4/m n c ","129":"P 4/n m m" ,"130":"P 4/n c c",
            "131": "P 42/m m c ","132":" P 42/m c m ","133":" P 42/n b c ","134":"P 42/n n m" ,"135":"P 42/m b c",
            "136": "P 42/m n m ","137":" P 42/n m c ","138":" P 42/n c m ","139":"I 4/m m m" ,"140":"I 4/m c m",
            "141": "I 41/a m d ","142":" I 41/a c d ","143":" P 3    ","144":"P 31","145":"P 32",
            "146": "R 3    ","147":" P -3","148":" R -3","149":"P 3 1 2","150":"P 3 2 1",
            "151": "P 31 1 2 ","152":" P 31 2 1 ","153":" P 32 1 2 ","154":"P 32 2 1" ,"155":"R 3 2",
            "156": "P 3 m 1","157":" P 3 1 m","158":" P 3 c 1","159":"P 3 1 c"    ,"160":"R 3 m",
            "161": "R 3 c","162":" P -3 1 m ","163":" P -3 1 c ","164":"P -3 m 1" ,"165":"P -3 c 1",
            "166": "R -3 m","167":" R -3 c","168":" P 6    ","169":"P 61","170":"P 65",
            "171": "P 62","172":" P 64","173":" P 63","174":"P -6","175":"P 6/m",
            "176": "P 63/m","177":" P 6 2 2","178":" P 61 2 2 ","179":"P 65 2 2" ,"180":"P 62 2 2",
            "181": "P 64 2 2 ","182":" P 63 2 2 ","183":" P 6 m m","184":"P 6 c c"    ,"185":"P 63 c m",
            "186": "P 63 m c ","187":" P -6 m 2 ","188":" P -6 c 2 ","189":"P -6 2 m" ,"190":"P -6 2 c",
            "191": "P 6/m m m ","192":" P 6/m c c ","193":" P 63/m c m ","194":"P 63/m m c" ,"195":"P 2 3",
            "196": "F 2 3","197":" I 2 3","198":" P 21 3","199":"I 21 3","200":"P m -3",
            "201": "P n -3","202":" F m -3","203":" F d -3","204":"I m -3","205":"P a -3",
            "206": "I a -3","207":" P 4 3 2","208":" P 42 3 2 ","209":"F 4 3 2","210":"F 41 3 2",
            "211": "I 4 3 2","212":" P 43 3 2 ","213":" P 41 3 2 ","214":"I 41 3 2" ,"215":"P -4 3 m",
            "216": "F -4 3 m ","217":" I -4 3 m ","218":" P -4 3 n ","219":"F -4 3 c" ,"220":"I -4 3 d",
            "221": "P m -3 m ","222":" P n -3 n ","223":" P m -3 n ","224":"P n -3 m" ,"225":"F m -3 m",
            "226": "F m -3 c ","227":" F d -3 m ","228":" F d -3 c ","229":"I m -3 m" ,"230":"I a -3 d"}
    
    return spgDict[sym]