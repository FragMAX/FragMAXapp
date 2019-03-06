from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from django.utils import timezone
from .models import Post
from .forms import PostForm
from difflib import SequenceMatcher

import glob
import os
import random


################################
#User specific data
#Changing this parameters for different projects based on user credentials
acr="hCAII"
proposal="20180489"
shift="20190127"
proposal_type="visitors"

path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"
static_datapath="/static/biomax/"+proposal+"/"+shift
################################

def index(request):
    return render(request, "fragview/index.html")

def process_all(request):
    return render(request, "fragview/process_all.html")
    
def load_project_summary(request):
    a="data from user project"
    return render(request,'fragview/project_summary.html', {'structure': a,})

def dataset_info(request):    
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


    return render(request,'fragview/dataset_info.html', {
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
    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift

    with open(path+"/fragmax/process/datacollectionPar.csv","r") as inp:
        a=inp.readlines()

    acr_list=a[1].split(",")
    prf_list=a[2].split(",")
    res_list=a[3].split(",")
    img_list=a[4].split(",")
    path_list=a[5].split(",")
    snap_list=a[6].split(",")
    png_list=a[7].split(",")
    run_list=a[8].split(",")

    results = zip(img_list,prf_list,res_list,path_list,snap_list,acr_list,png_list,run_list)
    return render_to_response('fragview/datasets.html', {'files': results})


def results(request):
    with open(path+"/fragmax/process/generalrefsum.csv","r") as inp:
        a=inp.readlines()
    return render_to_response('fragview/results.html', {'files': a})


def request_page(request):
    a=str(request.GET.get('structure'))     
    name=a.split(";")[0].split("/modelled_structures/")[-1].split(".pdb")[0]  
    a=zip([a.split(";")[0]],[a.split(";")[1]],[a.split(";")[2]],[a.split(";")[3]])  
    
    return render(request,'fragview/pandda_density.html', {'structure': a,'protname':name})

def request_page_res(request):
    a=str(request.GET.get('structure')) 
    center=""
    if "],[" in a.split(";")[3]:
        center=a.split(";")[3].split("],[")[0]+"]"
    else:
        center=a.split(";")[3].replace("],","")
    center=[a.split(";")[0]]    
    a=zip([a.split(";")[0].split("/pandda/")[-1].split("/final")[0]],[a.split(";")[0]],[a.split(";")[1]],[a.split(";")[2]],[a.split(";")[3]],center )    
    
    return render(request,'fragview/density.html', {'structure': a})

def ugly(request):
    a="load maps and pdb"
    return render(request,'fragview/ugly.html', {'Report': a})


def dual_ligand(request):
    a="load maps and pdb"
    return render(request,'fragview/dual_ligand.html', {'Report': a})

##################################
####### COMPARE TWO LIGANDS ######
##################################
def compare_poses(request):
    a=str(request.GET.get('ligfit_dataset')) 
    data=a.split(";")[0]
    blob=a.split(";")[1]
    png=data.split(acr+"-")[-1].split("_")[0]
    return render(request,'fragview/dual_density.html', {'ligfit_dataset': data,'blob': blob, 'png':png})

def ligfit_results(request):
    with open(path+"/fragmax/process/autolig.csv","r") as outp:
        a="".join(outp.readlines())
    
    return render(request,'fragview/ligfit_results.html', {'resTable': a})

###################################
##########Load external HTML#######
###################################


def pandda(request):    
    with open(path+"/fragmax/results/pandda/pandda/analyses/html_summaries/pandda_analyse.html","r") as inp:
        a="".join(inp.readlines())

    with open(path+"/fragmax/process/panddarefsum.csv","r") as inp:
        body="".join(inp.readlines())
    thead_ini=a.index("<thead>")+8
    thead_end=a.index("</thead>") 
    tbody_ini=a.index("<tbody>")+8
    tbody_end=a.index("</tbody>")     
    a=a.replace(a[thead_ini:thead_end],"""<tr>
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
            </tr>""")
    a=a.replace(a[tbody_ini:tbody_end],"<tr></tr>"+body)
    a=a.replace('class="table-responsive"','').replace('id="main-table" class="table table-bordered table-striped"','id="resultsTable"')
    
    return render(request,'fragview/pandda.html', {'Report': a})


def procReport(request):
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

    if a.startswith("autoPROC"):
        a=a.replace("autoPROC","")
        a=path+"/fragmax/results/"+a+"_1/pipedream/process/summary.html"
        if os.path.exists(a):
            with open(a,"r") as inp:
                html="".join(inp.readlines())
        else:
            html='<h5 style="padding-left:260px;" >autoPROC report for this dataset is not available</h5>' 
    html=html.replace('src="/data/visitors/','src="/static/').replace('href="/data/visitors/','href="/static/').replace("gphl_logo.png","data:image/png;base64,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")

    return render(request,'fragview/procReport.html', {'Report': html})


def reproc_web(request):
    dataproc = str(request.GET.get("submitProc"))
    outdir=dataproc.split(";")[0]
    data=dataproc.split(";")[1]
    
    import subprocess
    from time import sleep
    base_script="""#!/bin/bash
    #!/bin/bash
    #SBATCH -t 99:55:00
    #SBATCH -J FragWeb
    #SBATCH --exclusive
    #SBATCH -N1
    #SBATCH --cpus-per-task=48
    #SBATCH --mem=220000
    #SBATCH -o /data/visitors/biomax/20180489/20190127/fragmax/logs/manual_proc_WebApp_%j.out
    #SBATCH -e /data/visitors/biomax/20180489/20190127/fragmax/logs/manual_proc_WebApp_%j.err
    module load CCP4 XDSAPP autoPROC Phenix BUSTER

    {0}
    {1}

    """.format(outdir, data)

    with open("/data/visitors/biomax/20180489/20190127/fragmax/scripts/reprocess_webapp.sh","w") as inp:
        inp.write(base_script)

    command ='echo "module purge | module load CCP4 XDSAPP | sbatch /data/visitors/biomax/20180489/20190127/fragmax/scripts/reprocess_webapp.sh " | ssh -F ~/.ssh/ clu0-fe-1'
    sleep(1)
    subprocess.call(command,shell=True)

    proc = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'squeue','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    output=""
    for i in out.decode("UTF-8").split("\n")[1:-1]:
        output+="<tr><td>"+"</td><td>".join(i.split())+"</td></tr>"

    return render(request,'fragview/reproc_web.html', {'command': output})


def hpcstatus(request):
    import subprocess

    proc = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'squeue','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    output=""
    for i in out.decode("UTF-8").split("\n")[1:-1]:
        output+="<tr><td>"+"</td><td>".join(i.split())+"</td><td>job_"+i.split()[0]+".out</td><td>job_"+i.split()[0]+".err</td></tr>"

    proc_sacct = subprocess.Popen(['ssh', '-t', 'clu0-fe-1', 'sacct','-u','guslim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_sacct, err_sacct = proc_sacct.communicate()
    sacct=""
    for a in out_sacct.decode("UTF-8").split("\n")[2:-1]:
        linelist=[a[:13],a[13:23],a[23:34],a[34:45],a[45:56],a[56:67],a[67:]]
        linelist=[x.replace(" ","") for x in linelist]
        sacct+="<tr><td>"+"</td><td>".join(linelist)+"</td></tr>"

      
    return render(request,'fragview/hpcstatus.html', {'command': output, 'history': sacct})
#####################################################################################
#####################################################################################
########################## REGULAR PYTHON FUNCTIONS #################################
#####################################################################################
#####################################################################################


def retrieveParameters(xmlfile):
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