from __future__ import annotations

import random
from urllib.parse import quote, quote_plus
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from wallet.models import WalletTransaction
from wallet.services import credit_wallet

from .models import ReferralEvent, Reward, RewardCoin, RewardRule, RewardTransaction, ScratchCard, ScratchPrizeOption, SpinHistory, SpinRewardOption


DEFAULT_REWARD_RULES = [
    {
        "key": RewardRule.Key.SIGNUP_BONUS,
        "title": "Signup Bonus",
        "reward_type": RewardRule.RewardType.COINS,
        "coin_amount": 100,
        "wallet_amount": Decimal("0.00"),
        "spin_count": 1,
        "scratch_cards_count": 1,
        "max_per_user": 1,
        "max_per_day": 1,
    },
    {
        "key": RewardRule.Key.REFERRAL_REFERRER,
        "title": "Referral Reward For Referrer",
        "reward_type": RewardRule.RewardType.CASHBACK,
        "coin_amount": 150,
        "wallet_amount": Decimal("50.00"),
        "spin_count": 1,
        "scratch_cards_count": 0,
        "max_per_user": 1000,
        "max_per_day": 50,
    },
    {
        "key": RewardRule.Key.REFERRAL_INVITEE,
        "title": "Referral Welcome Reward",
        "reward_type": RewardRule.RewardType.COINS,
        "coin_amount": 75,
        "wallet_amount": Decimal("0.00"),
        "spin_count": 1,
        "scratch_cards_count": 0,
        "max_per_user": 1,
        "max_per_day": 10,
    },
    {
        "key": RewardRule.Key.DAILY_LOGIN,
        "title": "Daily Login Reward",
        "reward_type": RewardRule.RewardType.SPIN,
        "coin_amount": 10,
        "wallet_amount": Decimal("0.00"),
        "spin_count": 1,
        "scratch_cards_count": 0,
        "max_per_user": 5000,
        "max_per_day": 1,
    },
    {
        "key": RewardRule.Key.LEAD_CONVERSION,
        "title": "Lead Conversion Cashback",
        "reward_type": RewardRule.RewardType.CASHBACK,
        "coin_amount": 50,
        "wallet_amount": Decimal("100.00"),
        "spin_count": 1,
        "scratch_cards_count": 1,
        "max_per_user": 5000,
        "max_per_day": 100,
    },
    {
        "key": RewardRule.Key.COIN_TO_WALLET,
        "title": "Coin Conversion Rule",
        "reward_type": RewardRule.RewardType.CASHBACK,
        "coin_amount": 100,
        "wallet_amount": Decimal("1.00"),
        "spin_count": 0,
        "scratch_cards_count": 0,
        "max_per_user": 0,
        "max_per_day": 0,
    },
]

DEFAULT_SPIN_OPTIONS = [
    {"label": "10 Coins", "reward_type": SpinRewardOption.RewardType.COINS, "coin_amount": 10, "wallet_amount": Decimal("0.00"), "weight": 35},
    {"label": "25 Coins", "reward_type": SpinRewardOption.RewardType.COINS, "coin_amount": 25, "wallet_amount": Decimal("0.00"), "weight": 20},
    {"label": "Rs 10 Cashback", "reward_type": SpinRewardOption.RewardType.CASHBACK, "coin_amount": 0, "wallet_amount": Decimal("10.00"), "weight": 18},
    {"label": "Scratch Card", "reward_type": SpinRewardOption.RewardType.SCRATCH, "coin_amount": 0, "wallet_amount": Decimal("0.00"), "weight": 12},
    {"label": "50 Coins", "reward_type": SpinRewardOption.RewardType.COINS, "coin_amount": 50, "wallet_amount": Decimal("0.00"), "weight": 10},
    {"label": "Rs 25 Cashback", "reward_type": SpinRewardOption.RewardType.CASHBACK, "coin_amount": 0, "wallet_amount": Decimal("25.00"), "weight": 5},
]

