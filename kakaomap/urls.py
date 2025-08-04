# kakaomap/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.route_finder, name='route_finder'),
]