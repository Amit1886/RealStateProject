from .services import build_request_mode_context


def system_mode_context(request):
    context = getattr(request, "system_mode_context", None)
    if context is None:
        context = build_request_mode_context(request)

    return {
        "system_mode": context,
        "system_mode_name": context.get("current_mode", "DESKTOP"),
        "system_mode_locked": bool(context.get("is_locked", False)),
        "resolved_system_mode": context.get("resolved_mode", "DESKTOP"),
        "resolved_system_mode_css": context.get("resolved_mode_css", "desktop"),
        "system_route_profile": context.get("route_profile", {}),
    }
