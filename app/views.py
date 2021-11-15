from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path
from rest_framework import routers, serializers, viewsets

from app.serializers import UserSerializer


def index(request):
    context = {}
    return render(request, "home.html", context)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
