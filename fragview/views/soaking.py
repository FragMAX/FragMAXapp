from django.shortcuts import render


def soaking_plan(request):
    return render(request,
                  "fragview/soaking_plan.html",
                  {"platename": "plateNumber1"})
