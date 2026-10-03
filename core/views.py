from django.shortcuts import render


def home(request):
    return render(request, "home/home.html")

def coming_soon(request):
    return render(request, "home/coming_soon.html")