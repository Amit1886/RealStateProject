from __future__ import annotations

from functools import wraps
from importlib import import_module

from rest_framework import viewsets


def lazy_view(dotted_path: str, *, as_view_kwargs: dict | None = None):
    """
    Return a lightweight callable that imports the target view only when used.

    Works for plain function views and class-based views. For class-based views,
    pass as_view kwargs like {"get": "list"} or {"permission_classes": [...]}.
    """

    module_path, _, attr_name = dotted_path.rpartition(".")
    if not module_path or not attr_name:
        raise ValueError(f"Invalid dotted path: {dotted_path!r}")

    resolved = {}
    as_view_kwargs = as_view_kwargs or {}

    def resolve():
        if "callable" not in resolved:
            target = getattr(import_module(module_path), attr_name)
            if hasattr(target, "as_view"):
                target = target.as_view(**as_view_kwargs)
            resolved["callable"] = target
        return resolved["callable"]

    @wraps(resolve)
    def view(request, *args, **kwargs):
        return resolve()(request, *args, **kwargs)

    view._lazy_target = dotted_path  # type: ignore[attr-defined]
    return view


def lazy_viewset(dotted_path: str):
    """
    Return a lightweight DRF ViewSet proxy that imports the real ViewSet lazily.

    Use this with DefaultRouter.register(...) so startup does not import the
    underlying API module until a matching route is actually used.
    """

    module_path, _, attr_name = dotted_path.rpartition(".")
    if not module_path or not attr_name:
        raise ValueError(f"Invalid dotted path: {dotted_path!r}")

    resolved = {}

    def resolve():
        if "callable" not in resolved:
            resolved["callable"] = getattr(import_module(module_path), attr_name)
        return resolved["callable"]

    class LazyViewSet(viewsets.ViewSet):
        @classmethod
        def _resolve(cls):
            return resolve()

        @classmethod
        def as_view(cls, actions=None, **initkwargs):
            target = cls._resolve()
            return target.as_view(actions=actions, **initkwargs)

        @classmethod
        def get_extra_actions(cls):
            return []

    LazyViewSet.__name__ = f"Lazy{attr_name}"
    LazyViewSet.__qualname__ = LazyViewSet.__name__
    LazyViewSet.__module__ = __name__
    LazyViewSet._lazy_target = dotted_path  # type: ignore[attr-defined]
    return LazyViewSet
