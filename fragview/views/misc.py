from django.shortcuts import render


def project_details(request):
    return render(request, "fragview/project_details.html")


def download_options(request):
    return render(request, "fragview/download_options.html")


def perc2float(v):
    return str("{:.3f}".format(float(v.replace("%", "")) / 100.0))