DEFAULT_SCRATCH_PRIZE_OPTIONS = [
    {"label": "Top Prize", "description": "10% extra payout on next lead or deal", "reward_type": ScratchPrizeOption.RewardType.BONUS, "coin_amount": 100, "wallet_amount": Decimal("0.00"), "weight": 5},
    {"label": "100 Coins", "description": "Reward coins for your wallet", "reward_type": ScratchPrizeOption.RewardType.COINS, "coin_amount": 100, "wallet_amount": Decimal("0.00"), "weight": 15},
    {"label": "50 Coins", "description": "Small bonus coins for activity", "reward_type": ScratchPrizeOption.RewardType.COINS, "coin_amount": 50, "wallet_amount": Decimal("0.00"), "weight": 30},
    {"label": "Rs 25 Cashback", "description": "Cashback credited to wallet", "reward_type": ScratchPrizeOption.RewardType.CASHBACK, "coin_amount": 0, "wallet_amount": Decimal("25.00"), "weight": 20},
    {"label": "Rs 10 Cashback", "description": "Fast wallet cashback reward", "reward_type": ScratchPrizeOption.RewardType.CASHBACK, "coin_amount": 0, "wallet_amount": Decimal("10.00"), "weight": 30},
]


def get_or_create_reward_coin(user) -> RewardCoin:
    account, _ = RewardCoin.objects.get_or_create(user=user)
    return account


def ensure_default_reward_rules():
    for rule in DEFAULT_REWARD_RULES:
        RewardRule.objects.update_or_create(
            key=rule["key"],
            defaults={
                "title": rule["title"],
                "reward_type": rule["reward_type"],
                "coin_amount": rule["coin_amount"],
                "wallet_amount": rule["wallet_amount"],
                "spin_count": rule["spin_count"],
                "scratch_cards_count": rule["scratch_cards_count"],
                "max_per_user": rule["max_per_user"],
                "max_per_day": rule["max_per_day"],
                "is_active": True,
            },
        )
    for option in DEFAULT_SPIN_OPTIONS:
        SpinRewardOption.objects.get_or_create(
            label=option["label"],
            defaults={
                "reward_type": option["reward_type"],
                "coin_amount": option["coin_amount"],
                "wallet_amount": option["wallet_amount"],
                "weight": option["weight"],
                "is_active": True,
            },
        )


def ensure_default_scratch_prizes():
    for option in DEFAULT_SCRATCH_PRIZE_OPTIONS:
        ScratchPrizeOption.objects.update_or_create(
            label=option["label"],
            defaults={
                "description": option.get("description", ""),
                "badge": option.get("badge", "Demo preset"),
                "reward_type": option["reward_type"],
                "coin_amount": option["coin_amount"],
                "wallet_amount": option["wallet_amount"],
                "weight": option["weight"],
                "is_active": True,
            },
        )


def evaluate_rewards_for_agent(agent):
    perf = agent.performance or {}
    closed_leads = int(perf.get("closed_leads", 0))
    revenue = Decimal(str(perf.get("revenue", 0)))

    if closed_leads >= 10:
        Reward.objects.get_or_create(
            agent=agent,
            type=Reward.Type.CERTIFICATE,
            condition="10 closed leads",
            defaults={"title": "Consistency Certificate", "achieved": True},
        )

    if closed_leads >= 25 or revenue >= Decimal("50000"):
        Reward.objects.get_or_create(
            agent=agent,
            type=Reward.Type.BONUS,
            condition="25 closed leads or Rs 50k revenue",
            defaults={"title": "High Performer Bonus", "achieved": True},
        )


def _reward_count_for_rule(user, rule: RewardRule):
    queryset = RewardTransaction.objects.filter(user=user, source=_rule_source(rule))
    total_count = queryset.count()
    daily_count = queryset.filter(created_at__date=timezone.localdate()).count()
    return total_count, daily_count


def _rule_source(rule: RewardRule) -> str:
    mapping = {
        RewardRule.Key.SIGNUP_BONUS: RewardTransaction.Source.SIGNUP,
        RewardRule.Key.REFERRAL_REFERRER: RewardTransaction.Source.REFERRAL,
        RewardRule.Key.REFERRAL_INVITEE: RewardTransaction.Source.REFERRAL,
        RewardRule.Key.DAILY_LOGIN: RewardTransaction.Source.DAILY_LOGIN,
        RewardRule.Key.LEAD_CONVERSION: RewardTransaction.Source.LEAD_CONVERSION,
        RewardRule.Key.COIN_TO_WALLET: RewardTransaction.Source.COIN_REDEMPTION,
    }
    return mapping.get(rule.key, RewardTransaction.Source.MANUAL)


