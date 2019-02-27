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
################################


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
    subpath="/data/"+proposal_type+"/biomax/"+proposal+"/"

    with open(path+"/fragmax/process/datacollectionPar.csv","r") as inp:
        a=inp.readlines()

    acr_list=a[1].split(",")
    prf_list=a[2].split(",")
    res_list=a[3].split(",")
    img_list=a[4].split(",")
    path_list=a[5].split(",")
    snap_list=a[6].split(",")
    png_list=a[7].split(",")

    results = zip(img_list,prf_list,res_list,path_list,snap_list,acr_list,png_list)
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