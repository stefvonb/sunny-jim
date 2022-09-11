from django.shortcuts import render


def live_page(request):
    return render(request, 'live_monitoring/live_page.html')