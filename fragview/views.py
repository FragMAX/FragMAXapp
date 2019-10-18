from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from .models import Project
from .forms import ProjectForm
from .proposals import get_proposals
from difflib import SequenceMatcher

import glob
import os
import random
import natsort
import shutil
import pyfastcopy
import csv
import subprocess
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
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from random import randint

################################
#Changing this parameters for different projects based on user credentials



setfile="/mxn/home/guslim/Projects/webapp/static/projectSettings/.settings"

class ThreadWithReturnValue(threading.Thread):
        def __init__(self, group=None, target=None, name=None,
                    args=(), kwargs={}, Verbose=None):
            threading.Thread.__init__(self, group, target, name, args, kwargs)
            self._return = None
        def run(self):
            print(type(self._target))
            if self._target is not None:
                self._return = self._target(*self._args,
                                                    **self._kwargs)
        def join(self, *args):
            threading.Thread.join(self, *args)
            return self._return


def project_definitions():
    proposal = ""
    shift    = ""
    acronym  = ""
    proposal_type = ""
    with open(setfile,"r") as inp:
        prjset=inp.readlines()[0]

    proposal      = prjset.split(";")[1].split(":")[-1]
    shift         = prjset.split(";")[2].split(":")[-1]    
    acronym       = prjset.split(";")[3].split(":")[-1]    
    proposal_type = prjset.split(";")[4].split(":")[-1]
    fraglib       = prjset.split(";")[5].split(":")[-1].replace("\n","") 
    shiftList     = prjset.split(";")[6].split(":")[-1].split(",")

    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
    static_datapath="/static/biomax/"+proposal+"/"+shift
    #fraglib="F2XEntry"
    #fraglib="JBS"
    os.makedirs(path+"/fragmax/process/",mode=0o760, exist_ok=True)
    os.makedirs(path+"/fragmax/scripts/",mode=0o760, exist_ok=True)
    os.makedirs(path+"/fragmax/results/",mode=0o760, exist_ok=True)
    os.makedirs(path+"/fragmax/logs/",mode=0o760, exist_ok=True)

    

    
    return proposal, shift, acronym, proposal_type, path, subpath, static_datapath,fraglib, shiftList


proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

if len(proposal)<7 or len(shift)<7 or len(acr)<1 or len(proposal_type)<5:

    acr="ProteinaseK"
    proposal="20180479"
    shift="20190323"
    proposal_type="visitors"
    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
    static_datapath="/static/biomax/"+proposal+"/"+shift
    shiftList=["20190323"]

################################

def index(request):
    return render(request, "fragview/index.html")

def results_download(request):
    return render(request, "fragview/results_download.html")

def error_page(request):
    return render(request, "fragview/error.html")

def data_analysis(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    models=[x.split("/")[-1].split(".pdb")[0] for x in glob.glob(path+"/fragmax/models/*.pdb")]
    datasets=sorted([x.split("/")[-1].replace("_master.h5","") for x in glob.glob(path+"/raw/"+acr+"/*/*master.h5")],key=lambda x: ("Apo" in x, x))
    return render(request, "fragview/data_analysis.html",{"acronym":acr,"models":models,"datasets":datasets})

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


def projects(request):
    """
    projects list page, aka 'manage projects' page
    """
    return render(request, "fragview/projects.html")


def project(request, id):
    """
    GET requests show the 'Edit Project' page
    POST requests will update or delete the project
    """
    proj = get_object_or_404(Project, pk=id)
    form = ProjectForm(request.POST or None, instance=proj)

    if request.method == "POST":
        action = request.POST["action"]
        if action == "modify":
            if form.is_valid():
                form.save()
                return redirect("/projects/")
        elif action == "delete":
            proj.delete()
            return redirect("/projects/")
        else:
            return HttpResponseBadRequest(f"unexpected action '{action}'")

    return render(
        request,
        "fragview/project.html",
        {"form": form, "project_id": proj.id})


def project_new(request):
    """
    GET requests show the 'Create new Project' page
    POST requests will try to create a new project
    """
    if request.method == "GET":
        return render(request, "fragview/project.html")

    form = ProjectForm(request.POST)
    if not form.is_valid():
        return render(request, "fragview/project.html", {"form": form})

    form.save()

    return redirect("/projects/")


def project_set_current(request, id):
    proj = Project.get_project(get_proposals(request), id)
    if proj is None:
        return HttpResponseNotFound()

    request.user.set_current_project(proj)

    # go back to original URL, or site root if we
    # don't know referring page
    return redirect(request.META.get("HTTP_REFERER", "/"))


#TODO: remove this view
def load_project_summary(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    number_known_apo=len(glob.glob(path+"/raw/"+acr+"/*Apo*"))
    number_datasets=len(glob.glob(path+"/raw/"+acr+"/*"))
    totalapo=0
    totaldata=0
    for s in shiftList:
        p="/data/visitors/biomax/"+proposal+"/"+s
        totalapo+=len(glob.glob(p+"/raw/"+acr+"/*Apo*"))
        totaldata+=len(glob.glob(p+"/raw/"+acr+"/*"))
    if "JBS" in fraglib:
        libname="JBS Xtal Screen"
    elif "F2XEntry" in fraglib:
        libname="F2X Entry Screen"
    else:
        libname="Custom library"
    months={"01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun","07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"}
    natdate=shift[0:4]+" "+months[shift[4:6]]+" "+shift[6:8]
    
    return render(request,'fragview/project_summary.html', {
        'acronym':acr,
        "proposal":proposal,
        "shiftList":"<br>".join(shiftList),
        "proposal_type":proposal_type,
        "shift":shift,
        "known_apo":number_known_apo,
        "num_dataset":number_datasets,
        "totalapo":totalapo,
        "totaldata":totaldata,
        "fraglib":libname,
        "exp_date":natdate})
    
def dataset_info(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    dataset=str(request.GET.get('proteinPrefix'))     
    prefix=dataset.split(";")[0]
    images=dataset.split(";")[1]
    run=dataset.split(";")[2]

    images=str(int(images)/2)
    #xmlfile=path+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+".xml"
    xmlfile=""
    for s in shiftList:
        p="/data/visitors/biomax/"+proposal+"/"+s
        if os.path.exists(p+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+".xml"):
            xmlfile=p+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+".xml"
            curp=p

    datainfo=retrieveParameters(xmlfile)    

    energy=format(12.4/float(datainfo["wavelength"]),".2f")
    totalExposure=format(float(datainfo["exposureTime"])*float(datainfo["numberOfImages"]),".2f")
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

    diffraction1=curp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_1.jpeg"
    diffraction1=diffraction1.replace("/data/visitors/","/static/")
    if not os.path.exists(diffraction1):    
        h5data=curp+"/raw/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_data_0000"
        cmd="adxv -sa "+h5data+"01.h5 "+diffraction1.replace("/static/","/data/visitors/")
        subprocess.call(cmd,shell=True)
    
    diffraction2=curp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_2.jpeg"
    diffraction2=diffraction2.replace("/data/visitors/","/static/")
    if not os.path.exists(diffraction2):    
        half=int(float(images)/200)
        if half<10:
            half="0"+str(half)
        h5data=curp+"/raw/"+acr+"/"+prefix+"/"+prefix+"_"+run+"_data_0000"
        cmd="adxv -sa "+h5data+half+".h5 "+diffraction2.replace("/static/","/data/visitors/")
        subprocess.call(cmd,shell=True)

    #getreports
    scurp=curp.replace("/data/visitors/","/static/")
    xdsappreport    = scurp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/xdsapp/results_"+prefix+"_"+run+"_data.txt"
    dialsreport     = scurp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/dials/xia2.html"  
    xdsreport       = scurp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/xdsxscale/xia2.html"
    autoprocreport  = scurp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/autoproc/summary.html"
    ednareport      = scurp+"/process/"+acr+"/"+prefix+"/xds_"+prefix+"_"+run+"_1/EDNA_proc/results/ep_"+prefix+"_"+run+"_phenix_xtriage_noanom.log"
    fastdpreport    = scurp+"/process/"+acr+"/"+prefix+"/xds_"+prefix+"_"+run+"_1/fastdp/results/ap_"+prefix+"_run"+run+"_noanom_fast_dp.log"

    xdsappOK="no"
    dialsOK="no"
    xdsOK="no"
    autoprocOK="no"
    ednaOK="no"
    fastdpOK="no"
    if os.path.exists(curp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/xdsapp/results_"+prefix+"_"+run+"_data.txt"):
        xdsappOK="ready"
    if os.path.exists(curp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/dials/xia2.html"  ):
        dialsOK="ready"
    if os.path.exists(curp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/xdsxscale/xia2.html"):
        xdsOK="ready"
    if os.path.exists(curp+"/fragmax/process/"+acr+"/"+prefix+"/"+prefix+"_"+run+"/autoproc/summary.html"):
        autoprocOK="ready"
    if os.path.exists(curp+"/process/"+acr+"/"+prefix+"/xds_"+prefix+"_"+run+"_1/EDNA_proc/results/ep_"+prefix+"_"+run+"_phenix_xtriage_noanom.log"):
        ednaOK="ready"
    if os.path.exists(curp+"/process/"+acr+"/"+prefix+"/xds_"+prefix+"_"+run+"_1/fastdp/results/ap_"+prefix+"_run"+run+"_noanom_fast_dp.log"):
        fastdpOK="ready"

    

    if "Apo" in prefix:
        soakTime="Soaking not performed"
        fragConc="-"
        solventConc="-"
    if os.path.exists(path+"/fragmax/process/"+acr+"/results.csv"):
        with open(path+"/fragmax/process/"+acr+"/results.csv","r") as readFile:
            reader = csv.reader(readFile)
            lines = [line for line in list(reader)[1:] if prefix+"_"+run in line[0]]
    else:
        lines=[]
    return render(request,'fragview/dataset_info.html', {
        "csvfile":lines,
        "proposal":proposal,
        "shift":curp.split("/")[-1],
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
        "fraglib":fraglib,
        "xdsappreport":xdsappreport,
        "dialsreport":dialsreport,
        "xdsreport":xdsreport,
        "autoprocreport":autoprocreport,
        "ednareport":ednareport,
        "fastdpreport":fastdpreport,
        "xdsappOK":xdsappOK,
        "dialsOK":dialsOK,
        "xdsOK":xdsOK,
        "autoprocOK":autoprocOK,
        "ednaOK":ednaOK,
        "fastdpOK":fastdpOK,
        })
  

def datasets(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    resyncAction=str(request.GET.get("resyncdsButton"))
    resyncStatus=str(request.GET.get("resyncstButton"))
    datacollectionSummary(acr,path) 

    if "resyncDataset" in resyncAction:        
        datacollectionSummary(acr,path)
    
    if "resyncStatus" in resyncStatus:
        os.remove(path+"/fragmax/process/"+acr+"/datacollections.csv")
        get_project_status()
        datacollectionSummary(acr,path)
        resultSummary()
    
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


    if not os.path.exists(path+"/fragmax/process/"+acr+"/allstatus.csv"):
        get_project_status()

    ##Proc status
    if os.path.exists(path+"/fragmax/process/"+acr+"/allstatus.csv"):
        with open(path+"/fragmax/process/"+acr+"/allstatus.csv","r") as csvFile:
            reader = csv.reader(csvFile)
            lines = list(reader)[1:]
        for i,j in zip(prf_list,run_list):
            dictEntry=i+"_"+j
            status=[line for line in lines if line[0]==dictEntry]
            if status!=[]:
                
                da="<td>"
                if status[0][1]=="full":
                    da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> autoPROC</font></p>""")
                elif status[0][1]=="partial":
                    da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> autoPROC</font></p>""")
                else:
                    da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> autoPROC</font></p>""")

            
                if status[0][2]=="full":
                    da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> DIALS</font></p>""")
                elif status[0][2]=="partial":
                    da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> DIALS</font></p>""")
                else:
                    da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> DIALS</font></p>""")

                if status[0][3]=="full":
                    da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> EDNA_proc</font></p>""")
                elif status[0][3]=="partial":
                    da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> EDNA_proc</font></p>""")
                else:
                    da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> EDNA_proc</font></p>""")


                if status[0][4]=="full" :
                    da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Fastdp</font></p>""")
                elif status[0][4]=="partial":
                    da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> Fastdp</font></p>""")
                else:
                    da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Fastdp</font></p>""")

                if status[0][5]=="full":
                    da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XDSAPP</font></p>""")
                elif status[0][5]=="partial":
                    da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> XDSAPP</font></p>""")
                else:
                    da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDSAPP</font></p>""")


                if status[0][6]=="full":
                    da+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> XDS/XSCALE</font></p>""")
                elif status[0][6]=="partial":
                    da+=("""<p align="left"><font size="2" color="yellow">&#9679;</font><font size="2"> XDS/XSCALE</font></p>""")
                else:
                    da+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDS/XSCALE</font></p></td>""")
                
                
                dpentry.append(da)
                re="<td>"  
                if status[0][9]=="full":
                    re+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> BUSTER</font></p>""")
                else:
                    re+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> BUSTER</font></p>""")
                
                
                if status[0][7]=="full":
                    re+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> Dimple</font></p>""")
                else:
                    re+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Dimple</font></p>""")


                if status[0][8]=="full":
                    re+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> FSpipeline</font></p></td>""")
                else:
                    re+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> FSpipeline</font></p></td>""")
                rfentry.append(re)
            

                lge="<td>"  
                if status[0][10]=="full":
                    lge+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> LigFit</font></p>""")
                else:
                    lge+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> LigFit</font></p>""")
                
                if status[0][11]=="full":
                    lge+=("""<p align="left"><font size="2" color="green">&#9679;</font><font size="2"> RhoFit</font></p></td>""")
                else:
                    lge+=("""<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p></td>""")
                lgentry.append(lge)
            
    else:
        for i in prf_list:
            dpentry.append("""<td>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> autoPROC</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/DIALS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XIA2/XDS</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> XDSAPP</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> fastdp</font></p>
                    <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> EDNA_proc</font></p>    
                </td>""")
            rfentry.append("""<td>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> BUSTER</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Dimple</font></p>
                        <p align="left"><font size="2" color="red">&#9675;</font><font size="2"> FSpipeline</font></p>    
                    </td>""")
        for i,j in zip(prf_list,run_list):
            lge="<td>"
            lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> RhoFit</font></p>'
            lge+='<p align="left"><font size="2" color="red">&#9675;</font><font size="2"> Phenix LigFit</font></p></td>'
            lgentry.append(lge)
    ##Ref status
    
        
    
    
    results = zip(img_list,prf_list,res_list,path_list,snap_list,acr_list,png_list,run_list,smp_list,dpentry,rfentry,lgentry)
    return render(request,'fragview/datasets.html', {'files': results})
    # except:
    #     return render_to_response('fragview/datasets_notready.html')    
    
