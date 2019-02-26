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
    

    with open(path+"/fragmax/process/refsum.csv","r") as inp:
        a=inp.readlines()

    return render_to_response('fragview/results.html', {'files': a})


def request_page(request):
    
    a=str(request.GET.get('structure')) 
    print(a)
    a=zip([a.split(";")[0]],[a.split(";")[1]],[a.split(";")[2]],[a.split(";")[3]])    
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
    
    path="/data/"+proposal_type+"/biomax/"+proposal+"/"+shift
    
    with open(path+"/fragmax/results/pandda/pandda/analyses/html_summaries/pandda_analyse.html","r") as inp:
        a="".join(inp.readlines())

    a=a.replace("<title>PANDDA Processing Output</title>","<style>.container{width: 1600px; max-width: 250% !important;} label{font-size: 1.8rem !important;}</style><title>PANDDA Processing 12Output</title>")
        
    return render(request,'fragview/pandda.html', {'Report': a})