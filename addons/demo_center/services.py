from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils import timezone


@dataclass(frozen=True)
class DemoDefaults:
    orders_today: int = 47
    ai_calls_handled: int = 126
    auto_orders_created: int = 32
    low_stock_alerts: int = 5
    courier_dispatched: int = 29
    ads_running: int = 8
    revenue_today: int = 187000
    net_profit: int = 38400


DEFAULT_TOGGLES = {
    "autopilot_enabled": True,
    "low_stock_threshold_set": True,
    "social_accounts_connected": True,
    "ad_accounts_connected": True,
    "courier_apis_connected": True,
    "ai_call_assistant_enabled": True,
    "warehouse_assigned": True,
    "auto_workflow_rules_active": True,
}


def _cache_key(branch_code: str) -> str:
    return f"addons.demo_center.state:{branch_code or 'default'}"


def get_state(branch_code: str = "default") -> Dict[str, Any]:
    state = cache.get(_cache_key(branch_code))
    if state:
        return state

    defaults = DemoDefaults()
    state = {
        "generated_at": timezone.now().isoformat(),
        "branch_code": branch_code or "default",
        "toggles": dict(DEFAULT_TOGGLES),
        "metrics": {
            "orders_today": defaults.orders_today,
            "ai_calls_handled": defaults.ai_calls_handled,
            "auto_orders_created": defaults.auto_orders_created,
            "low_stock_alerts": defaults.low_stock_alerts,
            "courier_dispatched": defaults.courier_dispatched,
            "ads_running": defaults.ads_running,
            "revenue_today": defaults.revenue_today,
            "net_profit": defaults.net_profit,
        },
        "timeline": [
            {"title": "Call Received", "time": "10:01 AM"},
            {"title": "Order Confirmed", "time": "10:03 AM"},
            {"title": "Invoice Generated", "time": "10:03 AM"},
            {"title": "Payment Received", "time": "10:05 AM"},
            {"title": "Courier Assigned", "time": "10:06 AM"},
            {"title": "Dispatched", "time": "2:30 PM"},
            {"title": "Delivered", "time": "Next Day"},
        ],
        "campaign": {
            "name": "Festive Offer 20% OFF",
            "budget": 25000,
            "projected_reach": 48000,
            "expected_ctr": 3.8,
            "ab_split": {"variant_a": 60, "variant_b": 40},
            "captions": [
                "Festive season special: flat 20% OFF on best-sellers. Limited time only!",
                "Celebrate with savings—grab your essentials at 20% OFF today.",
                "Big festive deals are live! Shop now and save 20% instantly.",
            ],
            "assets": {
                "banners": ["banner_demo_1.png", "banner_demo_2.png"],
                "reel_script": "Hook → Problem → Offer → Social proof → CTA (demo script).",
            },
            "stats": {"reach": 39210, "clicks": 1489, "conversions": 97, "roi_pct": 164.2},
        },
        "courier": {
            "order_number": "10234",
            "courier": "Delhivery",
            "awb": "DL98765432",
            "status": "In Transit",
            "eta": "Tomorrow",
        },
        "transport": {
            "vehicle": "MH12AB1234",
            "driver": "Rajesh",
            "route": "Warehouse A → Pune",
        },
        "accounting": {"sales": 187000, "gst": 33660, "expenses": 92000, "net_profit": 38400},
        "hr": {"present": 18, "on_leave": 2, "late": 3, "salary_processed": 485000},
        "autopilot_logs": [
            "[INFO] Order Created → Invoice Generated",
            "[INFO] Stock Reduced",
            "[INFO] Courier Assigned",
            "[INFO] Customer Notified",
            "[SUCCESS] Payment Verified",
            "[COMPLETE] Order Closed",
        ],
        "charts": {
            "orders_hourly": {"labels": ["9AM", "10AM", "11AM", "12PM", "1PM", "2PM"], "data": [6, 12, 9, 8, 7, 5]},
            "revenue_week": {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "data": [120000, 150000, 98000, 163000, 187000, 210000, 175000]},
        },
    }
    cache.set(_cache_key(branch_code), state, timeout=60 * 60)
    return state


def get_user_state(user, branch_code: str = "default") -> Dict[str, Any]:
    """
    User-side demo state. Uses real demo data if present for this user,
    and falls back to sample numbers for presentation.
    """
    state = get_state(branch_code)
    user_metrics = {
        "parties": 0,
        "transactions": 0,
        "total_credit": 0,
        "total_debit": 0,
    }

    try:
        from khataapp.models import Party, Transaction

        parties_qs = Party.objects.filter(owner=user)
        user_metrics["parties"] = parties_qs.count()
        tx_qs = Transaction.objects.filter(party__owner=user)
        user_metrics["transactions"] = tx_qs.count()

        sums = tx_qs.values("txn_type").annotate(total=Sum("amount"))
        for row in sums:
            if row["txn_type"] == "credit":
                user_metrics["total_credit"] = float(row["total"] or 0)
            elif row["txn_type"] == "debit":
                user_metrics["total_debit"] = float(row["total"] or 0)
    except Exception:
        # keep zeros if legacy apps not ready
        pass

    state = {**state}
    state["user"] = {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", ""),
        "username": getattr(user, "username", ""),
    }
    state["user_metrics"] = user_metrics
    return state


def reset_state(branch_code: str = "default") -> Dict[str, Any]:
    cache.delete(_cache_key(branch_code))
    return get_state(branch_code)


def set_toggle(branch_code: str, key: str, enabled: bool) -> Dict[str, Any]:
    state = get_state(branch_code)
    toggles = state.get("toggles") or {}
    toggles[key] = bool(enabled)
    state["toggles"] = toggles
    cache.set(_cache_key(branch_code), state, timeout=60 * 60)
    return state