def _build_scratch_payload():
    ensure_default_scratch_prizes()
    reward_buckets = list(ScratchPrizeOption.objects.filter(is_active=True).order_by("weight", "id"))
    if not reward_buckets:
        reward_buckets = [
            ScratchPrizeOption(label=row["label"], reward_type=row["reward_type"], coin_amount=row["coin_amount"], wallet_amount=row["wallet_amount"], weight=row["weight"])
            for row in DEFAULT_SCRATCH_PRIZE_OPTIONS
        ]
    option = random.choices(reward_buckets, weights=[max(1, row.weight) for row in reward_buckets], k=1)[0]
    return {
        "reward_type": option.reward_type,
        "coin_amount": option.coin_amount,
        "wallet_amount": option.wallet_amount,
        "title": option.label,
        "description": option.description or option.metadata.get("description", ""),
        "badge": option.badge or option.metadata.get("badge", "Live prize"),
        "option_id": getattr(option, "id", None),
    }


def issue_scratch_cards(user, count: int = 1, *, metadata=None):
    coin_account = get_or_create_reward_coin(user)
    cards = []
    for _ in range(max(0, int(count or 0))):
        payload = _build_scratch_payload()
        cards.append(
            ScratchCard.objects.create(
                user=user,
                title=payload["title"],
                reward_type=payload["reward_type"],
                coin_amount=payload["coin_amount"],
                wallet_amount=payload["wallet_amount"],
                status=ScratchCard.Status.LOCKED,
                expires_at=timezone.now() + timedelta(days=14),
                metadata={
                    **(metadata or {}),
                    **({"scratch_prize_option_id": payload["option_id"]} if payload.get("option_id") else {}),
                    **({"scratch_prize_description": payload["description"]} if payload.get("description") else {}),
                    **({"scratch_prize_badge": payload["badge"]} if payload.get("badge") else {}),
                },
            )
        )
    if cards:
        coin_account.available_scratch_cards = coin_account.available_scratch_cards + len(cards)
        coin_account.save(update_fields=["available_scratch_cards", "updated_at"])
    return cards


@transaction.atomic
def _create_reward_transaction(
    user,
    *,
    entry_type: str,
    source: str,
    coins: int = 0,
    cash_value: Decimal = Decimal("0.00"),
    dedupe_key: str = "",
    narration: str = "",
    metadata=None,
):
    coin_account = RewardCoin.objects.select_for_update().get(pk=get_or_create_reward_coin(user).pk)
    if dedupe_key:
        existing = RewardTransaction.objects.filter(user=user, dedupe_key=dedupe_key, status=RewardTransaction.Status.SUCCESS).first()
        if existing:
            return coin_account, existing
    if entry_type == RewardTransaction.EntryType.DEBIT and coin_account.balance < abs(int(coins)):
        raise ValueError("Insufficient reward coins")
    if entry_type == RewardTransaction.EntryType.CREDIT:
        coin_account.balance = coin_account.balance + max(0, int(coins))
        coin_account.lifetime_earned = coin_account.lifetime_earned + max(0, int(coins))
    else:
        coin_account.balance = coin_account.balance - abs(int(coins))
        coin_account.lifetime_redeemed = coin_account.lifetime_redeemed + abs(int(coins))
    coin_account.save(update_fields=["balance", "lifetime_earned", "lifetime_redeemed", "updated_at"])
    reward_txn = RewardTransaction.objects.create(
        coin_account=coin_account,
        user=user,
        entry_type=entry_type,
        source=source,
        status=RewardTransaction.Status.SUCCESS,
        coins=coins,
        cash_value=cash_value,
        dedupe_key=dedupe_key[:120],
        narration=narration[:255],
        metadata=metadata or {},
    )
    return coin_account, reward_txn


def _apply_rule(
    user,
    rule: RewardRule,
    *,
    dedupe_key: str,
    narration: str,
    metadata=None,
):
    if not rule.is_active:
        return None
    total_count, daily_count = _reward_count_for_rule(user, rule)
    if rule.max_per_user and total_count >= rule.max_per_user:
        return None
    if rule.max_per_day and daily_count >= rule.max_per_day:
        return None
    coin_account, reward_txn = _create_reward_transaction(
        user,
        entry_type=RewardTransaction.EntryType.CREDIT,
        source=_rule_source(rule),
        coins=rule.coin_amount,
        cash_value=rule.wallet_amount,
        dedupe_key=dedupe_key,
        narration=narration,
        metadata=metadata,
    )
    updates = {}
    if rule.spin_count:
        coin_account.available_spins = coin_account.available_spins + rule.spin_count
        updates["available_spins"] = coin_account.available_spins
    if rule.scratch_cards_count:
        issue_scratch_cards(user, count=rule.scratch_cards_count, metadata={"rule": rule.key, **(metadata or {})})
    if updates:
        coin_account.save(update_fields=[*updates.keys(), "updated_at"])
    wallet_reference = None
    if rule.wallet_amount and rule.wallet_amount > Decimal("0.00"):
        _, wallet_txn = credit_wallet(
            user,
            rule.wallet_amount,
            source=WalletTransaction.Source.CASHBACK if rule.reward_type == RewardRule.RewardType.CASHBACK else WalletTransaction.Source.REWARD,
            reference=rule.key,
            idempotency_key=f"reward-wallet:{dedupe_key}",
            metadata={"reward_transaction_id": reward_txn.id, "rule": rule.key, **(metadata or {})},
            narration=narration,
            actor=user,
        )
        wallet_reference = wallet_txn.reference_id
        reward_txn.metadata = {**(reward_txn.metadata or {}), "wallet_reference_id": str(wallet_reference)}
        reward_txn.save(update_fields=["metadata"])
    return {"coin_account": coin_account, "reward_transaction": reward_txn, "wallet_reference": wallet_reference}


