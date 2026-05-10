import os

import yaml
from django.conf import settings
from rest_framework.permissions import BasePermission

_permissions_cache = None


def load_permissions():
    """
    Loads permissions.yaml once. Caches in memory.
    """
    global _permissions_cache

    if _permissions_cache is not None:
        return _permissions_cache

    path = os.path.join(settings.BASE_DIR, "config", "permissions.yaml")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    _permissions_cache = config.get("roles", {})
    return _permissions_cache


def is_action_allowed(role, resource, action):
    """
    Checks loaded permissions config.
    Returns True if role can perform action on resource.
    """

    permissions = load_permissions()
    role_permissions = permissions.get(role, {})
    allowed_actions = role_permissions.get(resource, [])

    if "*" in allowed_actions:
        return True

    return action in allowed_actions


class YAMLPermission(BasePermission):
    """
    Role based permission class driven by config/permissions.yaml
    Every view using this class must declare:
        resource_name = "listings" # must match yaml key exactly
    """

    def _get_action(self, request, view):
        if hasattr(view, "action"):
            return view.action

        method_map = {
            "GET": "retrieve",
            "POST": "create",
            "PATCH": "update",
            "PUT": "update",
            "DELETE": "destroy",
        }

        return method_map.get(request.method, "")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        resource = getattr(view, "resource_name", None)

        if not resource:
            return False

        action = self._get_action(request, view)
        role = request.user.role

        return is_action_allowed(role, resource, action)

    def has_object_permission(self, request, view, obj):
        return True
