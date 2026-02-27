"""
URL configuration for graph_django_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
]

''' Ovako dalje treba, ovo je primer sa vezbi
    path('kategorije/', views.lista_kategorija, name='lista_kategorija'),
    path('artikli/', artikli_view.lista_artikala, name='lista_artikala'),
    path('brisanje/artikla/<int:id>', artikli_view.brisanje_artikla, name='brisanje_artikla'),
    path('unos/artikla/', artikli_view.unos_artikla, name='unos_artikla'),
    path('unos/artikla/<int:id>', artikli_view.unos_artikla, name='unos_artikla_p'),
    path('prodavnice/', prodavnica_view.lista_prodavnica, name='lista_prodavnica'),
    path('brisanje/prodavnice/<int:id>', prodavnica_view.brisanje_prodavnice, name='brisanje_prodavnice'),
    path('unos/prodavnice/', prodavnica_view.unos_prodavnice, name='unos_prodavnice'),
    path('unos/prodavnice/<int:id>', prodavnica_view.unos_prodavnice, name='unos_prodavnice_p'),'''
