from __future__ import annotations

from django.core.management.base import BaseCommand

from addons.autopilot_engine.models import WorkflowAction, WorkflowRule


class Command(BaseCommand):
    help = "Install safe default Autopilot rules (addons-only, backward compatible)."

    def add_arguments(self, parser):
        parser.add_argument("--branch-code", default="default")
        parser.add_argument("--apply", action="store_true", help="Actually create/update rules (default is dry-run).")
        parser.add_argument("--with-courier", action="store_true", help="Also install courier booking rule (requires courier addon).")

    def handle(self, *args, **options):
        branch_code = options["branch_code"]
        apply = bool(options["apply"])
        with_courier = bool(options["with_courier"])

        defaults = [
            {
                "name": "Storefront order paid -> sync to billing (safe adapter)",
                "event_key": "storefront_order_paid",
                "priority": 100,
                "conditions": {},
                "actions": [
                    {"action_key": "ecommerce_sync_to_billing", "run_order": 10, "critical": False, "params": {}},
                ],
            }
        ]

        if with_courier:
            defaults.append(
                {
                    "name": "Storefront order paid -> create courier shipment (addon)",
                    "event_key": "storefront_order_paid",
                    "priority": 110,
                    "conditions": {},
                    "actions": [
                        {
                            "action_key": "assign_courier",
                            "run_order": 10,
                            "critical": False,
                            "params": {"provider": "shiprocket", "use_addon": True, "ref_type": "storefront_order"},
                        }
                    ],
                }
            )

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run (no DB changes). Use --apply to write rules."))

        for spec in defaults:
            self.stdout.write(f"- {spec['event_key']} -> {spec['name']}")
            if not apply:
                continue

            rule, _ = WorkflowRule.objects.update_or_create(
                branch_code=branch_code,
                event_key=spec["event_key"],
                name=spec["name"],
                defaults={
                    "priority": spec["priority"],
                    "conditions": spec["conditions"],
                    "is_active": True,
                },
            )

            # Replace actions for idempotency.
            rule.actions.all().delete()
            for action in spec["actions"]:
                WorkflowAction.objects.create(
                    rule=rule,
                    action_key=action["action_key"],
                    run_order=action["run_order"],
                    critical=action.get("critical", False),
                    params=action.get("params", {}),
                )

        if apply:
            self.stdout.write(self.style.SUCCESS("Default rules installed/updated."))
