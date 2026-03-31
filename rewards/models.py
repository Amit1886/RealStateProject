from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Reward(models.Model):
    class Type(models.TextChoices):
        BONUS = "bonus", "Bonus"
        CERTIFICATE = "certificate", "Certificate"
        OFFER = "offer", "Offer"

    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="rewards")
    title = models.CharField(max_length=160)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.BONUS)
    condition = models.CharField(max_length=200)
    achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    certificate_file = models.FileField(upload_to="certificates/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["agent", "type", "achieved"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.type})"

    def mark_achieved(self):
        self.achieved = True
        self.achieved_at = timezone.now()
        self.save(update_fields=["achieved", "achieved_at", "updated_at"])


class RewardCoin(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reward_coin")
    balance = models.PositiveIntegerField(default=0)
    lifetime_earned = models.PositiveIntegerField(default=0)
    lifetime_redeemed = models.PositiveIntegerField(default=0)
    available_spins = models.PositiveIntegerField(default=0)
    available_scratch_cards = models.PositiveIntegerField(default=0)
    last_daily_login_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.balance}"


class RewardRule(models.Model):
    class Key(models.TextChoices):
        SIGNUP_BONUS = "signup_bonus", "Signup Bonus"
        REFERRAL_REFERRER = "referral_referrer", "Referral Referrer"
        REFERRAL_INVITEE = "referral_invitee", "Referral Invitee"
        DAILY_LOGIN = "daily_login", "Daily Login"
        LEAD_CONVERSION = "lead_conversion", "Lead Conversion"
        COIN_TO_WALLET = "coin_to_wallet", "Coin To Wallet"

    class RewardType(models.TextChoices):
        COINS = "coins", "Coins"
        CASHBACK = "cashback", "Cashback"
        SPIN = "spin", "Spin"
        SCRATCH = "scratch", "Scratch"

    key = models.CharField(max_length=40, choices=Key.choices, unique=True)
    title = models.CharField(max_length=120)
    reward_type = models.CharField(max_length=20, choices=RewardType.choices, default=RewardType.COINS)
    coin_amount = models.PositiveIntegerField(default=0)
    wallet_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    spin_count = models.PositiveIntegerField(default=0)
    scratch_cards_count = models.PositiveIntegerField(default=0)
    max_per_user = models.PositiveIntegerField(default=1)
    max_per_day = models.PositiveIntegerField(default=1)
    delay_seconds = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.title


class RewardTransaction(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Source(models.TextChoices):
        SIGNUP = "signup", "Signup"
        REFERRAL = "referral", "Referral"
        LEAD_CONVERSION = "lead_conversion", "Lead Conversion"
        DAILY_LOGIN = "daily_login", "Daily Login"
        COIN_REDEMPTION = "coin_redemption", "Coin Redemption"
        SCRATCH_CARD = "scratch_card", "Scratch Card"
        SPIN_WHEEL = "spin_wheel", "Spin Wheel"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    coin_account = models.ForeignKey(RewardCoin, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reward_transactions")
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    source = models.CharField(max_length=30, choices=Source.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True)
    coins = models.IntegerField(default=0)
    cash_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reference_id = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    dedupe_key = models.CharField(max_length=120, blank=True, default="", db_index=True)
    narration = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "source", "created_at"]),
            models.Index(fields=["coin_account", "created_at"]),
            models.Index(fields=["dedupe_key"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.source}:{self.coins}"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = uuid.uuid4()
        super().save(*args, **kwargs)


class ReferralEvent(models.Model):
    class Status(models.TextChoices):
        TRACKED = "tracked", "Tracked"
        QUALIFIED = "qualified", "Qualified"
        REWARDED = "rewarded", "Rewarded"

    code_used = models.CharField(max_length=24, db_index=True)
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_sent")
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_event")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRACKED, db_index=True)
    referrer_reward = models.ForeignKey(
        "rewards.RewardTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrer_referral_events",
    )
    invitee_reward = models.ForeignKey(
        "rewards.RewardTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitee_referral_events",
    )
    wallet_reward_reference = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    qualified_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["referrer", "status"]),
            models.Index(fields=["code_used", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.referrer_id}->{self.referred_user_id}:{self.status}"


class ScratchCard(models.Model):
    class RewardType(models.TextChoices):
        COINS = "coins", "Coins"
        CASHBACK = "cashback", "Cashback"
        BONUS = "bonus", "Bonus"

    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        REVEALED = "revealed", "Revealed"
        CLAIMED = "claimed", "Claimed"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scratch_cards")
    reward_transaction = models.ForeignKey(
        "rewards.RewardTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scratch_cards",
    )
    reference_id = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    title = models.CharField(max_length=120, default="Mystery Reward")
    reward_type = models.CharField(max_length=20, choices=RewardType.choices, default=RewardType.COINS)
    coin_amount = models.PositiveIntegerField(default=0)
    wallet_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LOCKED, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revealed_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.reference_id}:{self.status}"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = uuid.uuid4()
        super().save(*args, **kwargs)


class SpinRewardOption(models.Model):
    class RewardType(models.TextChoices):
        COINS = "coins", "Coins"
        CASHBACK = "cashback", "Cashback"
        BONUS = "bonus", "Bonus"
        SCRATCH = "scratch", "Scratch"

    label = models.CharField(max_length=120)
    reward_type = models.CharField(max_length=20, choices=RewardType.choices, default=RewardType.COINS)
    coin_amount = models.PositiveIntegerField(default=0)
    wallet_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    weight = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    daily_limit = models.PositiveIntegerField(default=0, help_text="0 means unlimited")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label", "id"]

    def __str__(self) -> str:
        return self.label


class ScratchPrizeOption(models.Model):
    class RewardType(models.TextChoices):
        COINS = "coins", "Coins"
        CASHBACK = "cashback", "Cashback"
        BONUS = "bonus", "Bonus"

    label = models.CharField(max_length=120)
    description = models.CharField(max_length=220, blank=True, default="")
    badge = models.CharField(max_length=40, blank=True, default="Demo preset")
    reward_type = models.CharField(max_length=20, choices=RewardType.choices, default=RewardType.COINS)
    coin_amount = models.PositiveIntegerField(default=0)
    wallet_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    weight = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label", "id"]

    def __str__(self) -> str:
        return self.label


class SpinHistory(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spin_history")
    option = models.ForeignKey(SpinRewardOption, on_delete=models.SET_NULL, null=True, blank=True, related_name="spin_history")
    reward_transaction = models.ForeignKey(
        "rewards.RewardTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="spin_history",
    )
    reference_id = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    reward_type = models.CharField(max_length=20, choices=SpinRewardOption.RewardType.choices, default=SpinRewardOption.RewardType.COINS)
    coins_awarded = models.PositiveIntegerField(default=0)
    wallet_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.reference_id}"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = uuid.uuid4()
        super().save(*args, **kwargs)
