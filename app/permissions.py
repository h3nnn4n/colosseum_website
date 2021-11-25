from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.owner == request.user


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, _view):
        return request.method in permissions.SAFE_METHODS


class IsAdminUserOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, _view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_staff)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, _view):
        return bool(request.user and request.user.is_staff)


class IsOwnerPermissionMixin(UserPassesTestMixin):
    def test_func(self):
        current_user = self.request.user
        object_onwer = self.get_object().owner

        return current_user == object_onwer
