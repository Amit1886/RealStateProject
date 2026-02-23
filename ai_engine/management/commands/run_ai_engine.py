from __future__ import annotations

from django.core.management.base import BaseCommand

from ai_engine.services.credit_risk_engine import calculate_credit_risk_scores
from ai_engine.services.forecast_engine import generate_demand_forecast
from ai_engine.services.runner import run_all_ai_engines
from ai_engine.services.salesman_performance_engine import calculate_salesman_scores


class Command(BaseCommand):
    help = "Run AI engines safely in background/cron without affecting billing flow."

    def add_arguments(self, parser):
        parser.add_argument(
            "--engine",
            choices=["all", "forecast", "credit-risk", "salesman-score"],
            default="all",
            help="Which AI engine to run.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Forecast horizon in days (used for forecast engine).",
        )
        parser.add_argument(
            "--months",
            type=int,
            default=6,
            help="Sales history months to read (used for forecast engine).",
        )

    def handle(self, *args, **options):
        engine = options["engine"]

        if engine == "forecast":
            result = generate_demand_forecast(days=options["days"], months=options["months"])
        elif engine == "credit-risk":
            result = calculate_credit_risk_scores()
        elif engine == "salesman-score":
            result = calculate_salesman_scores()
        else:
            result = run_all_ai_engines()

        self.stdout.write(self.style.SUCCESS(f"AI Engine Result: {result}"))
