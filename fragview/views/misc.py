from django.shortcuts import render


def project_details(request):
    return render(request, "fragview/project_details.html")


def download_options(request):
    return render(request, "fragview/download_options.html")


def testfunc(request):
    return render(request, "fragview/testpage.html", {"files": "results"})


def ugly(request):
    return render(request, "fragview/ugly.html")
