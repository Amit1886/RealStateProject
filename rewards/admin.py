from django.contrib import admin

from .models import (
    ReferralEvent,
    Reward,
    RewardCoin,
    RewardRule,
    RewardTransaction,
    ScratchCard,
    ScratchPrizeOption,
    SpinHistory,
    SpinRewardOption,
)
from .services import ensure_default_scratch_prizes


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "agent", "type", "achieved", "achieved_at", "created_at"]
    list_filter = ["type", "achieved"]
    search_fields = ["title", "agent__name"]
    autocomplete_fields = ["agent"]
    readonly_fields = ["created_at", "updated_at", "achieved_at"]


@admin.register(RewardCoin)
class RewardCoinAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "balance", "available_spins", "available_scratch_cards", "updated_at"]
    search_fields = ["user__email", "user__username"]
    readonly_fields = ["created_at", "updated_at", "last_daily_login_at"]


@admin.register(RewardRule)
class RewardRuleAdmin(admin.ModelAdmin):
    list_display = ["key", "title", "reward_type", "coin_amount", "wallet_amount", "spin_count", "is_active"]
    list_filter = ["reward_type", "is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RewardTransaction)
class RewardTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "source", "entry_type", "coins", "cash_value", "status", "created_at"]
    list_filter = ["source", "entry_type", "status"]
    search_fields = ["user__email", "dedupe_key", "narration"]
    readonly_fields = ["reference_id", "created_at"]


@admin.register(ReferralEvent)
class ReferralEventAdmin(admin.ModelAdmin):
    list_display = ["id", "referrer", "referred_user", "code_used", "status", "created_at", "rewarded_at"]
    list_filter = ["status"]
    search_fields = ["referrer__email", "referred_user__email", "code_used"]
    readonly_fields = ["created_at", "qualified_at", "rewarded_at"]


@admin.register(ScratchCard)
class ScratchCardAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "reward_type", "coin_amount", "wallet_amount", "status", "created_at"]
    list_filter = ["reward_type", "status"]
    search_fields = ["user__email", "title"]
    readonly_fields = ["reference_id", "created_at", "revealed_at", "claimed_at"]


@admin.register(SpinRewardOption)
class SpinRewardOptionAdmin(admin.ModelAdmin):
    list_display = ["id", "label", "reward_type", "coin_amount", "wallet_amount", "weight", "is_active"]
    list_filter = ["reward_type", "is_active"]


@admin.register(ScratchPrizeOption)
class ScratchPrizeOptionAdmin(admin.ModelAdmin):
    list_display = ["id", "label", "badge", "description", "reward_type", "coin_amount", "wallet_amount", "weight", "is_active"]
    list_filter = ["reward_type", "is_active"]
    search_fields = ["label", "badge", "description"]
    actions = ["load_demo_scratch_prizes"]
    readonly_fields = ["demo_hint"]

    def demo_hint(self, obj):
        return "Use the admin action to load the default demo prize presets."

    demo_hint.short_description = "Demo preset"

    @admin.action(description="Load demo scratch prize presets")
    def load_demo_scratch_prizes(self, request, queryset):
        ensure_default_scratch_prizes()
        self.message_user(request, "Demo scratch prize presets loaded.")


@admin.register(SpinHistory)
class SpinHistoryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "option", "reward_type", "coins_awarded", "wallet_amount", "status", "created_at"]
    list_filter = ["reward_type", "status"]
    search_fields = ["user__email", "option__label"]
    readonly_fields = ["reference_id", "created_at"]