def results(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    resync=str(request.GET.get("resync"))
    if "resyncresults" in resync:
        resultSummary()
    if not os.path.exists(path+"/fragmax/process/"+acr+"/results.csv"):
        resultSummary()
    try:
        with open(path+"/fragmax/process/"+acr+"/results.csv","r") as readFile:
            reader = csv.reader(readFile)
            lines = list(reader)[1:]
        return render(request, "fragview/results.html",{"csvfile":lines,"proposal":proposal,"shift":shift,"acr":acr})    
    except:
        return render_to_response('fragview/results_notready.html')

def results_density(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    value=str(request.GET.get('structure'))     
    with open(path+"/fragmax/process/"+acr+"/results.csv","r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]
    result_info=list(filter(lambda x:x[0]==value,lines))[0]
    usracr,pdbout,nat_map,dif_map,spg,resolution,isa,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,ligfit_dataset,pipeline,rhofitscore,ligfitscore,ligblob=result_info        
    
    if os.path.exists(path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final.pdb"):
        if not os.path.exists(path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final.mtz"):
            if glob.glob(path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final*.mtz")!=[]:
                mtzf=glob.glob(path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final*.mtz")[0]
                mtzfd=path+"/fragmax/results/"+"_".join(usracr.split("_")[:-2])+"/"+"/".join(pipeline.split("_"))+"/final.mtz"
                shutil.copyfile(mtzf,mtzfd)

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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    
    return render(request, "fragview/testpage.html",{"files":"results"})    
    
def ugly(request):
    return render(request,'fragview/ugly.html')

def reciprocal_lattice(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    dataset=str(request.GET.get('dataHeader')) 
    flatlist=[y for x in [glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/process/"+acr+"/*/"+dataset+"/dials/DEFAULT/NATIVE/*/index/2_SWEEP*") for s in shiftList] for y in x]
    state="new"
    if flatlist != []:
        rlpdir="/".join(flatlist[0].split("/")[:-1])
        if os.path.exists(rlpdir+"/rlp.json"):
            rlpdir="/".join(flatlist[0].split("/")[:-1])
            rlp=rlpdir+"/rlp.json"
            state="none"
        else:
            
            cmd='echo "module load DIALS;cd '+rlpdir+'; dials.export 2_SWEEP1_datablock.json 2_SWEEP1_strong.pickle format=json" | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(cmd,shell=True)
            rlp=rlpdir+"/rlp.json"
    else:
        rlp="none2"
    if dataset in rlp:
        timer=0
        while os.path.exists(rlp)==False: 
            if timer==20:
                break
            time.sleep(1)
            timer+=1
    rlp=rlp.replace("/data/visitors/","/static/")
    return render(request,'fragview/reciprocal_lattice.html', {'dataset': dataset, "rlp":rlp,"state":state})
    

def compare_poses(request):   
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
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
    #NOT USED ANYMORE
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()   

    datasetPathList=glob.glob(path+"/raw/"+acr+"/*/*master.h5")
    datasetPathList=natsort.natsorted(datasetPathList)
    datasetNameList= [i.split("/")[-1].replace("_master.h5","") for i in datasetPathList if "ref-" not in i] 
    datasetList=zip(datasetPathList,datasetNameList)
    return render(request, "fragview/pipedream.html",{"data":datasetList})

def pipedream_results(request):

    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()   

    resync=str(request.GET.get("resync"))
    if "resyncresults" in resync:
        get_pipedream_results()
    if not os.path.exists(path+"/fragmax/process/"+acr+"/pipedream.csv"):
            get_pipedream_results()
    if os.path.exists(path+"/fragmax/process/"+acr+"/pipedream.csv"):
        with open(path+"/fragmax/process/"+acr+"/pipedream.csv","r") as readFile:
            reader = csv.reader(readFile)
            lines = list(reader)[1:]
        return render(request,'fragview/pipedream_results.html', {'lines': lines})
    else:
        return render(request,'fragview/pipedream_results.html')

def submit_pipedream(request):
    def get_user_pdb_path():
        if len(b_userPDBcode.replace("b_userPDBcode:", "")) == 4:
            userPDB = b_userPDBcode.replace("b_userPDBcode:", "")
            userPDBpath = path + "/fragmax/models/" + userPDB + ".pdb"

            ## Download and prepare PDB _file - remove waters and HETATM
            with open(userPDBpath, "w") as pdb:
                pdb.write(pypdb.get_pdb_file(userPDB, filetype='pdb'))

            preparePDB = "pdb_selchain -" + pdbchains + " " + userPDBpath + " | pdb_delhetatm | pdb_tidy > " + userPDBpath.replace(
                ".pdb", "_tidy.pdb")
            subprocess.call(preparePDB, shell=True)
        else:
            if len(b_userPDBcode.split("b_userPDBcode:")) == 2:
                if path in b_userPDBcode.split("b_userPDBcode:")[1]:
                    userPDBpath = b_userPDBcode.split("b_userPDBcode:")[1]
                else:
                    userPDBpath = path + "/fragmax/models/" + b_userPDBcode.split("b_userPDBcode:")[1]

        return userPDBpath

    #Function definitions
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    ppdCMD=str(request.GET.get("ppdform"))
    empty,input_data, ap_spacegroup, ap_cellparam,ap_staraniso,ap_xbeamcent,ap_ybeamcent,ap_datarange,ap_rescutoff,ap_highreslim,ap_maxrpim,ap_mincomplet,ap_cchalfcut,ap_isigicut,ap_custompar,b_userPDBfile,b_userPDBcode,b_userMTZfile,b_refinemode,b_MRthreshold,b_chainsgroup,b_bruteforcetf,b_reslimits,b_angularrf,b_sideaiderefit,b_sideaiderebuild,b_pepflip,b_custompar,rho_ligandsmiles,rho_ligandcode,rho_ligandfromname,rho_copiestosearch,rho_keepH,rho_allclusters,rho_xclusters,rho_postrefine,rho_occuprefine,rho_fittingproc,rho_scanchirals,rho_custompar,extras = ppdCMD.split(";;")

    nodes=10
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

        os.makedirs("/".join(ppdoutdir.split("/")[:-1]),mode=0o760, exist_ok=True)
        if os.path.exists(ppdoutdir):
            shutil.rmtree(ppdoutdir)
        #     try:
        #         int(ppdoutdir[-1])
        #     except ValueError:
        #         run="1"
        #     else:
        #         run=str(int(ppdoutdir[-1])+1)
            

        #     ppdoutdir=ppdoutdir+"_run"+run

        userPDBpath = get_user_pdb_path()

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
                    ncluster="1"
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
        singlePipedreamOut+= """#SBATCH -o """+path+"""/fragmax/logs/pipedream_"""+ligand+"""_%j_out.txt\n"""
        singlePipedreamOut+= """#SBATCH -e """+path+"""/fragmax/logs/pipedream_"""+ligand+"""_%j_err.txt\n"""    
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

        userPDBpath = get_user_pdb_path()

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
                    ncluster="1"
                clusterSearch=" -xcluster "+ncluster
        else:
            ncluster=rho_xclusters.split(":")[-1]
            if ncluster=="":
                    ncluster="1"
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
        header+= """#SBATCH -o """+path+"""/fragmax/logs/pipedream_allDatasets_%j_out.txt\n"""
        header+= """#SBATCH -e """+path+"""/fragmax/logs/pipedream_allDatasets_%j_err.txt\n"""    
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
            allPipedreamOut+=chdir.replace("cd ","rm -rf ")+"/pipedream/"+"\n"
            allPipedreamOut+=ppd+"\n\n"
            
            scriptList.append(allPipedreamOut)
        chunkScripts=[header+"".join(x) for x in list(scrsplit(scriptList,nodes) )]

        for num,chunk in enumerate(chunkScripts):
            time.sleep(0.2)
            with open(path+"/fragmax/scripts/pipedream_part"+str(num)+".sh", "w") as outfile:
                outfile.write(chunk)
                    
            script=path+"/fragmax/scripts/pipedream_part"+str(num)+".sh"
            command ='echo "module purge | module load autoPROC BUSTER | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(command,shell=True)

    return render(request,
                  "fragview/jobs_submitted.html",
                  {"command":"<br>".join(ppdCMD.split(";;"))})


def get_pipedream_results():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    with open(path+"/fragmax/process/"+acr+"/pipedream.csv","w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["sample","summaryFile","fragment","fragmentLibrary","symmetry","resolution","rwork","rfree","rhofitscore","a","b","c","alpha","beta","gamma","ligsvg"])

        pipedreamXML=list()
        for s in shiftList:
            p="/data/visitors/biomax/"+proposal+"/"+s
            pipedreamXML+=glob.glob(p+"/fragmax/process/"+acr+"/*/*/pipedream/summary.xml")
        for summary in pipedreamXML:
            try:
                with open(summary,"r") as fd:
                    doc=xmltodict.parse(fd.read())


                sample=doc['GPhL-pipedream']['setup']["runfrom"].split("/")[-1]
                a=doc['GPhL-pipedream']['refdata']["cell"]["a"]
                b=doc['GPhL-pipedream']['refdata']["cell"]["b"]
                c=doc['GPhL-pipedream']['refdata']["cell"]["c"]
                alpha=doc['GPhL-pipedream']['refdata']["cell"]["alpha"]
                beta=doc['GPhL-pipedream']['refdata']["cell"]["beta"]
                gamma=doc['GPhL-pipedream']['refdata']["cell"]["gamma"]
                ligandID=doc['GPhL-pipedream']['ligandfitting']["ligand"]["@id"]
                symm=doc['GPhL-pipedream']['refdata']["symm"]
                rhofitscore=doc['GPhL-pipedream']['ligandfitting']["ligand"]["rhofitsolution"]["correlationcoefficient"]
                R=doc['GPhL-pipedream']['refinement']['Cycle'][-1]["R"]
                Rfree=doc['GPhL-pipedream']['refinement']['Cycle'][-1]["Rfree"]
                resolution=doc['GPhL-pipedream']['inputdata']['table1']['shellstats'][0]['reshigh']
                ligsvg=path.replace("/data/visitors/","/static/")+"/fragmax/process/fragment/"+fraglib+"/"+ligandID+"/"+ligandID+".svg"
                writer.writerow([sample,summary.replace("/data/visitors/","/static/").replace(".xml","_out.txt"),ligandID,fraglib,symm,resolution,R,Rfree,rhofitscore,a,b,c,alpha,beta,gamma,ligsvg])
                
            except:
                pass
        
def load_pipedream_density(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    sample=str(request.GET.get('structure')) 

    with open(path+"/fragmax/process/"+acr+"/pipedream.csv","r") as readFile:
        reader = csv.reader(readFile)
        lines = list(reader)[1:]
    
    for n,line in enumerate(lines):
        if line[0]==sample:
            ligand      =line[2]
            symmetry    =sym2spg(line[4])
            resolution  =line[5]
            rwork       =line[6]
            rfree       =line[7]
            rhofitscore =line[8]
            ligsvg      =line[-1]
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
            "ligsvg":ligsvg,
            # "name":name,

            # "frag":frag,
            # "prevst":prevst,
            # "nextst":nextst,
            
        })

################ PANDDA #####################

def pandda_density(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    panddaInput=str(request.GET.get('structure'))     
    
    if len(panddaInput.split(";"))==5:
        method,dataset,event,site,nav=panddaInput.split(";")
    if len(panddaInput.split(";"))==3:
        method,dataset,nav=panddaInput.split(";")
    
    mdl=[x.split("/")[-3] for x in sorted(glob.glob(path+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/*/modelled_structures/*model.pdb'))]
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
        modelledDir=path+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/'+dataset+'/modelled_structures/'
        pdb=sorted(glob.glob(modelledDir+"*fitted*"))[-1]
        
        center="[0,0,0]"
        rwork=""
        rfree=""
        resolution=""
        spg=""

        with open(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/pandda_inspect_events.csv","r") as inp:
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
        map1='biomax/'+proposal+'/'+shift+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/'+dataset+'/'+dataset+'-z_map.native.ccp4'
        map2=glob.glob('/data/visitors/biomax/'+proposal+'/'+shift+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/'+dataset+'/*BDC*ccp4')[0].replace("/data/visitors/","")
        summarypath=('biomax/'+proposal+'/'+shift+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/processed_datasets/"+dataset+"/html/"+dataset+".html")
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    panddaInput=str(request.GET.get('structure'))     
    
    

    
    dataset,site_idx,event_idx,method,ddtag,run=panddaInput.split(";")
    
    
    map1='biomax/'+proposal+'/'+shift+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/'+dataset+ddtag+"_"+run+'/'+dataset+ddtag+"_"+run+'-z_map.native.ccp4'
    map2=glob.glob(path+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/'+dataset+ddtag+"_"+run+'/*BDC*ccp4')[0].replace("/data/visitors/","")
    summarypath=('biomax/'+proposal+'/'+shift+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/processed_datasets/"+dataset+ddtag+"_"+run+"/html/"+dataset+ddtag+"_"+run+".html")

    allEventDict, eventDict,low_conf, medium_conf, high_conf = panddaEvents([])
          




    ligand=dataset.split("-")[-1].split("_")[0]+ddtag
    modelledDir=path+'/fragmax/results/pandda/'+acr+"/"+method+'/pandda/processed_datasets/'+dataset+ddtag+"_"+run+'/modelled_structures/'
    pdb=sorted(glob.glob(modelledDir+"*fitted*"))[-1]
    pdb=pdb.replace("/data/visitors/","")
    center="[0,0,0]"
    rwork=""
    rfree=""
    resolution=""
    spg=""

    with open(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/pandda_inspect_events.csv","r") as inp:
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    proc_methods=[x.split("/")[-5] for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/analyses/html_summaries/*inspect.html")]
    if proc_methods==[]:
        localcmd="cd "+path+"/fragmax/results/pandda/xdsapp_fspipeline/pandda/; pandda.inspect"
        return render(request,'fragview/pandda_notready.html', {"cmd":localcmd})
    newest=0
    newestpath=""
    newestmethod=""
    filters=[]
    eventscsv=[x for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/analyses/pandda_inspect_events.csv")]
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
            flat_filters=set([j for sub in [x.split("/")[10].split("_") for x in eventscsv] for j in sub])
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
        flat_filters=set([j for sub in [x.split("/")[10].split("_") for x in eventscsv] for j in sub])
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
                        run=v1[0].split("_")[-1]
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
                    run=v1[0].split("_")[-1]

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
        if os.path.exists(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/html_summaries/pandda_inspect.html"):
            with open(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/html_summaries/pandda_inspect.html","r") as inp:
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    methods=[x.split("/")[10] for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/analyses/*inspect_events*")]
    return render(request, "fragview/pandda.html",{"methods":methods})

def submit_pandda(request):

    #Function definitions
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    panddaCMD=str(request.GET.get("panddaform"))
    giantCMD=str(request.GET.get("giantform"))
    if "giantscore" in giantCMD:
        function,method=giantCMD.split(";")
        t2 = threading.Thread(target=giant_score,args=(method,))
        t2.daemon = True
        t2.start()
        return render(request, "fragview/submit_pandda.html",{"command":giantCMD})
    if "analyse" in panddaCMD:    
        function,proc,ref,complete,use_apo,use_dmso,use_cryo,use_CAD,ref_CAD,ign_errordts,keepup_last,ign_symlink=panddaCMD.split(";")
        
        method=proc+"_"+ref
        if os.path.exists(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/"):
            shutil.move(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/",path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda_backup/")    
        
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
            '''shiftList=sys.argv[5].split(",")\n'''  
            '''proposal=path.split("/")[4]\n'''           
            '''def pandda_run(method):\n'''
            '''    os.chdir(path+"/fragmax/results/pandda/"+acr+"/"+method)\n'''
            '''    command="pandda.analyse data_dirs='"+path+"/fragmax/results/pandda/"+acr+"/"+method+"/*' cpus=16" \n'''
            '''    subprocess.call(command, shell=True)\n'''
            '''    if len(glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/logs/*.log"))>0:\n'''
            '''        lastlog=sorted(glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/logs/*.log"))[-1]\n'''
            '''        with open(lastlog,"r") as logfile:\n'''
            '''            log=logfile.readlines()\n'''
            '''        badDataset=dict()\n'''
            '''        for line in log:\n'''
            '''            if "Structure factor column"  in line:\n'''
            '''                bd=line.split(" has ")[0].split("in dataset ")[-1]        \n'''
            '''                bdpath=glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+bd+"*")\n'''
            '''                badDataset[bd]=bdpath\n'''
            '''            if "Failed to align dataset" in line:\n'''
            '''                bd=line.split("Failed to align dataset ")[1].rstrip()\n'''
            '''                bdpath=glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+bd+"*")\n'''
            '''                badDataset[bd]=bdpath\n'''
            '''        for k,v in badDataset.items():\n'''
            '''            if len(v)>0:\n'''
            '''                if os.path.exists(v[0]):\n'''
            '''                    shutil.rmtree(v[0])\n''' 
            '''                    if os.path.exists(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k):\n'''
            '''                        shutil.rmtree(path+"/fragmax/process/pandda/ignored_datasets/"+method+"/"+k)\n'''
            '''                pandda_run(method)\n'''    
            '''pandda_run(method)\n'''        
            '''os.system('chmod -R g+rw '+path+'/fragmax/results/pandda/')\n''')

        methodshort=proc[:2]+ref[:2]
        with open(path+"/fragmax/scripts/panddaRUN_"+acr+method+".sh","w") as outp:
                outp.write('#!/bin/bash\n')
                outp.write('#!/bin/bash\n')
                outp.write('#SBATCH -t 99:55:00\n')
                outp.write('#SBATCH -J PDD'+methodshort+'\n')
                outp.write('#SBATCH --exclusive\n')
                outp.write('#SBATCH -N1\n')
                outp.write('#SBATCH --cpus-per-task=48\n')
                outp.write('#SBATCH --mem=220000\n')
                outp.write('#SBATCH -o '+path+'/fragmax/logs/panddarun_'+acr+method+'_%j_out.txt\n')
                outp.write('#SBATCH -e '+path+'/fragmax/logs/panddarun_'+acr+method+'_%j_err.txt\n')
                outp.write('module purge\n')
                outp.write('module load PReSTO\n')
                outp.write('\n')
                outp.write('python '+path+'/fragmax/scripts/pandda_worker.py '+path+' '+method+' '+acr+' '+fraglib+' '+",".join(shiftList)+'\n')
        
        #script=path+"/fragmax/scripts/panddaRUN_"+method+".sh"
        #command ='echo "module purge | module load PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        #subprocess.call(command,shell=True)
        t1 = threading.Thread(target=pandda_worker,args=(method,))
        t1.daemon = True
        t1.start()
        
        return render(request,
                      "fragview/jobs_submitted.html",
                      {"command": panddaCMD})

def pandda_analyse(request):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    fixsl=request.GET.get("fixsymlinks")
    if not fixsl is None and "FixSymlinks" in fixsl:
        t1 = threading.Thread(target=fix_pandda_symlinks,args=())
        t1.daemon = True
        t1.start()
    proc_methods=[x.split("/")[-2] for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda")]
    newest=datetime.datetime.strptime("2000-01-01-1234", '%Y-%m-%d-%H%M')
    newestpath=""
    newestmethod=""
    for methods in proc_methods:
        if len(glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+methods+"/pandda/analyses-*"))>0:
            last=sorted(glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+methods+"/pandda/analyses-*"))[-1]
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
                localcmd="cd "+path+"/fragmax/results/pandda/"+acr+"/"+newestmethod+"/pandda/; pandda.inspect"

                return render(request,'fragview/pandda_analyse.html', {"opencmd":localcmd,'proc_methods':proc_methods, 'Report': a.replace("PANDDA Processing Output","PANDDA Processing Output for "+newestmethod)})
        else:
            running=[x.split("/")[10] for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/*running*")]    
            return render(request,'fragview/pandda_notready.html', {'Report': "<br>".join(running)})

    else:
        if os.path.exists(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/html_summaries/pandda_analyse.html"):
            with open(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/html_summaries/pandda_analyse.html","r") as inp:
                a="".join(inp.readlines())
                localcmd="cd "+path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/; pandda.inspect"
            return render(request,'fragview/pandda_analyse.html', {"opencmd":localcmd,'proc_methods':proc_methods, 'Report': a.replace("PANDDA Processing Output","PANDDA Processing Output for "+method)})
        else:
            running=[x.split("/")[9] for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/*running*")]    
            return render(request,'fragview/pandda_notready.html', {'Report': "<br>".join(running)})

def datasetDetails(dataset,site_idx,method):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    detailsDict=dict()
    with open(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda/analyses/pandda_inspect_events.csv","r") as inp:
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    eventscsv=[x for x in glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/analyses/pandda_inspect_events.csv") ]
    if len(filters)!=0:
        eventscsv=[x for x in eventscsv if  any(xs in x for xs in filters)]
    eventDict=dict()
    allEventDict=dict()

    high_conf=0
    medium_conf=0
    low_conf=0

    for eventcsv in eventscsv:
        method=eventcsv.split("/")[10]
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
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    os.system("chmod -R 775 "+path+"/fragmax/results/pandda/")

    subprocess.call("cd "+path+"/fragmax/results/pandda/"+acr+"""/ ; find -type l -iname *-pandda-input.* -exec bash -c 'ln -f "$(readlink -m "$0")" "$0"' {} \;""",shell=True)
    subprocess.call("cd "+path+"/fragmax/results/pandda/"+acr+"""/ ; find -type l -iname *pandda-model.pdb -exec bash -c 'ln -f "$(readlink -m "$0")" "$0"' {} \;""",shell=True)
    subprocess.call("cd "+path+"/fragmax/results/pandda/"+acr+"""/ ; chmod -R 770 .""",shell=True)
    linksFolder=glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda/processed_datasets/*/modelled_structures/*pandda-model.pdb")
    for dst in linksFolder:    
        folder="/".join(dst.split("/")[:-1])+"/"
        pdbs=os.listdir(folder)
        src=folder+sorted([x for x in pdbs if "fitted" in x])[-1]
        os.remove(dst)
        shutil.copyfile(src,dst)
        
def pandda_giant(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    scoreDict=dict()
    available_scores=glob.glob(path+"/fragmax/results/pandda/"+acr+"/*/pandda-scores/residue_scores.html")
    if available_scores!=[]:
        for score in available_scores:
            with open(score,"r") as readFile:
                htmlcontent="".join(readFile.readlines())
                
            htmlcontent=htmlcontent.replace('src="./residue_plots','src="/static/'+'/'.join(score.split('/')[3:-1])+'/residue_plots')
            scoreDict[score.split('/')[-3]]=htmlcontent
        return render(request,'fragview/pandda_giant.html', {'scores_plots': scoreDict})
    else:
        return render(request, "fragview/index.html")

def pandda_worker(method):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    rn=str(randint(10000, 99999))

    
    header= '''#!/bin/bash\n'''
    header+='''#!/bin/bash\n'''
    header+='''#SBATCH -t 00:15:00\n'''
    header+='''#SBATCH -J PnD'''+rn+'''\n'''
    #header+='''#SBATCH --nice=25\n'''
    header+='''#SBATCH --cpus-per-task=1\n'''
    header+='''#SBATCH --mem=2500\n'''
    header+='''#SBATCH -o '''+path+'''/fragmax/logs/pandda_prepare_'''+acr+'''_%j_out.txt\n'''
    header+='''#SBATCH -e '''+path+'''/fragmax/logs/pandda_prepare_'''+acr+'''_%j_err.txt\n'''
    header+='''module purge\n'''
    header+='''module load CCP4 Phenix\n'''

    fragDict=dict()
    datasetDict=dict()
    for _dir in glob.glob(path+"/fragmax/process/fragment/"+fraglib+"/*"):
        fragDict[_dir.split("/")[-1]]=_dir

    datasetDict ={dt.split("/")[-1].split("_master.h5")[0]:dt for dt in sorted([x for x in [item for it in [glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/raw/"+acr+"/*/*master.h5") for s in shiftList] for item in it] if "ref-" not in x])}
    selectedDict={ x.split("/")[-4]:x for x in sorted([x for x in [item for it in [glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/results/"+acr+"*/"+method.replace("_","/")+"/final.pdb") for s in shiftList] for item in it]]) }
    missingDict ={ k : datasetDict[k] for k in set(datasetDict) - set(selectedDict) }

    for dataset in missingDict:
        optionList=[item for it in [glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/results/"+dataset+"/*/*/final.pdb") for s in shiftList] for item in it ]
        if optionList==[]:
            selectedDict[dataset]=""
        else:
            prefered= sorted([s for s in optionList if method.split("_")[0] in s or method.split("_")[-1] in s], reverse=True)    
            if prefered ==[] and optionList!=[]:  
                prefered=sorted([s for s in optionList if "dials" in s or "xdsapp" in s or "autoproc" in s], reverse=True)
                if prefered ==[]:                  
                    sub = optionList[0]            
                elif prefered!=[]:
                    sub = prefered[0]
            elif prefered!=[]:
                sub = prefered[0]
            selectedDict[dataset]=sub


    for dataset,pdb in selectedDict.items():
        if os.path.exists(pdb):
            with open(path+"/fragmax/scripts/pandda_prepare_"+acr+dataset.split("-")[-1]+".sh","w") as writeFile:
                writeFile.write(header)
                proc,ref= method.split("_")        
                frag=dataset.split("-")[-1].split("_")[0]
                hklin=pdb.replace(".pdb",".mtz")
                os.makedirs(path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/",exist_ok=True)
                hklout=path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/final.mtz"
                cmdcp1="cp "+pdb+" "+path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/final.pdb"
                cmdcp2="cp "+hklin+" "+path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/final.mtz"
                cmd =  """echo 'source $HOME/Apps/CCP4/ccp4-7.0/bin/ccp4.setup-sh; cd /tmp; mtzdmp """+hklin+"""' | ssh -F ~/.ssh/ w-guslim-cc-0"""
                output = subprocess.Popen( cmd, shell=True,stdout=subprocess.PIPE ).communicate()[0].decode("utf-8")
                
                for i in output.splitlines():
                    if "A )" in i:
                        resHigh=i.split()[-3]
                    if "free" in i.lower() and "flag" in i.lower():
                        freeRflag=i.split()[-1]
                    spl_l=i.split()
                    if len(spl_l)>2: 
                        if spl_l[-2]=="F" and spl_l[-1]=="FP":
                            flabel="FP"
                            sigflabel="SIGFP"
                        if spl_l[-2]=="F" and spl_l[-1]=="F":
                            flabel="F"
                            sigflabel="SIGF"
                cad_fill    = '''echo -e " monitor BRIEF\\n labin file 1 -\\n  ALL\\n resolution file 1 999.0 '''+resHigh+'''" | cad hklin1 '''+hklin+''' hklout '''+hklout
                uniqueify   = '''uniqueify -f '''+freeRflag+''' '''+hklout+''' '''+hklout                
                hklout_rfill= hklout.replace(".mtz","_rfill.mtz")
                hklout_coef = hklout.replace(".mtz","_map_coeffs.mtz")
                freerflag   = '''echo -e "COMPLETE FREE='''+freeRflag+''' \\nEND" | freerflag hklin '''+hklout+''' hklout '''+hklout_rfill
                phenix_maps = "phenix.maps "+hklout_rfill+" "+hklout.replace(".mtz",".pdb")+"; mv "+hklout+" "+hklout.replace(".mtz","_original.mtz")+"; mv "+hklout.replace(".mtz","_map_coeffs.mtz")+" "+hklout
                cad_copyflag='''echo -e "monitor BRIEF \\n labin file_number 1 ALL \\nlabin file_number 2 E1='''+flabel+''' E2='''+sigflabel+''' E3='''+freeRflag+''' \\nlabout file_number 2 E1='''+flabel+''' E2='''+sigflabel+''' E3='''+freeRflag+'''" | cad hklin1 '''+hklout_coef+''' hklin2 '''+hklout_rfill+''' hklout '''+hklout
                
                writeFile.write(cmdcp1+"\n")
                writeFile.write(cad_fill+"\n")
                writeFile.write(uniqueify+"\n")
                writeFile.write(freerflag+"\n")
                writeFile.write(phenix_maps+"\n")
                #writeFile.write(cad_copyflag+"\n")

                if "Apo" not in dataset:        
                    cmdcp3="cp "+fragDict[frag]+"/"+frag+".cif "+path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/"+frag+".cif"                
                    cmdcp4="cp "+fragDict[frag]+"/"+frag+".pdb "+path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/"+frag+".pdb"                
                    writeFile.write(cmdcp3+"\n")
                    writeFile.write(cmdcp4+"\n")
            script=path+"/fragmax/scripts/pandda_prepare_"+acr+dataset.split("-")[-1]+".sh"
            cmd='echo "module purge | module load CCP4 | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
            subprocess.call(cmd,shell=True)
            
            

    cmd='echo "module purge | module load CCP4 | '+"sbatch --dependency=singleton --job-name=PnD"+rn+" "+path+"/fragmax/scripts/panddaRUN_"+acr+method+".sh"+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(cmd,shell=True)
            
def giant_score(method):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    header='''#!/bin/bash\n'''
    header+='''#!/bin/bash\n'''
    header+='''#SBATCH -t 00:05:00\n'''
    header+='''#SBATCH -J GiantScore\n'''
    header+='''#SBATCH --nice=25\n'''
    header+='''#SBATCH --cpus-per-task=1\n'''    
    header+='''#SBATCH --mem=2500\n'''        
    header+='''sleep 15000\n'''
    with open(path+"/fragmax/scripts/giant_holder.sh","w") as writeFile:
        writeFile.write(header)
    
    script=path+"/fragmax/scripts/giant_holder.sh"
    cmd='echo "module purge | module load CCP4 | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(cmd,shell=True)

    rn=str(randint(10000, 99999))
    jname="Gnt"+rn
    header='''#!/bin/bash\n'''
    header+='''#!/bin/bash\n'''
    header+='''#SBATCH -t 02:00:00\n'''
    header+='''#SBATCH -J '''+jname+'''\n'''
    header+='''#SBATCH --nice=25\n'''
    header+='''#SBATCH --cpus-per-task=2\n'''    
    header+='''#SBATCH --mem=5000\n'''
    header+='''#SBATCH -o '''+path+'''/fragmax/logs/pandda_export_%j.out\n'''
    header+='''#SBATCH -e '''+path+'''/fragmax/logs/pandda_export_%j.err\n\n'''
    header+='''module purge\n'''
    header+='''module load CCP4 Phenix\n'''


    panddaExport="pandda.export pandda_dir='"+path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda' export_dir='"+path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda-export'"
    

    with open(path+"/fragmax/scripts/pandda-export.sh","w") as writeFile:
        writeFile.write(header)
        writeFile.write(panddaExport)

    script=path+"/fragmax/scripts/pandda-export.sh"



    cmd='echo "module purge | module load CCP4 | sh '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(cmd,shell=True)


    header='''#!/bin/bash\n'''
    header+='''#!/bin/bash\n'''
    header+='''#SBATCH -t 02:00:00\n'''
    header+='''#SBATCH -J '''+jname+'''\n'''
    header+='''#SBATCH --nice=25\n'''
    header+='''#SBATCH --cpus-per-task=1\n'''    
    header+='''#SBATCH --mem=2500\n'''
    header+='''#SBATCH -o '''+path+'''/fragmax/logs/pandda_giant_%j_out.txt\n'''
    header+='''#SBATCH -e '''+path+'''/fragmax/logs/pandda_giant_%j_err.txt\n\n'''
    header+='''module purge\n'''
    header+='''module load CCP4 Phenix\n'''

    _dirs=glob.glob(path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda-export/*")

    line="#! /bin/bash"
    line+="\njid1=$(sbatch "+path+"/fragmax/scripts/pandda-export.sh)"
    line+="\njid1=`echo $jid1|cut -d ' ' -f4`"
    for _dir in _dirs:
        dataset=_dir.split("/")[-1]    
        src=path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/final_original.mtz"
        dst=path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda-export/"+dataset+"/"+dataset+"-pandda-input.mtz"
        cpcmd3="cp -f "+src+" "+dst
        if "Apo" not in _dir:
            try:
                ens=glob.glob(_dir+"/*ensemble*.pdb")[0]
                make_restraints="giant.make_restraints "+ens+" all=True resname=XXX"        
                inp_mtz=ens.replace("-ensemble-model.pdb","-pandda-input.mtz")
                frag=_dir.split("/")[-1].split("-")[-1].split("_")[0]
                quick_refine="giant.quick_refine "+ens+" "+inp_mtz+" "+frag+".cif multi-state-restraints.refmac.params resname=XXX"        
            except:
                ens=""
                make_restraints=""
                quick_refine=""
        with open(path+"/fragmax/scripts/giant_pandda_"+frag+".sh","w") as writeFile:
            writeFile.write(header)
            writeFile.write("\n"+"cd "+_dir)
            writeFile.write("\n"+cpcmd3)
            writeFile.write("\n"+make_restraints)            
            writeFile.write("\n"+quick_refine)        
        script=path+"/fragmax/scripts/giant_pandda_"+frag+".sh"
        line+="\nsbatch  --dependency=afterany:$jid1 "+path+"/fragmax/scripts/giant_pandda_"+frag+".sh"
        line+="\nsleep 0.1"
    with open(path+"/fragmax/scripts/giant_worker.sh","w") as writeFile:
        writeFile.write(line)
        writeFile.write("\n\nsbatch --dependency=singleton --job-name="+jname+" "+path+"/fragmax/scripts/pandda-score.sh")

    header='''#!/bin/bash\n'''
    header+='''#!/bin/bash\n'''
    header+='''#SBATCH -t 02:00:00\n'''
    header+='''#SBATCH -J '''+jname+'''\n'''
    header+='''#SBATCH --nice=25\n'''
    header+='''#SBATCH --cpus-per-task=2\n'''    
    header+='''#SBATCH --mem=2000\n'''
    header+='''#SBATCH -o '''+path+'''/fragmax/logs/pandda_score_%j_out.txt\n'''
    header+='''#SBATCH -e '''+path+'''/fragmax/logs/pandda_score_%j_err.txt\nn'''
    header+='''module purge\n'''
    header+='''module load CCP4 Phenix\n\n'''
    scoreModel='giant.score_model_multiple out_dir="'+path+"/fragmax/results/pandda/"+acr+"/"+method+'/pandda-scores" '+path+"/fragmax/results/pandda/"+acr+"/"+method+'/pandda-export/* res_names="XXX" cpu=24'

    with open(path+"/fragmax/scripts/pandda-score.sh","w") as writeFile:
        writeFile.write(header)
        scorecmd="""echo 'source $HOME/Apps/CCP4/ccp4-7.0/bin/ccp4.setup-sh;"""+scoreModel+"""' | ssh -F ~/.ssh/ w-guslim-cc-0"""
        for _dir in _dirs:
            dataset=_dir.split("/")[-1]    
            src=path+"/fragmax/results/pandda/"+acr+"/"+method+"/"+dataset+"/final_original.mtz"
            dst=path+"/fragmax/results/pandda/"+acr+"/"+method+"/pandda-export/"+dataset+"/"+dataset+"-pandda-input.mtz"
            cpcmd3="cp -f "+src+" "+dst
            writeFile.write("\n"+cpcmd3)

        writeFile.write("\n"+scorecmd)

    script=path+"/fragmax/scripts/giant_worker.sh"
    cmd='echo "module purge | module load CCP4 | sh '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call(cmd,shell=True)

#############################################

def procReport(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    method=""
    report=str(request.GET.get('dataHeader')) 
    if "fastdp" in report or "EDNA" in report:
        method="log"
        with open(report.replace("/static/","/data/visitors/"),"r") as readFile:
            report=readFile.readlines()
        report="<br>".join(report)
    return render(request,'fragview/procReport.html', {'reportHTML': report, "method":method})

def dataproc_merge(request):    
    #NEEDS UPDATE 
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    outinfo=str(request.GET.get("mergeprocinput")).replace("static","data/visitors")
    
    runList="<br>".join(glob.glob(outinfo+"*/*"))
    
    return render(request,'fragview/dataproc_merge.html', {'datasetsRuns': runList})

def reproc_web(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
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
            outp.write('\n#SBATCH -o '+path+'/fragmax/logs/manual_proc_'+procSW+'_%j_out.txt')
            outp.write('\n#SBATCH -e '+path+'/fragmax/logs/manual_proc_'+procSW+'_%j_err.txt')
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
                os.makedirs(outputdir+"/xdsapp",mode=0o760, exist_ok=True)
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
                os.makedirs(outputdir,mode=0o760, exist_ok=True)
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
                outp.write('\n#SBATCH -o '+path+'/fragmax/logs/manual_refine_'+procSW+'_'+refineSW+'_%j_out.txt')
                outp.write('\n#SBATCH -e '+path+'/fragmax/logs/manual_refine_'+procSW+'_'+refineSW+'_%j_err.txt')
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
    empty,dimpleSW,fspSW,busterSW,refinemode,mrthreshold,refinerescutoff,userPDB,refspacegroup,filters,customrefdimple,customrefbuster,customreffspipe,aimlessopt=userInput.split(";;")
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
    os.makedirs(path+"/fragmax/models/",mode=0o777, exist_ok=True)
    if pdbmodel!="":
        if pdbmodel in [x.split("/")[-1].split(".pdb")[0] for x in glob.glob(path+"/fragmax/models/*.pdb")]:
            if ".pdb" not in pdbmodel:
                pdbmodel=path+"/fragmax/models/"+pdbmodel+".pdb"
            else:
                pdbmodel=path+"/fragmax/models/"+pdbmodel
        elif "/data/visitors/biomax/" in pdbmodel:

            if not os.path.exists(path+"/fragmax/models/"+pdbmodel.split("/")[-1]):
                shutil.copyfile(pdbmodel,path+"/fragmax/models/"+pdbmodel.split("/")[-1])
                pdbmodel=path+"/fragmax/models/"+pdbmodel.split("/")[-1]
        else:
            if ".pdb" in pdbmodel:
                pdbmodel=pdbmodel.split(".pdb")[0]
            with open(path+"/fragmax/models/"+pdbmodel+".pdb","w") as pdb:
                pdb.write(pypdb.get_pdb_file(pdbmodel, filetype='pdb'))
            pdbmodel=path+"/fragmax/models/"+pdbmodel+".pdb"
    pdbmodel.replace(".pdb.pdb",".pdb")
    spacegroup=refspacegroup.replace("refspacegroup:","")
    run_structure_solving(useDIMPLE, useFSP, useBUSTER, pdbmodel, spacegroup,filters,customrefdimple,customrefbuster,customreffspipe,aimlessopt)
    outinfo = "<br>".join(userInput.split(";;"))

    return render(request,'fragview/refine_datasets.html', {'allproc': outinfo})

def ligfit_datasets(request):
    #MAYBE NO USE ANYMORE
    userInput=str(request.GET.get("submitligProc"))
    empty,rhofitSW,ligfitSW,ligandfile,fitprocess,scanchirals,customligfit,ligfromname,filters=userInput.split(";;")
    useRhoFit="False"
    useLigFit="False"
    
    if "true" in rhofitSW:
        useRhoFit="True"
    if "true" in ligfitSW:
        useLigFit="True"
  
    t1 = threading.Thread(target=autoLigandFit,args=(useLigFit,useRhoFit,fraglib,filters))
    t1.daemon = True
    t1.start()
    return render(request,'fragview/ligfit_datasets.html', {'allproc': "<br>".join(userInput.split(";;"))})

def dataproc_datasets(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

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
        pnodes=30
        with open(path+"/fragmax/scripts/processALL.sh","w") as outp:
            outp.write("""#!/bin/bash \n"""
                    """#!/bin/bash \n"""
                    """#SBATCH -t 99:55:00 \n"""
                    """#SBATCH -J FragMAX \n"""
                    """#SBATCH --exclusive \n"""
                    """#SBATCH -N1 \n"""
                    """#SBATCH --cpus-per-task=40 \n"""
                    """#SBATCH -o """+path+"""/fragmax/logs/analysis_workflow_%j_out.txt \n"""
                    """#SBATCH -e """+path+"""/fragmax/logs/analysis_workflow_%j_err.txt \n"""
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
        filters=dtprc_inp[-1].split(":")[-1]
        sbatch_script_list=list()
        nodes=12
        if filters!="ALL":
            nodes=1
        if usexdsapp=="true":
            t = threading.Thread(target=run_xdsapp, args=(nodes, filters))
            t.daemon = True
            t.start()
        if usedials=="true":
            t = threading.Thread(target=run_dials, args=(nodes, filters))
            t.daemon = True
            t.start()
            
        if useautproc=="true":
            t = threading.Thread(target=run_autoproc, args=(nodes, filters))
            t.daemon = True
            t.start()
          
        if usexdsxscale=="true":
            t = threading.Thread(target=run_xdsxscale, args=(nodes, filters))
            t.daemon = True
            t.start()
            
        return render(request,'fragview/dataproc_datasets.html', {'allproc': "Jobs submitted using "+str(nodes)+" per method"})

    
    
    return render(request,'fragview/dataproc_datasets.html', {'allproc': ""})


########### HPC JOBS CONTROL #################
def kill_HPC_job(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    jobid_k=str(request.GET.get('jobid_kill'))     

    subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'scancel', jobid_k], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    sleep(5)
    proc = subprocess.Popen(
        ["ssh", "-t", "clu0-fe-1", "squeue", "-u", request.user.username],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        output+="<tr><td>"+"</td><td>".join(i.split())+"</td><td>"+prosw+"</td><td><a href='/static"+stdout_file+"'> job_"+i.split()[0]+"_out.txt</a></td><td><a href='/static"+stderr_file+"'>job_"+i.split()[0]+"""_err.txt</a></td><td>
           
        <form action="/hpcstatus_jobkilled/" method="get" id="kill_job_{0}" >
            <button class="btn-small" type="submit" value={0} name="jobid_kill" size="1">Kill</button>
        </form>

        </tr>""".format(i.split()[0])

    
    
    return render(request,'fragview/hpcstatus_jobkilled.html', {'command': output, 'history': ""})


def hpcstatus(request):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    proc = subprocess.Popen(
        ["ssh", "-t", "clu0-fe-1", "squeue", "-u", request.user.username],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    out, err = proc.communicate()
    #output=""
    hpcList=list()
    for j in out.decode("UTF-8").split("\n")[1:-1]:
        if j.split()!=[]:
            try:
                jobid,partition,name,user,ST,TIME,NODE,NODEn=j.split()
            except ValueError:
                jobid,partition,name,user,ST,TIME,NODE,NODEn1,NODEn2=j.split()
                NODEn=NODEn1+NODEn2
            try:
                stdErr,stdOut=sorted(list(item for it in [glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/logs/*"+jobid+"*") for s in shiftList] for item in it))
                stdErr=stdErr.replace("/data/visitors/","/static/")
                stdOut=stdOut.replace("/data/visitors/","/static/")
            except:
                stdErr,stdOut=["-","-"]
                
            hpcList.append([jobid,partition,name,user,ST,TIME,NODE,NODEn,stdErr,stdOut])
    
    return render(request,'fragview/hpcstatus.html', {'hpcList':hpcList, "proposal":proposal, "user":user})
##############################################

def retrieveParameters(xmlfile):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

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

def datacollectionSummary(acr, path):    
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    
    lists=list()
    for s in shiftList:
        lists+=glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml")


    if os.path.exists(path+"/fragmax/process/"+acr+"/datacollections.csv"):
        return
    else:        
        os.makedirs(path+"/fragmax/process/"+acr,mode=0o760, exist_ok=True)
        with open(path+"/fragmax/process/"+acr+"/datacollections.csv","w") as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(["imagePrefix","SampleName","dataCollectionPath","Acronym","dataCollectionNumber","numberOfImages","resolution","snapshot","ligsvg"])
            
            for xml in natsort.natsorted(lists, key=lambda x: ("Apo" in x, x)):    
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
                       
def resultSummary():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    
    def info_func(entry,isaDict):
        usracr,pdbout,dif_map,nat_map,spg,resolution,isa,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,ligfit_dataset,pipeline,rhofitscore,ligfitscore,ligblob=[""]*23
        pdbout   = ""
        usracr   = "_".join(entry.split("/")[8:11])
        pipeline = "_".join(entry.split("/")[9:11])
        isa      = isaDict[entry.split("/")[8]][entry.split("/")[9]]

        if "dimple" in usracr:
            with open(entry,"r") as inp:
                pdb_file=inp.readlines()
            for line in pdb_file:
                if "REMARK   3   FREE R VALUE                     :" in line:            
                    r_free=line.split()[-1]
                    r_free=str("{0:.2f}".format(float(r_free)))        
                    #bonds=line.split()[10]
                    #angles=line.split()[13]
                if "REMARK   3   R VALUE            (WORKING SET) :" in line:            
                    r_work=line.split()[-1]
                    r_work=str("{0:.2f}".format(float(r_work)))
                if "REMARK   3   BOND LENGTHS REFINED ATOMS        (A):" in line:
                    bonds=line.split()[-3]
                if "REMARK   3   BOND ANGLES REFINED ATOMS   (DEGREES):" in line:
                    angles=line.split()[-3]
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
                    spg="".join(line.split()[7:])

            entry=entry.replace("final.pdb","dimple.log")
            with open(entry,"r") as inp:
                dimple_log=inp.readlines()
            blist=[]
            for n,line in enumerate(dimple_log):                
                if line.startswith("blobs: "):                     
                    blist=line.split(":")[-1].rstrip()
                
            pdbout="/".join(entry.split("/")[3:-1])+"/final.pdb"
            dif_map ="/".join(entry.split("/")[3:-1])+"/final_2mFo-DFc.ccp4"
            nat_map ="/".join(entry.split("/")[3:-1])+"/final_mFo-DFc.ccp4"

        if "buster" in usracr:
            with open(entry,"r") as inp:
                pdb_file=inp.readlines()
            for line in pdb_file:
                if "REMARK   3   R VALUE            (WORKING SET) :" in line:            
                    r_work=line.split(" ")[-1]                
                    r_work=str("{0:.2f}".format(float(r_work)))
                if "REMARK   3   FREE R VALUE                     :" in line:            
                    r_free=line.split(" ")[-1]
                    r_free=str("{0:.2f}".format(float(r_free)))
                if "REMARK   3   BOND LENGTHS                       (A) :" in line:
                    bonds=line.split()[-1]
                if "REMARK   3   BOND ANGLES                  (DEGREES) :" in line:   
                    angles=line.split()[-1]
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
            if not os.path.exists(entry.replace("refine.pdb","final.pdb")):            
                shutil.copyfile(entry, entry.replace("refine.pdb","final.pdb"))
            if not os.path.exists(entry.replace("refine.pdb","final.mtz")):            
                shutil.copyfile(entry.replace("refine.pdb","refine.mtz"), entry.replace("refine.pdb","final.mtz"))
            blist="[]"
            pdbout="/".join(entry.split("/")[3:-1])+"/final.pdb"
            dif_map ="/".join(entry.split("/")[3:-1])+"/final_2mFo-DFc.ccp4"
            nat_map ="/".join(entry.split("/")[3:-1])+"/final_mFo-DFc.ccp4"

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
                    blist=[]
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
        
        return [usracr,pdbout,dif_map,nat_map,spg,resolution,isa,r_work,r_free,bonds,angles,a,b,c,alpha,beta,gamma,blist,ligfit_dataset,pipeline,rhofitscore,ligfitscore,ligblob]        
    
    
    xdsappLogs    = list()
    autoprocLogs  = list()
    dialsLogs     = list()
    xdsxscaleLogs = list()
    fastdpLogs    = list()
    EDNALogs      = list()
    isaDict       = dict()
    h5List        = list()
    for s in shiftList:
        xdsappLogs    += glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/process/"+acr+"/*/*/xdsapp/results*txt")
        autoprocLogs  += glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/process/"+acr+"/*/*/autoproc/process.log")
        dialsLogs     += glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/process/"+acr+"/*/*/dials/LogFiles/*log")
        xdsxscaleLogs += glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/fragmax/process/"+acr+"/*/*/xdsxscale/LogFiles/*XSCALE.log")
        fastdpLogs    += glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/process/"+acr+"/*/*/fastdp/results/*.LP")
        EDNALogs      += glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/process/"+acr+"/*/*/EDNA_proc/results/*.LP")


    for s in shiftList:
        h5List+=glob.glob("/data/visitors/biomax/"+proposal+"/"+s+"/raw/"+acr+"/*/*master.h5")
    h5List=sorted(h5List, key=lambda x: ("Apo" in x, x))
    for dataset in [x.split("/")[-1].split("_master.h5")[0] for x in h5List]:
            isaDict[dataset]={"xdsapp":"","autoproc":"","xdsxscale":"","dials":"","fastdp":"","EDNA":""}

    for log in xdsappLogs:
        dataset=log.split("/")[10]
        with open(log,"r") as readFile:
            logfile=readFile.readlines()
        for line in logfile:
            if "    ISa" in line:
                isa=line.split()[-1]
                isaDict[dataset].update({"xdsapp":isa})
    for log in autoprocLogs:
        dataset=log.split("/")[10]
        with open(log,"r") as readFile:
            logfile=readFile.readlines()
        for n,line in enumerate(logfile):
            if "ISa" in line:           
                isa=logfile[n+1].split()[-1]        
        isaDict[dataset].update({"autoproc":isa})
    for log in dialsLogs:
        dataset=log.split("/")[10]
        with open(log,"r") as readFile:
            logfile=readFile.readlines()
        for n,line in enumerate(logfile):
            if "ISa" in line:            
                isa=logfile[n+1].split()[-1]            
        isaDict[dataset].update({"dials":isa})
    for log in xdsxscaleLogs:
        dataset=log.split("/")[10]
        with open(log,"r") as readFile:
            logfile=readFile.readlines()
        for n,line in enumerate(logfile):
            if "ISa" in line:             
                if logfile[n+3].split()!=[]:                
                    isa=logfile[n+3].split()[-2]            
        isaDict[dataset].update({"xdsxscale":isa})
    for log in fastdpLogs:
        dataset=log.split("/")[9][4:-2]
        with open(log,"r") as readFile:
            logfile=readFile.readlines()
        for n,line in enumerate(logfile):
            if "ISa" in line:            
                isa=logfile[n+1].split()[-1]            
        isaDict[dataset].update({"fastdp":isa})
    for log in EDNALogs:
        dataset=log.split("/")[9][4:-2]
        with open(log,"r") as readFile:
            logfile=readFile.readlines()
        for n,line in enumerate(logfile):
            if "ISa" in line:             
                if logfile[n+3].split()!=[]:                
                    isa=logfile[n+3].split()[-2]
                    if isa=="b":
                        isa=""
        isaDict[dataset].update({"EDNA":isa})
    #for s in shiftList:
    #resultsList=glob.glob(path+"*/fragmax/results/"+acr+"**/*/dimple/final.pdb")+glob.glob(path+"*/fragmax/results/"+acr+"**/*/fspipeline/final.pdb")+glob.glob(path+"*/fragmax/results/"+acr+"**/*/buster/refine.pdb")
    
    resultsList=list()
    for s in shiftList:
        p="/data/visitors/biomax/"+proposal+"/"+s
        resultsList+=glob.glob(p+"*/fragmax/results/"+acr+"**/*/dimple/final.pdb")+glob.glob(p+"*/fragmax/results/"+acr+"**/*/fspipeline/final.pdb")+glob.glob(p+"*/fragmax/results/"+acr+"**/*/buster/refine.pdb")
    resultsList=sorted(resultsList, key=lambda x: ("Apo" in x, x))
    
    with open(path+"/fragmax/process/"+acr+"/results.csv","w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["usracr","pdbout","dif_map","nat_map","spg","resolution","ISa","r_work","r_free","bonds","angles","a","b","c","alpha","beta","gamma","blist","dataset","pipeline","rhofitscore","ligfitscore","ligblob"])        
        for entry in resultsList:
            row = ThreadWithReturnValue(target=info_func, args=(entry,isaDict,))
            row.start()
            
            if row.join() is not None:
                writer.writerow(row.join())
    
    
    #########################   

    
    with open(path+"/fragmax/scripts/plots.py","w") as writeFile:
        writeFile.write('''#!/mxn/home/guslim/anaconda2/envs/Python36/bin/python'''
                        '''\nimport pandas as pd'''
                        '''\nimport seaborn as sns'''
                        '''\nimport matplotlib.pyplot as plt'''
                        '''\nimport shutil'''
                        '''\nrst=pd.read_csv("'''+path+'''/fragmax/process/'''+acr+'''/results.csv")'''
                        '''\nunq=list()'''
                        '''\nnt=[unq.append(x) for x in sorted([x.split("-")[-1] for x in rst["dataset"]]) if x not in unq]'''
                        '''\nsns.set(color_codes=True)'''
                        '''\nsns.set_style("darkgrid", {"axes.facecolor": ".9"})'''
                        '''\nplt.figure(figsize=(30, 10), dpi=150)'''
                        '''\nax=sns.lineplot(x="dataset",y="ISa",data=rst, ci="sd",label="ISa", color="#82be00")'''
                        '''\nfor tick in ax.get_xticklabels():'''
                        '''\n    tick.set_rotation(90)'''
                        '''\nax.set_xlabel("Dataset")'''
                        '''\nax.set_ylabel("ISa")'''
                        '''\nnt=ax.set_xticklabels(unq)'''
                        '''\nfor tick in ax.get_xticklabels():'''
                        '''\n    tick.set_rotation(90)    '''
                        '''\nplt.savefig("'''+path+'''/fragmax/process/'''+acr+'''/ISas.png", bbox_inches='tight')'''
                        '''\nplt.figure(figsize=(30, 10), dpi=150)'''
                        '''\nax=sns.lineplot(x="dataset", y="r_free",data=rst, ci=66,  label="Rfree", color="#82be00")'''
                        '''\nax=sns.lineplot(x="dataset", y="r_work",data=rst, ci=66,  label="Rwork", color="#fea901")'''
                        '''\nfor tick in ax.get_xticklabels():'''
                        '''\n    tick.set_rotation(90)'''
                        '''\nax.set_xlabel("Dataset")'''
                        '''\nax.set_ylabel("Rfactor")'''
                        '''\nnt=ax.set_xticklabels(unq)'''
                        '''\nplt.savefig("'''+path+'''/fragmax/process/'''+acr+'''/Rfactors.png", bbox_inches='tight')'''
                        '''\nplt.figure(figsize=(30, 10), dpi=150)'''
                        '''\nax=sns.lineplot(x="dataset", y="a"    , data=rst, ci="sd", label="a" )'''
                        '''\nax=sns.lineplot(x="dataset", y="b"    , data=rst, ci="sd", label="b" )'''
                        '''\nax=sns.lineplot(x="dataset", y="c"    , data=rst, ci="sd", label="c" )'''
                        '''\nax=sns.lineplot(x="dataset", y="alpha", data=rst, ci="sd", label="alpha" )'''
                        '''\nax=sns.lineplot(x="dataset", y="beta" , data=rst, ci="sd", label="beta" )'''
                        '''\nax=sns.lineplot(x="dataset", y="gamma", data=rst, ci="sd", label="gamma" )'''
                        '''\nfor tick in ax.get_xticklabels():'''
                        '''\n    tick.set_rotation(90)    '''
                        '''\nax.set_xlabel("Dataset")'''
                        '''\nax.set_ylabel("Cell Parameter")'''
                        '''\nnt=ax.set_xticklabels(unq)'''
                        '''\nplt.savefig("'''+path+'''/fragmax/process/'''+acr+'''/Cellparameters.png", bbox_inches='tight')'''
                        '''\nplt.figure(figsize=(30, 10), dpi=150)'''
                        '''\nax=sns.lineplot(x="dataset",y="resolution",data=rst, ci="sd",label="Resolution", color="#82be00")'''
                        '''\nfor tick in ax.get_xticklabels():'''
                        '''\n    tick.set_rotation(90)'''
                        '''\nax.set_xlabel("Dataset")'''
                        '''\nax.set_ylabel("Resolution")'''
                        '''\nnt=ax.set_xticklabels(unq)'''
                        '''\nfor tick in ax.get_xticklabels():'''
                        '''\n    tick.set_rotation(90)    '''
                        '''\nplt.savefig("'''+path+'''/fragmax/process/'''+acr+'''/Resolutions.png", bbox_inches='tight')'''
                        '''\nfor s in ['''+",".join(shiftList)+''']:'''
                        '''\n    try:'''
                        '''\n        shutil.copyfile("'''+path+'''/fragmax/process/'''+acr+'''/Resolutions.png","/data/visitors/biomax/'''+proposal+'''/"+str(s)+"/fragmax/process/'''+acr+'''/Resolutions.png")'''
                        '''\n        shutil.copyfile("'''+path+'''/fragmax/process/'''+acr+'''/Rfactors.png","/data/visitors/biomax/'''+proposal+'''/"+str(s)+"/fragmax/process/'''+acr+'''/Rfactors.png")'''
                        '''\n        shutil.copyfile("'''+path+'''/fragmax/process/'''+acr+'''/Cellparameters.png","/data/visitors/biomax/'''+proposal+'''/"+str(s)+"/fragmax/process/'''+acr+'''/Cellparameters.png")'''
                        '''\n        shutil.copyfile("'''+path+'''/fragmax/process/'''+acr+'''/ISas.png","/data/visitors/biomax/'''+proposal+'''/"+str(s)+"/fragmax/process/'''+acr+'''/ISas.png")'''
                        '''\n    except:'''
                        '''\n        pass''')
    plotcmd="""echo '"""+"/mxn/home/guslim/anaconda2/envs/Python36/bin/python "+path+"/fragmax/scripts/plots.py"+"""' | ssh -F ~/.ssh/ w-guslim-cc-0"""
    subprocess.call(plotcmd,shell=True)


def run_xdsapp(nodes, filters):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
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
    header+= """#SBATCH -o """+path+"""/fragmax/logs/xdsapp_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/xdsapp_fragmax_%j_err.txt\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDSAPP\n\n"""

    scriptList=list()


    for xml in sorted(x for x in glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml") if filters in x):
    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
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
        with open(path+"/fragmax/scripts/xdsapp_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
                
        script=path+"/fragmax/scripts/xdsapp_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_autoproc(nodes, filters):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
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
    header+= """#SBATCH -o """+path+"""/fragmax/logs/autoproc_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/autoproc_fragmax_%j_err.txt\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 autoPROC\n\n"""

    scriptList=list()

    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in sorted(x for x in glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml") if filters in x):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
        outdir=os.path.join(proj.data_path(),"fragmax","process",proj.protein,dtc["imagePrefix"],dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"])
        h5master=dtc["imageDirectory"]+"/"+dtc["fileTemplate"].replace("%06d.h5","")+"master.h5"
        nImg=dtc["numberOfImages"]
        os.makedirs(outdir,mode=0o760, exist_ok=True)
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

def run_xdsxscale(nodes, filters):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
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
    header+= """#SBATCH -o """+path+"""/fragmax/logs/xdsxscale_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/xdsxscale_fragmax_%j_err.txt\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDS\n\n"""

    scriptList=list()

    with open(path+"/fragmax/scripts/filter.txt","w") as inp:
        inp.write(filters)    
    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in sorted(x for x in glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml") if filters in x):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
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
        with open(path+"/fragmax/scripts/xdsxscale_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
        script=path+"/fragmax/scripts/xdsxscale_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def run_dials(nodes, filters):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

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

    header+= """#SBATCH -o """+path+"""/fragmax/logs/dials_fragmax_%j_out.txt\n"""
    header+= """#SBATCH -e """+path+"""/fragmax/logs/dials_fragmax_%j_err.txt\n"""    
    header+= """module purge\n\n"""
    header+= """module load CCP4 XDS DIALS/1.12.3-PReSTO\n\n"""

    scriptList=list()

    
    xml_files = sorted(x for x in project_xml_files(proj) if filters in x)

    for xml in sorted(x for x in glob.glob(path+"**/process/"+acr+"/**/**/fastdp/cn**/ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml") if filters in x):
        with open(xml) as fd:
            doc = xmltodict.parse(fd.read())
        dtc=doc["XSDataResultRetrieveDataCollection"]["dataCollection"]
        outdir=dtc["imageDirectory"].replace("/raw/","/fragmax/process/")+"/"+dtc["imagePrefix"]+"_"+dtc["dataCollectionNumber"]
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
        with open(path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh", "w") as outfile:
            outfile.write(chunk)
        script=path+"/fragmax/scripts/dials_fragmax_part"+str(num)+".sh"
        command ='echo "module purge | module load CCP4 XDSAPP DIALS/1.12.3-PReSTO | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def process2results(spacegroup, filters, aimlessopt):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    for dp in ["xdsapp","autoproc","xdsxscale","EDNA","fastdp","dials"]:
        #[os.makedirs("/".join(x.split("/")[:9]+x.split("/")[10:]).replace("/process/","/results/")+dp, mode=0o760, exist_ok=True) for x in glob.glob(path+"/fragmax/process/AR/*/*/")]
        [os.makedirs("/".join(x.split("/")[:8]+x.split("/")[10:]).replace("/process/","/results/")+dp, mode=0o760, exist_ok=True) for x in glob.glob(path+"/fragmax/process/"+acr+"/*/*/")]
    with open(path+"/fragmax/scripts/process2results.py","w") as writeFile:
        writeFile.write('''import os '''
                '''\nimport glob'''
                '''\nimport subprocess'''
                '''\nimport shutil'''
                '''\nimport sys'''
                '''\npath="%s"'''
                '''\nacr="%s"'''
                '''\nspg="%s"'''
                '''\naimless="%s"'''
                '''\nsubprocess.call("rm "+path+"/fragmax/results/"+acr+"*/*/*merged.mtz",shell=True)'''
                '''\ndatasetList=glob.glob(path+"/fragmax/process/"+acr+"/*/*/")'''
                '''\nfor dataset in datasetList:    '''
                '''\n    if glob.glob(dataset+"autoproc/*mtz")!=[]:'''
                '''\n        try:'''
                '''\n            srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz") if "staraniso" in x][0]'''
                '''\n        except IndexError:'''
                '''\n            try:'''
                '''\n                srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz") if "aimless" in x][0]'''
                '''\n            except IndexError:'''
                '''\n                srcmtz=[x for x in glob.glob(dataset+"autoproc/*mtz")][0]'''
                '''\n    dstmtz=path+"/fragmax/results/"+dataset.split("/")[-2]+"/autoproc/"+dataset.split("/")[-2]+"_autoproc_merged.mtz"'''
                '''\n    if not os.path.exists(dstmtz) and os.path.exists(srcmtz):            '''
                '''\n        shutil.copyfile(srcmtz,dstmtz)'''
                '''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    srcmtz=dataset+"dials/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"'''
                '''\n    if os.path.exists(srcmtz):'''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/dials/"+dataset.split("/")[-2]+"_dials_merged.mtz"'''
                '''\n        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):            '''
                '''\n            shutil.copyfile(srcmtz,dstmtz)            '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    srcmtz=dataset+"xdsxscale/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"'''
                '''\n    if os.path.exists(srcmtz):'''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsxscale/"+dataset.split("/")[-2]+"_xdsxscale_merged.mtz"'''
                '''\n        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):            '''
                '''\n            shutil.copyfile(srcmtz,dstmtz)            '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    mtzoutList=glob.glob(dataset+"xdsapp/*F.mtz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]    '''
                '''\n    if os.path.exists(srcmtz):                '''
                '''\n        dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/xdsapp/"+dataset.split("/")[-2]+"_xdsapp_merged.mtz"        '''
                '''\n        if not os.path.exists(dstmtz) and os.path.exists(srcmtz):'''
                '''\n            shutil.copyfile(srcmtz,dstmtz)        '''
                '''\n            cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/EDNA_proc/results/*_noanom_aimless.mtz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]    '''
                '''\n    dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/EDNA/"+dataset.split("/")[-2]+"_EDNA_merged.mtz"        '''
                '''\n    if not os.path.exists(dstmtz) and os.path.exists(srcmtz):'''
                '''\n        shutil.copyfile(srcmtz,dstmtz)        '''
                '''\n        cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)        '''
                '''\n    mtzoutList=glob.glob(path+"/process/"+acr+"/"+dataset.split("/")[-3]+"/*"+dataset.split("/")[-2]+"*/fastdp/results/*_noanom_fast_dp.mtz.gz")'''
                '''\n    if mtzoutList!=[]:'''
                '''\n        srcmtz=mtzoutList[0]        '''
                '''\n        if os.path.exists(srcmtz):                '''
                '''\n            dstmtz=dataset.split("process/")[0]+"results/"+dataset.split("/")[-2]+"/fastdp/"+dataset.split("/")[-2]+"_fastdp_merged.mtz"        '''
                '''\n            if not os.path.exists(dstmtz) and os.path.exists(srcmtz):'''
                '''\n                shutil.copyfile(srcmtz,dstmtz)'''
                '''\n                try:'''
                '''\n                    subprocess.check_call(['gunzip', dstmtz+".gz"])'''
                '''\n                except:'''
                '''\n                    pass'''
                '''\n                a=dataset.split("process/")[0]+"results/"+dataset+"/fastdp/"+dataset+"_fastdp_unmerged.mtz"'''
                '''\n                cmd="echo 'choose spacegroup "+spg+"' | pointless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "+dstmtz+" HKLOUT "+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/aimless.log ; "'''
                '''\n        if aimless=="true":'''
                '''\n            subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)'''%(path,acr,spacegroup,aimlessopt))
                    
                


            

    proc2resOut=""

    #define env for script for dimple
    proc2resOut+= """#!/bin/bash\n"""
    proc2resOut+= """#!/bin/bash\n"""
    proc2resOut+= """#SBATCH -t 99:55:00\n"""
    proc2resOut+= """#SBATCH -J Pro2Res\n"""
    proc2resOut+= """#SBATCH --exclusive\n"""
    proc2resOut+= """#SBATCH -N1\n"""
    proc2resOut+= """#SBATCH --cpus-per-task=48\n"""
    proc2resOut+= """#SBATCH --mem=220000\n""" 
    proc2resOut+= """#SBATCH -o """+path+"""/fragmax/logs/process2results_%j_out.txt\n"""
    proc2resOut+= """#SBATCH -e """+path+"""/fragmax/logs/process2results_%j_err.txt\n"""    
    proc2resOut+= """module purge\n"""
    proc2resOut+= """module load CCP4 Phenix\n\n"""


    #HARD CODED
    #dimpleOut+=" & ".join(dimp)
    proc2resOut+="\n\n"
    proc2resOut+="python "+path+"/fragmax/scripts/process2results.py "
    with open(path+"/fragmax/scripts/run_proc2res.sh","w") as outp:
        outp.write(proc2resOut)
    
def run_structure_solving(useDIMPLE, useFSP, useBUSTER, userPDB, spacegroup, filters,customrefdimple,customrefbuster,customreffspipe,aimlessopt):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    customreffspipe = customreffspipe.split("customrefinefspipe:")[-1]    
    customrefbuster = customrefbuster.split("customrefinebuster:")[-1]
    customrefdimple = customrefdimple.split("customrefinedimple:")[-1]
    aimlessopt      = aimlessopt.split("aimlessopt:")[-1]
    argsfit="none"
    if "filters:" in filters:
        filters=filters.split(":")[-1]
    if filters=="ALL":
        filters=""
    process2results(spacegroup, filters,aimlessopt) 
    with open(path+'/fragmax/scripts/run_queueREF.py',"w") as writeFile:
        writeFile.write('''\nimport commands, os, sys, glob, time, subprocess'''
                        '''\nargsfit=sys.argv[1]'''
                        '''\npath=sys.argv[2]'''
                        '''\nacr=sys.argv[3]'''
                        '''\nPDBfile=sys.argv[4]'''
                        '''\ncmd = "sbatch "+path+"/fragmax/scripts/run_proc2res.sh"'''
                        '''\nstatus, jobnum1 = commands.getstatusoutput(cmd)'''
                        '''\njobnum1=jobnum1.split("batch job ")[-1]'''
                        '''\ninputData=list()'''
                        '''\nfor proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):'''
                        '''\n    mtzList=glob.glob(proc+"*mtz")'''
                        '''\n    if mtzList and "'''+filters+'''" in proc:'''
                        '''\n        inputData.append(sorted(glob.glob(proc+"*mtz"))[0])'''
                        '''\ndef scrsplit(a, n):'''
                        '''\n    k, m = divmod(len(a), n)'''
                        '''\n    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))'''
                        '''\nif "dimple" in argsfit:'''
                        '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/run_dimple.sh" % (jobnum1,path)'''
                        '''\n    status,jobnum2 = commands.getstatusoutput(cmd)'''
                        '''\nif "fspipeline" in argsfit:'''                                                                                             
                        '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/fspipeline_master.sh" % (jobnum1,path)'''
                        '''\n    status,jobnum3 = commands.getstatusoutput(cmd)'''
                        '''\nif "buster" in argsfit:'''                        
                        '''\n    cmd = "sbatch --dependency=afterany:%s %s/fragmax/scripts/buster_master.sh" % (jobnum1,path)'''
                        '''\n    status,jobnum4 = commands.getstatusoutput(cmd)''')
    def fspipeline_hpc(PDB):
        inputData=list()
        scriptList=list()
        m=0
        inputData=list()
        fsp='''python /data/staff/biomax/guslim/FragMAX_dev/fm_bessy/fspipeline.py --sa=false --refine='''+PDB+''' --exclude="dimple fspipeline buster unmerged rhofit ligfit truncate" --cpu=2 '''+customreffspipe
        for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):
            mtzList=glob.glob(proc+"*mtz")
            if mtzList and filters in proc:
                inputData.append(sorted(glob.glob(proc+"*mtz"))[0])
        scriptList=["cd "+"/".join(x.split("/")[:-1])+"/ \n"+fsp for x in inputData]
        nodes=round(len(inputData)/48 + 0.499)
        node0=64-nodes

        for n,i in enumerate(list(scrsplit(scriptList,nodes))):    
            header='''#!/bin/bash\n'''
            header+='''#!/bin/bash\n'''
            header+='''#SBATCH -t 04:00:00\n'''
            header+='''#SBATCH -J FSpipeline\n'''
            header+='''#SBATCH --nodelist=cn'''+str(node0+n)+'''\n'''
            header+='''#SBATCH --nice=25\n'''
            header+='''#SBATCH --cpus-per-task=2\n'''    
            header+='''#SBATCH --mem=5000\n'''
            header+='''#SBATCH -o '''+path+'''/fragmax/logs/fsp_fragmax_%j_out.txt\n'''
            header+='''#SBATCH -e '''+path+'''/fragmax/logs/fsp_fragmax_%j_err.txt\n\n'''
            header+='''module purge\n'''
            header+='''module load CCP4 Phenix\n'''
            header+='''echo export TMPDIR='''+path+'''/fragmax/logs/\n\n'''
            for j in i:
                with open(path+"/fragmax/scripts/fspipeline_worker_"+str(m)+".sh","w") as writeFile:
                    writeFile.write(header+j)
                m+=1
        with open(path+"/fragmax/scripts/fspipeline_master.sh","w") as writeFile:
            writeFile.write("""#!/bin/bash\n"""
                            """#!/bin/bash\n"""
                            """#SBATCH -t 01:00:00\n"""
                            """#SBATCH -J FSPmaster\n\n"""
                            """#SBATCH -o """+path+"""/fragmax/logs/fspipeline_master_%j_out.txt\n"""
                            """for file in """+path+"/fragmax/scripts"+"""/fspipeline_worker*.sh; do   sbatch $file;   sleep 0.1; rm $file; done\n"""
                            """rm fspipeline_worker*sh""")

    def buster_hpc(PDB):
        inputData=list()
        scriptList=list()
        m=0
        for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):
            mtzList=glob.glob(proc+"*mtz")
            if mtzList and filters in proc:
                inputData.append(sorted(glob.glob(proc+"*mtz"))[0])
        nodes=round(len(inputData)/48 + 0.499)
        node0=54-nodes
        for n,srcmtz in enumerate(inputData):
            cmd=""
            dstmtz=srcmtz.replace("merged","truncate")
            if os.path.exists("/".join(srcmtz.split("/")[:-1])+"/buster"):
                cmd+="rm -rf "+"/".join(srcmtz.split("/")[:-1])+"/buster\n\n"
            if not os.path.exists(dstmtz):
                cmd+='echo "truncate yes \labout F=FP SIGF=SIGFP" | truncate hklin '+srcmtz+' hklout '+dstmtz+" | tee "+'/'.join(dstmtz.split('/')[:-1])+"/truncate.log\n\n"   
            cmd+="refine -L -p "+PDB+" -m "+dstmtz+" "+customrefbuster+" -TLS -nthreads 2 -d "+"/".join(srcmtz.split("/")[:-1])+"/buster \n"
            scriptList.append(cmd)
        for n,i in enumerate(list(scrsplit(scriptList,nodes))):
            header='''#!/bin/bash\n'''
            header+='''#!/bin/bash\n'''
            header+='''#SBATCH -t 04:00:00\n'''
            header+='''#SBATCH -J BUSTER\n'''
            header+='''#SBATCH --cpus-per-task=2\n'''
            header+='''#SBATCH --mem=5000\n'''
            header+='''#SBATCH --nice=25\n'''
            header+='''#SBATCH --nodelist=cn'''+str(node0+n)+'''\n'''
            header+='''#SBATCH -o '''+path+'''/fragmax/logs/buster_fragmax_%j_out.txt\n'''
            header+='''#SBATCH -e '''+path+'''/fragmax/logs/buster_fragmax_%j_err.txt\n\n'''
            header+='''module purge\n'''
            header+='''module load autoPROC BUSTER\n'''
            header+='''echo export TMPDIR='''+path+'''/fragmax/logs/\n\n'''
            for j in i:
                with open(path+"/fragmax/scripts/buster_worker_"+str(m)+".sh","w") as writeFile:
                    writeFile.write(header+j)
                m+=1
        with open(path+"/fragmax/scripts/buster_master.sh","w") as writeFile:
            writeFile.write("""#!/bin/bash\n"""
                            """#!/bin/bash\n"""
                            """#SBATCH -t 01:00:00\n"""
                            """#SBATCH -J BSTRmaster\n\n"""
                            """#SBATCH -o """+path+"""/fragmax/logs/buster_master_%j_out.txt\n"""
                            """for file in """+path+"/fragmax/scripts"+"""/buster_worker*.sh; do   sbatch $file;   sleep 0.1; rm $file; done\n"""
                            """rm buster_worker*sh""")

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
        dimpleOut+= """#SBATCH -o """+path+"""/fragmax/logs/dimple_fragmax_%j_out.txt\n"""
        dimpleOut+= """#SBATCH -e """+path+"""/fragmax/logs/dimple_fragmax_%j_err.txt\n"""    
        dimpleOut+= """module purge\n"""
        dimpleOut+= """module load CCP4 Phenix \n\n"""
        
        dimpleOut+="python "+path+"/fragmax/scripts/run_dimple.py"
        dimpleOut+="\n\n"
        
        with open(path+"/fragmax/scripts/run_dimple.sh","w") as outp:
            outp.write(dimpleOut)


        with open(path+"/fragmax/scripts/run_dimple.py","w") as writeFile:
            writeFile.write('''import multiprocessing\n'''
                            '''import subprocess\n'''
                            '''import glob\n'''
                            '''\n'''
                            '''\n'''
                            '''path="%s"\n'''
                            '''acr="%s"\n'''
                            '''PDB="%s"\n'''
                            '''\n'''
                            '''inputData=list()\n'''
                            '''for proc in glob.glob(path+"/fragmax/results/"+acr+"*/*/"):\n'''
                            '''    mtzList=glob.glob(proc+"*mtz")\n'''
                            '''    if mtzList and "%s" in proc:\n'''
                            '''        inputData.append(sorted(glob.glob(proc+"*mtz"))[0])\n'''
                            '''\n'''
                            '''outDirs=["/".join(x.split("/")[:-1])+"/dimple" for x in inputData]\n'''
                            '''mtzList=inputData\n'''
                            '''\n'''
                            '''inpdata=list()\n'''
                            '''for a,b in zip(outDirs,mtzList):\n'''
                            '''    inpdata.append([a,b])\n'''
                            '''    \n'''
                            '''def fragmax_worker((di, mtz)):\n'''
                            '''    command="dimple -s "+mtz+" "+PDB+" "+di+" %s ; cd "+di+" ; phenix.mtz2map final.mtz"\n'''
                            '''    subprocess.call(command, shell=True) \n'''
                            '''def mp_handler():\n'''
                            '''    p = multiprocessing.Pool(48)\n'''
                            '''    p.map(fragmax_worker, inpdata)\n'''
                            '''if __name__ == "__main__":\n'''
                            '''    mp_handler()\n'''%(path,acr,PDB,filters,customrefdimple))    
    
    if userPDB!="":         
        if useFSP:
            fspipeline_hpc(userPDB)
            argsfit+="fspipeline"
        if useDIMPLE:
            dimple_hpc(userPDB)
            argsfit+="dimple"
        if useBUSTER:
            buster_hpc(userPDB)
            argsfit+="buster"
    else:
        userPDB="-"
    
    command ='echo "python '+path+'/fragmax/scripts/run_queueREF.py '+argsfit+' '+path+' '+acr+' '+userPDB+' " | ssh -F ~/.ssh/ clu0-fe-1'
    subprocess.call("rm "+path+"/fragmax/scripts/*.setvar.lis",shell=True)
    subprocess.call("rm "+path+"/fragmax/scripts/slurm*_out.txt",shell=True)
    subprocess.call(command,shell=True)
    
def autoLigandFit(useLigFit,useRhoFit,fraglib,filters):
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()
    if "filters:" in filters:
        filters=filters.split(":")[-1]
    if filters=="ALL":
        filters=""
    with open(path+"/fragmax/scripts/autoligand.py","w") as writeFile:
        writeFile.write('''import multiprocessing\n'''
                '''import time\n'''
                '''import subprocess\n'''
                '''import sys\n'''
                '''import glob\n'''
                '''import os\n'''
                '''path="'''+path+'''"\n'''
                '''fraglib="'''+fraglib+'''"\n'''
                '''acr="'''+acr+'''"\n'''
                '''shiftList="'''+",".join(shiftList)+'''"\n'''
                '''fitmethod=sys.argv[4]\n'''
                '''pdbList=list()\n'''
                '''shiftList=shiftList.split(",")\n'''
                '''for s in shiftList:\n'''
                '''    p="/data/visitors/biomax/'''+proposal+'''/"+s\n'''
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
                    '''#SBATCH -o '''+path+'''/fragmax/logs/auto_rhofit_%j_out.txt\n'''
                    '''#SBATCH -e '''+path+'''/fragmax/logs/auto_rhofit_%j_err.txt\n'''
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
                    '''#SBATCH -o '''+path+'''/fragmax/logs/auto_ligfit_%j_out.txt\n'''
                    '''#SBATCH -e '''+path+'''/fragmax/logs/auto_ligfit_%j_err.txt\n'''
                    '''module purge\n'''
                    '''module load autoPROC BUSTER Phenix CCP4\n'''
                    '''python '''+path+'''/fragmax/scripts/autoligand.py '''+path+''' '''+fraglib+''' '''+acr+''' ligfit\n''')
        command ='echo "module purge | module load CCP4 Phenix | sbatch '+script+' " | ssh -F ~/.ssh/ clu0-fe-1'
        subprocess.call(command,shell=True)

def get_project_status():
    proposal,shift,acr,proposal_type,path, subpath, static_datapath,fraglib,shiftList=project_definitions()

    statusDict=dict()
    procList=list()
    resList =list()
    for s in shiftList:
        p="/data/visitors/biomax/"+proposal+"/"+s
        procList+=["/".join(x.split("/")[:8])+"/"+x.split("/")[-2]+"/" for x in glob.glob(p+"/fragmax/process/"+acr+"/*/*/")]
        resList+=glob.glob(p+"/fragmax/results/"+acr+"*/")
    
    
    for i in procList:
        dataset_run=i.split("/")[-2]
        statusDict[dataset_run]={"autoproc":"none","dials":"none","EDNA":"none","fastdp":"none","xdsapp":"none","xdsxscale":"none","dimple":"none","fspipeline":"none","buster":"none","rhofit":"none","ligfit":"none"}
        
    for result in resList:
        dts=result.split("/")[-2]
        if dts not in statusDict:
            statusDict[dts]={"autoproc":"none","dials":"none","EDNA":"none","fastdp":"none","xdsapp":"none","xdsxscale":"none","dimple":"none","fspipeline":"none","buster":"none","rhofit":"none","ligfit":"none"}
    
        for j in glob.glob(result+"*"):
            dp=j.split("/")[-1]
            if os.path.exists(j+"/dimple/final.pdb"):
                statusDict[dts].update({"dimple":"full"})
            if os.path.exists(j+"/fspipeline/final.pdb"):
                statusDict[dts].update({"fspipeline":"full"})
            if os.path.exists(j+"/buster/final.pdb"):
                statusDict[dts].update({"buster":"full"})
            if glob.glob(j+"/*/ligfit/LigandFit*/ligand_fit_*.pdb")!=[]:
                statusDict[dts].update({"ligfit":"full"})
            if glob.glob(j+"/*/rhofit/best.pdb")!=[]:
                statusDict[dts].update({"rhofit":"full"})
                
    for process in procList:
        dts=process.split("/")[-2]
        j=list()
        for s in shiftList:
            p="/data/visitors/biomax/"+proposal+"/"+s
            j+=glob.glob(p+"/fragmax/process/"+acr+"/*/"+dts+"/")
        #j=glob.glob(path+"/fragmax/process/"+acr+"/*/"+dts+"/")
        if j!=[]:
            j=j[0]
        if glob.glob(j+"/autoproc/*staraniso*.mtz")+glob.glob(j+"/autoproc/*aimless*.mtz")!=[]:            
            statusDict[dts].update({"autoproc":"full"})
        if glob.glob(j+"/dials/DataFiles/*mtz")!=[]:            
            statusDict[dts].update({"dials":"full"})
        ej=list()
        for s in shiftList:
            p="/data/visitors/biomax/"+proposal+"/"+s            
            ej+=glob.glob(p+"/process/"+acr+"/*/*"+dts+"*/EDNA_proc/results/*mtz")
        if ej!=[]:
            statusDict[dts].update({"EDNA":"full"})
        fj=list()
        for s in shiftList:
            p="/data/visitors/biomax/"+proposal+"/"+s            
            fj+=glob.glob(p+"/process/"+acr+"/*/*"+dts+"*/fastdp/results/*mtz.gz")    
        if fj!=[]:
            statusDict[dts].update({"fastdp":"full"})
        if glob.glob(j+"/xdsapp/*mtz")!=[]:            
            statusDict[dts].update({"xdsapp":"full"})
        if glob.glob(j+"/xdsxscale/DataFiles/*mtz")!=[]:            
            statusDict[dts].update({"xdsxscale":"full"})    

    with open(path+"/fragmax/process/"+acr+"/allstatus.csv","w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["dataset","run","autoproc","dials","EDNA","fastdp","xdsapp","xdsxscale","dimple","fspipeline","buster","ligfit","rhofit"])    
        for dataset_run,status in statusDict.items():    
            writer.writerow([dataset_run]+list(status.values()))

###############################

###############################        
def scrsplit(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

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
