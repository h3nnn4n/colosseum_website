from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("app.urls")),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("__debug__/", include("debug_toolbar.urls")),
]
