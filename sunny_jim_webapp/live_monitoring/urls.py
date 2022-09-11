from django.urls import path

from .views import live_page

urlpatterns = [
    path('', live_page, name='live-page')
]