def award_signup_bonus(user):
    rule = RewardRule.objects.filter(key=RewardRule.Key.SIGNUP_BONUS).first()
    if not rule or not user.is_active:
        return None
    return _apply_rule(
        user,
        rule,
        dedupe_key=f"signup:{user.pk}",
        narration="Signup bonus credited",
        metadata={"event": "signup_bonus"},
    )


def process_referral_for_user(user):
    if not user.is_active or not user.referred_by_id:
        return None
    referrer = user.referred_by
    referrer_id = getattr(referrer, "id", None)
    if not referrer_id:
        return None
    referral_event, _ = ReferralEvent.objects.get_or_create(
        referred_user=user,
        defaults={
            "referrer": referrer,
            "code_used": referrer.referral_code or "",
            "status": ReferralEvent.Status.TRACKED,
            "metadata": {"event": "signup_referral"},
        },
    )
    if referral_event.status == ReferralEvent.Status.REWARDED:
        return referral_event
    referral_event.status = ReferralEvent.Status.QUALIFIED
    referral_event.qualified_at = referral_event.qualified_at or timezone.now()

    referrer_rule = RewardRule.objects.filter(key=RewardRule.Key.REFERRAL_REFERRER).first()
    invitee_rule = RewardRule.objects.filter(key=RewardRule.Key.REFERRAL_INVITEE).first()
    referrer_reward = (
        _apply_rule(
            referrer,
            referrer_rule,
            dedupe_key=f"referral:referrer:{user.pk}",
            narration=f"Referral reward for inviting {user.email}",
            metadata={"referred_user_id": user.pk},
        )
        if referrer_rule
        else None
    )
    invitee_reward = (
        _apply_rule(
            user,
            invitee_rule,
            dedupe_key=f"referral:invitee:{user.pk}",
            narration="Referral welcome reward",
            metadata={"referrer_id": referrer_id},
        )
        if invitee_rule
        else None
    )
    referral_event.referrer_reward = referrer_reward["reward_transaction"] if referrer_reward else None
    referral_event.invitee_reward = invitee_reward["reward_transaction"] if invitee_reward else None
    referral_event.wallet_reward_reference = referrer_reward["wallet_reference"] if referrer_reward else None
    referral_event.status = ReferralEvent.Status.REWARDED
    referral_event.rewarded_at = timezone.now()
    referral_event.save(
        update_fields=[
            "status",
            "qualified_at",
            "rewarded_at",
            "referrer_reward",
            "invitee_reward",
            "wallet_reward_reference",
        ]
    )
    return referral_event


@transaction.atomic
def award_daily_login_reward(user):
    coin_account = get_or_create_reward_coin(user)
    today = timezone.localdate()
    if coin_account.last_daily_login_at and timezone.localtime(coin_account.last_daily_login_at).date() == today:
        return None
    rule = RewardRule.objects.filter(key=RewardRule.Key.DAILY_LOGIN).first()
    result = (
        _apply_rule(
            user,
            rule,
            dedupe_key=f"daily-login:{user.pk}:{today.isoformat()}",
            narration="Daily login reward",
            metadata={"event_date": today.isoformat()},
        )
        if rule
        else None
    )
    coin_account.last_daily_login_at = timezone.now()
    coin_account.save(update_fields=["last_daily_login_at", "updated_at"])
    return result


