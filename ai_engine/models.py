from django.db import models


class AIQueryLog(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    question = models.TextField()
    answer = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DemandForecast(models.Model):
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="forecasts")
    forecast_date = models.DateField(db_index=True)
    predicted_qty = models.DecimalField(max_digits=12, decimal_places=2)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    model_version = models.CharField(max_length=40, default="baseline-v1")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "forecast_date", "model_version")


class ProductDemandForecast(models.Model):
    """
    Backward-compatible V2 forecast table.
    Keeps existing DemandForecast untouched.
    """

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="ai_demand_forecasts",
    )
    predicted_date = models.DateField(db_index=True)
    predicted_quantity = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "predicted_date")
        indexes = [models.Index(fields=["predicted_date"])]
        ordering = ["predicted_date", "product_id"]

    def __str__(self):
        return f"{self.product_id} - {self.predicted_date} - {self.predicted_quantity}"


class CustomerRiskScore(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "Low", "Low"
        MEDIUM = "Medium", "Medium"
        HIGH = "High", "High"

    customer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="ai_risk_scores",
    )
    risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW)
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer",)
        ordering = ["-risk_score", "-last_calculated"]

    def __str__(self):
        return f"{self.customer_id} - {self.risk_score} ({self.risk_level})"


class SalesmanScore(models.Model):
    salesman = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="ai_salesman_scores",
    )
    performance_score = models.IntegerField(default=0)
    risk_flag = models.BooleanField(default=False)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("salesman",)
        ordering = ["-performance_score", "-calculated_at"]

    def __str__(self):
        return f"{self.salesman_id} - {self.performance_score}"
