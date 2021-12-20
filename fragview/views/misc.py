from django.shortcuts import render


def project_details(request):
    return render(request, "project_details.html")


def perc2float(v):
    return str("{:.3f}".format(float(v.replace("%", "")) / 100.0))
