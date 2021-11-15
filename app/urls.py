from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"users", views.UserViewSet)

urlpatterns = [
    path("home/", views.index, name="home"),
    path("api/", include(router.urls)),
    path(
        "", RedirectView.as_view(url="home/", permanent=True), name="redirect_to_home"
    ),
    path("accounts/register/", views.register_request, name="register"),
]
