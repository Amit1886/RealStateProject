from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemMode
from .serializers import ChangeSystemModeSerializer, SystemModeSerializer
from .services import (
    build_request_mode_context,
    get_system_mode_state,
    switch_system_mode,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_staff)


class SystemModeAPIView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        mode_obj = SystemMode.get_solo()
        data = SystemModeSerializer(mode_obj).data
        data["resolved_mode"] = build_request_mode_context(request)["resolved_mode"]
        data["can_change"] = bool(request.user.is_staff)
        return Response(data)

    def patch(self, request):
        serializer = ChangeSystemModeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state = get_system_mode_state(force_refresh=True)

        if state.get("is_locked") and not request.user.is_superuser:
            if "current_mode" in serializer.validated_data:
                return Response(
                    {"detail": "System mode is locked globally. Super admin required to change mode."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        payload = switch_system_mode(
            current_mode=serializer.validated_data.get("current_mode"),
            is_locked=serializer.validated_data.get("is_locked"),
            updated_by=request.user,
        )
        return Response(payload, status=status.HTTP_200_OK)


class ChangeModeAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = ChangeSystemModeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        state = get_system_mode_state(force_refresh=True)
        if state.get("is_locked") and not request.user.is_superuser:
            if "current_mode" in serializer.validated_data:
                return Response(
                    {"detail": "System mode is locked globally. Super admin required to change mode."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        payload = switch_system_mode(
            current_mode=serializer.validated_data.get("current_mode"),
            is_locked=serializer.validated_data.get("is_locked"),
            updated_by=request.user,
        )
        return Response(payload, status=status.HTTP_200_OK)


class CurrentModeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        context = build_request_mode_context(request)
        context["can_change"] = bool(request.user and request.user.is_staff)
        return Response(context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def system_mode_panel(request):
    mode_obj = SystemMode.get_solo()
    if request.method == "POST":
        next_mode = request.POST.get("current_mode")
        next_lock = request.POST.get("is_locked") == "on"

        if mode_obj.is_locked and not request.user.is_superuser and next_mode != mode_obj.current_mode:
            messages.error(request, "System mode is globally locked. Super admin required to change mode.")
            return redirect("core_settings:system_mode_panel")

        switch_system_mode(
            current_mode=next_mode or mode_obj.current_mode,
            is_locked=next_lock,
            updated_by=request.user,
        )
        messages.success(request, "System mode updated successfully.")
        return redirect("core_settings:system_mode_panel")

    return render(
        request,
        "core_settings/system_mode_panel.html",
        {
            "mode_obj": mode_obj,
            "mode_choices": SystemMode.Mode.choices,
        },
    )
