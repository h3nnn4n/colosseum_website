from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"users", views.UserViewSet)

urlpatterns = [
    path("", views.index, name="index"),
    path("", include(router.urls)),
    path("about", views.about, name="about"),
]
