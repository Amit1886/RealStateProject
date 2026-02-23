from __future__ import annotations

import logging

from ai_engine.services.credit_risk_engine import calculate_credit_risk_scores
from ai_engine.services.forecast_engine import generate_demand_forecast
from ai_engine.services.salesman_performance_engine import calculate_salesman_scores

logger = logging.getLogger(__name__)


def run_all_ai_engines() -> dict:
    """
    Safe orchestrator for cron/celery.
    Any failure is isolated and never raises hard exception.
    """
    result = {
        "forecast": {"status": "skipped"},
        "credit_risk": {"status": "skipped"},
        "salesman_score": {"status": "skipped"},
    }
    try:
        result["forecast"] = generate_demand_forecast(days=7, months=6)
    except Exception as exc:
        logger.exception("Forecast engine failed in orchestrator: %s", exc)
        result["forecast"] = {"status": "error", "message": str(exc)}

    try:
        result["credit_risk"] = calculate_credit_risk_scores()
    except Exception as exc:
        logger.exception("Credit risk engine failed in orchestrator: %s", exc)
        result["credit_risk"] = {"status": "error", "message": str(exc)}

    try:
        result["salesman_score"] = calculate_salesman_scores()
    except Exception as exc:
        logger.exception("Salesman score engine failed in orchestrator: %s", exc)
        result["salesman_score"] = {"status": "error", "message": str(exc)}

    return result
