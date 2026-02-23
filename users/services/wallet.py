from decimal import Decimal

from django.db import transaction

from users.models import UserProfileExt, WalletLedger


@transaction.atomic
def apply_wallet_entry(user, entry_type: str, amount: Decimal, source: str, reference: str = ""):
    profile, _ = UserProfileExt.objects.select_for_update().get_or_create(user=user)

    WalletLedger.objects.create(
        user=user,
        entry_type=entry_type,
        amount=amount,
        source=source,
        reference=reference,
    )

    if entry_type == WalletLedger.EntryType.CREDIT:
        profile.wallet_balance += amount
    else:
        profile.wallet_balance -= amount
    profile.save(update_fields=["wallet_balance", "updated_at"])
    return profile
