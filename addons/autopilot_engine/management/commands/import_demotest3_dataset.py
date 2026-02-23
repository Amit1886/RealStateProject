from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone


@dataclass
class ImportStats:
    created_users: int = 0
    created_plans: int = 0
    created_subscriptions: int = 0
    upserted_parties: int = 0
    created_transactions: int = 0


def _to_decimal(val) -> Decimal:
    return Decimal(str(val))


class Command(BaseCommand):
    help = "Import demotest3 demo dataset into the local DB (safe, idempotent-ish)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write to DB (default is dry-run).")
        parser.add_argument("--branch-code", default="default")
        parser.add_argument("--dataset-path", default=str(Path("demo_outputs") / "demotest3_demo_dataset.json"))
        parser.add_argument("--create-admin", action="store_true", help="Also create demo admin email if missing (inactive by default).")

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        dataset_path = Path(options["dataset_path"])
        branch_code = options["branch_code"]
        create_admin = bool(options["create_admin"])

        if not dataset_path.exists():
            raise CommandError(f"Dataset not found: {dataset_path}")

        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
        creds = payload.get("credentials") or {}
        plans_payload = payload.get("plans") or {}

        stats = ImportStats()

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run (no DB changes). Use --apply to import data."))

        User = get_user_model()

        def log(msg: str):
            self.stdout.write(msg)

        with transaction.atomic():
            # Avoid triggering legacy Party post_save hook that builds an OfflineMessage
            # containing surrogate escape sequences (can break sqlite utf-8 encoding).
            party_signal_disconnected = False
            try:
                from khataapp.models import Party, auto_create_login_link

                post_save.disconnect(auto_create_login_link, sender=Party)
                party_signal_disconnected = True
            except Exception:
                party_signal_disconnected = False

            # 1) Demo user
            demo_email = creds.get("email") or "demotest3@gmail.com"
            demo_username = creds.get("username") or "Demotest3"
            demo_password = creds.get("password") or "Demo@123"

            demo_user = User.objects.filter(email__iexact=demo_email).first()
            if demo_user is None:
                log(f"- create user: {demo_email}")
                if apply:
                    stats.created_users += 1
                    demo_user = User.objects.create_user(
                        email=demo_email,
                        username=demo_username,
                        mobile="9000000003",
                        password=demo_password,
                        is_active=True,
                    )
            else:
                log(f"- user exists: {demo_email}")

            # Optional: create demo admin user entry (no password changes unless created now).
            admin_email = creds.get("admin_email")
            if create_admin and admin_email:
                admin_user = User.objects.filter(email__iexact=admin_email).first()
                if admin_user is None:
                    log(f"- create demo admin email: {admin_email}")
                    if apply:
                        stats.created_users += 1
                        User.objects.create_user(
                            email=admin_email,
                            username="DemoAdmin",
                            mobile="9000000009",
                            password="Admin@123",
                            is_active=True,
                            is_staff=True,
                            is_superuser=False,
                        )

            # 2) Plans + active subscription (best-effort)
            if demo_user and plans_payload:
                try:
                    from billing.models import Plan, Subscription

                    plan_specs = []
                    for key in ("free", "basic", "premium"):
                        p = plans_payload.get(key) or {}
                        if p.get("name"):
                            plan_specs.append((p["name"], _to_decimal(p.get("monthly", "0.00"))))

                    active_plan_name = plans_payload.get("active_plan")
                    active_plan_obj = None

                    for name, monthly in plan_specs:
                        log(f"- upsert plan: {name}")
                        is_new = not Plan.objects.filter(name__iexact=name).exists()
                        if apply:
                            if is_new:
                                stats.created_plans += 1
                            plan, _ = Plan.objects.update_or_create(
                                name=name,
                                defaults={
                                    "price": monthly,
                                    "price_monthly": monthly,
                                    "active": True,
                                },
                            )
                        else:
                            plan = Plan.objects.filter(name__iexact=name).first()

                        if active_plan_name and name.lower() == str(active_plan_name).lower():
                            active_plan_obj = plan

                    if apply and demo_user and active_plan_obj:
                        sub = Subscription.objects.filter(user=demo_user, status="active").first()
                        if sub is None:
                            stats.created_subscriptions += 1
                            Subscription.objects.create(
                                user=demo_user,
                                plan=active_plan_obj,
                                status="active",
                                start_date=timezone.now(),
                                end_date=None,
                                auto_renew=False,
                            )
                            log(f"- subscription activated: {active_plan_obj.name}")
                except Exception as exc:
                    log(f"- skip plans/subscription (billing not ready): {exc}")

            # 3) Parties
            party_map: Dict[str, int] = {}
            try:
                from khataapp.models import Party
            except Exception as exc:
                raise CommandError(f"khataapp Party model not available: {exc}")

            parties: List[Dict] = payload.get("parties") or []
            for item in parties:
                name = (item.get("name") or "").strip()
                ptype = (item.get("type") or "").strip().lower()
                if not name or ptype not in {"customer", "supplier"}:
                    continue

                log(f"- upsert party: {name} ({ptype})")
                if apply:
                    stats.upserted_parties += 1
                    obj, _ = Party.objects.update_or_create(
                        owner=demo_user,
                        name=name,
                        party_type=ptype,
                        defaults={
                            "mobile": item.get("mobile", "") or "",
                            "upi_id": item.get("upi_id"),
                            "bank_account_number": item.get("bank_account"),
                            "whatsapp_number": item.get("whatsapp"),
                            "sms_number": item.get("sms"),
                            "is_premium": bool(item.get("premium", False)),
                            "credit_grade": item.get("credit_grade", "-") or "-",
                            "is_active": True,
                        },
                    )
                    party_map[name] = obj.id
                else:
                    obj = Party.objects.filter(owner=demo_user, name=name, party_type=ptype).first()
                    if obj:
                        party_map[name] = obj.id

            # 4) Transactions (bulk create to avoid side effects from legacy signals)
            try:
                from khataapp.models import Transaction as KhataTransaction
            except Exception as exc:
                raise CommandError(f"khataapp Transaction model not available: {exc}")

            txs: List[Dict] = payload.get("transactions") or []
            to_create = []
            for t in txs:
                party_name = t.get("party")
                if not party_name or party_name not in party_map:
                    continue
                txn_type = (t.get("type") or "").strip().lower()
                txn_mode = (t.get("mode") or "cash").strip().lower()
                amt = _to_decimal(t.get("amount", "0.00"))
                dt_raw = (t.get("date") or "").strip()
                try:
                    dt = datetime.date.fromisoformat(dt_raw)
                except ValueError:
                    continue
                notes = t.get("notes")

                if txn_type not in {"credit", "debit"}:
                    continue

                if apply:
                    party = Party.objects.get(id=party_map[party_name])
                    exists = KhataTransaction.objects.filter(
                        party=party,
                        txn_type=txn_type,
                        txn_mode=txn_mode,
                        amount=amt,
                        date=dt,
                        notes=notes,
                    ).exists()
                    if exists:
                        continue
                    to_create.append(
                        KhataTransaction(
                            party=party,
                            txn_type=txn_type,
                            txn_mode=txn_mode,
                            amount=amt,
                            date=dt,
                            notes=notes,
                        )
                    )

            if apply and to_create:
                KhataTransaction.objects.bulk_create(to_create, batch_size=200)
                stats.created_transactions += len(to_create)
                log(f"- transactions created: {len(to_create)}")
            elif apply:
                log("- transactions created: 0")

            if not apply:
                # ensure no writes accidentally happen
                transaction.set_rollback(True)
                log("- dry-run complete (rolled back).")
                return
            if party_signal_disconnected:
                try:
                    from khataapp.models import Party, auto_create_login_link

                    post_save.connect(auto_create_login_link, sender=Party)
                except Exception:
                    pass

        log("Done.")