def award_lead_conversion_reward(lead):
    agent = getattr(lead, "assigned_agent", None)
    if not agent or not getattr(agent, "user", None):
        return None
    rule = RewardRule.objects.filter(key=RewardRule.Key.LEAD_CONVERSION).first()
    if not rule:
        return None
    return _apply_rule(
        agent.user,
        rule,
        dedupe_key=f"lead-conversion:{lead.pk}:{agent.user_id}",
        narration=f"Lead conversion reward for lead #{lead.pk}",
        metadata={"lead_id": lead.pk},
    )


@transaction.atomic
def convert_coins_to_wallet(user, coins: int):
    coins = int(coins or 0)
    if coins <= 0:
        raise ValueError("Coins must be greater than zero")
    rule = RewardRule.objects.filter(key=RewardRule.Key.COIN_TO_WALLET).first()
    if not rule or rule.coin_amount <= 0 or rule.wallet_amount <= Decimal("0.00"):
        raise ValueError("Coin conversion rule is not configured")
    if coins < rule.coin_amount:
        raise ValueError(f"Minimum {rule.coin_amount} coins required")
    if coins % rule.coin_amount != 0:
        raise ValueError(f"Coins must be in multiples of {rule.coin_amount}")
    multiplier = Decimal(coins) / Decimal(rule.coin_amount)
    wallet_amount = (multiplier * rule.wallet_amount).quantize(Decimal("0.01"))
    _, reward_txn = _create_reward_transaction(
        user,
        entry_type=RewardTransaction.EntryType.DEBIT,
        source=RewardTransaction.Source.COIN_REDEMPTION,
        coins=-coins,
        cash_value=wallet_amount,
        dedupe_key=f"coin-redemption:{user.pk}:{timezone.now().timestamp()}",
        narration=f"Converted {coins} coins to wallet",
        metadata={"coins": coins},
    )
    _, wallet_txn = credit_wallet(
        user,
        wallet_amount,
        source=WalletTransaction.Source.COIN_REDEMPTION,
        reference=str(reward_txn.reference_id),
        idempotency_key=f"coin-wallet:{reward_txn.reference_id}",
        metadata={"reward_transaction_id": reward_txn.id},
        narration="Reward coin conversion",
        actor=user,
    )
    reward_txn.metadata = {"wallet_reference_id": str(wallet_txn.reference_id), "coins": coins}
    reward_txn.save(update_fields=["metadata"])
    return reward_txn, wallet_txn


def reveal_scratch_card(user, card: ScratchCard):
    if card.user_id != user.id:
        raise ValueError("Scratch card does not belong to this user")
    if card.status != ScratchCard.Status.LOCKED:
        return card
    if card.expires_at and card.expires_at <= timezone.now():
        card.status = ScratchCard.Status.EXPIRED
        card.save(update_fields=["status"])
        raise ValueError("Scratch card has expired")
    card.status = ScratchCard.Status.REVEALED
    card.revealed_at = timezone.now()
    card.save(update_fields=["status", "revealed_at"])
    return card


@transaction.atomic
def claim_scratch_card(user, card: ScratchCard):
    if card.user_id != user.id:
        raise ValueError("Scratch card does not belong to this user")
    if card.status == ScratchCard.Status.CLAIMED:
        return card
    if card.status == ScratchCard.Status.LOCKED:
        raise ValueError("Reveal scratch card first")
    if card.status == ScratchCard.Status.EXPIRED:
        raise ValueError("Scratch card has expired")

    reward_txn = None
    if card.reward_type == ScratchCard.RewardType.COINS and card.coin_amount:
        _, reward_txn = _create_reward_transaction(
            user,
            entry_type=RewardTransaction.EntryType.CREDIT,
            source=RewardTransaction.Source.SCRATCH_CARD,
            coins=card.coin_amount,
            cash_value=Decimal("0.00"),
            dedupe_key=f"scratch:{card.reference_id}",
            narration=f"Scratch reward {card.title}",
            metadata={"scratch_card_id": card.id},
        )
    elif card.reward_type in {ScratchCard.RewardType.CASHBACK, ScratchCard.RewardType.BONUS} and card.wallet_amount:
        _, reward_txn = _create_reward_transaction(
            user,
            entry_type=RewardTransaction.EntryType.CREDIT,
            source=RewardTransaction.Source.SCRATCH_CARD,
            coins=0,
            cash_value=card.wallet_amount,
            dedupe_key=f"scratch:{card.reference_id}",
            narration=f"Scratch reward {card.title}",
            metadata={"scratch_card_id": card.id},
        )
        _, wallet_txn = credit_wallet(
            user,
            card.wallet_amount,
            source=WalletTransaction.Source.CASHBACK,
            reference=str(card.reference_id),
            idempotency_key=f"scratch-wallet:{card.reference_id}",
            metadata={"scratch_card_id": card.id},
            narration=f"Scratch reward {card.title}",
            actor=user,
        )
        reward_txn.metadata = {"wallet_reference_id": str(wallet_txn.reference_id)}
        reward_txn.save(update_fields=["metadata"])

    card.status = ScratchCard.Status.CLAIMED
    card.claimed_at = timezone.now()
    card.reward_transaction = reward_txn
    card.save(update_fields=["status", "claimed_at", "reward_transaction"])
    coin_account = get_or_create_reward_coin(user)
    if coin_account.available_scratch_cards:
        coin_account.available_scratch_cards = max(0, coin_account.available_scratch_cards - 1)
        coin_account.save(update_fields=["available_scratch_cards", "updated_at"])
    return card


