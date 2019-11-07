from django.shortcuts import render


def index(request):
    return render(request, "fragview/index.html")


def results_download(request):
    return render(request, "fragview/results_download.html")


def testfunc(request):
    return render(request, "fragview/testpage.html", {"files": "results"})


def ugly(request):
    return render(request, "fragview/ugly.html")
