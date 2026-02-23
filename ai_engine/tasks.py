from __future__ import annotations

import logging

from celery import shared_task

from ai_engine.services.credit_risk_engine import calculate_credit_risk_scores
from ai_engine.services.forecast_engine import generate_demand_forecast
from ai_engine.services.runner import run_all_ai_engines
from ai_engine.services.salesman_performance_engine import calculate_salesman_scores

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=False)
def run_demand_forecast_task(self):
    logger.info("AI task started: demand forecast")
    return generate_demand_forecast(days=7, months=6)


@shared_task(bind=True, ignore_result=False)
def run_credit_risk_task(self):
    logger.info("AI task started: credit risk")
    return calculate_credit_risk_scores()


@shared_task(bind=True, ignore_result=False)
def run_salesman_score_task(self):
    logger.info("AI task started: salesman score")
    return calculate_salesman_scores()


@shared_task(bind=True, ignore_result=False)
def run_all_ai_engines_task(self):
    logger.info("AI task started: run all engines")
    return run_all_ai_engines()
