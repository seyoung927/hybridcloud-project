from django.shortcuts import render
from django.utils import timezone

def landing(request):
    return render(request, "landing.html", {"now": timezone.now()})
