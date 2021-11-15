from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import include, path
from rest_framework import routers, serializers, viewsets

from app.serializers import UserSerializer


def index(request):
    return HttpResponse("Hi")


def about(request):
    return HttpResponse("Soon")


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