@transaction.atomic
def spin_wheel(user):
    coin_account = RewardCoin.objects.select_for_update().get(pk=get_or_create_reward_coin(user).pk)
    if coin_account.available_spins <= 0:
        raise ValueError("No spin chances available")
    options = list(SpinRewardOption.objects.filter(is_active=True))
    if not options:
        raise ValueError("Spin options are not configured")
    coin_account.available_spins = coin_account.available_spins - 1
    coin_account.save(update_fields=["available_spins", "updated_at"])

    option = random.choices(options, weights=[max(1, row.weight) for row in options], k=1)[0]
    reward_txn = None
    if option.reward_type == SpinRewardOption.RewardType.COINS and option.coin_amount:
        _, reward_txn = _create_reward_transaction(
            user,
            entry_type=RewardTransaction.EntryType.CREDIT,
            source=RewardTransaction.Source.SPIN_WHEEL,
            coins=option.coin_amount,
            cash_value=Decimal("0.00"),
            dedupe_key=f"spin:{user.pk}:{timezone.now().timestamp()}",
            narration=f"Spin reward {option.label}",
            metadata={"spin_option_id": option.id},
        )
    elif option.reward_type in {SpinRewardOption.RewardType.CASHBACK, SpinRewardOption.RewardType.BONUS} and option.wallet_amount:
        _, reward_txn = _create_reward_transaction(
            user,
            entry_type=RewardTransaction.EntryType.CREDIT,
            source=RewardTransaction.Source.SPIN_WHEEL,
            coins=0,
            cash_value=option.wallet_amount,
            dedupe_key=f"spin:{user.pk}:{timezone.now().timestamp()}",
            narration=f"Spin reward {option.label}",
            metadata={"spin_option_id": option.id},
        )
        _, wallet_txn = credit_wallet(
            user,
            option.wallet_amount,
            source=WalletTransaction.Source.CASHBACK,
            reference=option.label,
            idempotency_key=f"spin-wallet:{reward_txn.reference_id}",
            metadata={"spin_option_id": option.id},
            narration=f"Spin reward {option.label}",
            actor=user,
        )
        reward_txn.metadata = {"wallet_reference_id": str(wallet_txn.reference_id), "spin_option_id": option.id}
        reward_txn.save(update_fields=["metadata"])
    elif option.reward_type == SpinRewardOption.RewardType.SCRATCH:
        issue_scratch_cards(user, count=1, metadata={"spin_option_id": option.id})

    spin_history = SpinHistory.objects.create(
        user=user,
        option=option,
        reward_transaction=reward_txn,
        reward_type=option.reward_type,
        coins_awarded=option.coin_amount,
        wallet_amount=option.wallet_amount,
        status=SpinHistory.Status.SUCCESS,
        metadata={"label": option.label},
    )
    return spin_history


def build_referral_share_context(user, *, base_url=None):
    base_url = (base_url or getattr(settings, "BASE_URL", "") or "http://127.0.0.1:9000").rstrip("/")
    referral_code = getattr(user, "referral_code", "") or ""
    referral_link = f"{base_url}/accounts/signup/?ref={referral_code}" if referral_code else f"{base_url}/accounts/signup/"
    message = f"Join & earn rewards -> {referral_link}"
    return {
        "referral_code": referral_code,
        "referral_link": referral_link,
        "message": message,
        "share_links": {
            "whatsapp": f"https://wa.me/?text={quote_plus(message)}",
            "email": f"mailto:?subject={quote('Join & Earn')}&body={quote(message)}",
            "sms": f"sms:?body={quote(message)}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={quote(referral_link)}",
            "instagram": referral_link,
        },
    }
