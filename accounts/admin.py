from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, UserProfile, DailySummary, BusinessSnapshot,
    ExpenseCategory, Expense, LoyaltyProgram, MembershipTier,
    LoyaltyPoints, PointsTransaction, SpecialOffer
)

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'mobile', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'mobile')
    list_filter = ('is_active', 'is_staff', 'date_joined')

# Register User with custom admin
admin.site.register(User, CustomUserAdmin)

# Other models
admin.site.register(UserProfile)
admin.site.register(DailySummary)
admin.site.register(BusinessSnapshot)
admin.site.register(ExpenseCategory)
admin.site.register(Expense)

# Loyalty Program Admin
@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'points_per_rupee', 'points_to_rupee_ratio', 'min_redeem_points')
    list_editable = ('is_active', 'points_per_rupee', 'points_to_rupee_ratio', 'min_redeem_points')

# Membership Tier Admin
@admin.register(MembershipTier)
class MembershipTierAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'min_points_required', 'min_transaction_amount', 'upgrade_price', 'is_active')
    list_editable = ('min_points_required', 'min_transaction_amount', 'upgrade_price', 'is_active')
    list_filter = ('is_active', 'name')

# Loyalty Points Admin
@admin.register(LoyaltyPoints)
class LoyaltyPointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'available_points', 'total_points', 'current_tier', 'total_earned')
    search_fields = ('user__username', 'user__email')
    list_filter = ('program', 'current_tier')
    readonly_fields = ('total_points', 'available_points', 'used_points', 'total_earned')

# Points Transaction Admin
@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('loyalty_account', 'transaction_type', 'points', 'amount', 'description', 'created_at')
    search_fields = ('loyalty_account__user__username', 'description')
    list_filter = ('transaction_type', 'created_at')
    readonly_fields = ('created_at',)

# Special Offer Admin
@admin.register(SpecialOffer)
class SpecialOfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'offer_type', 'is_active', 'bonus_points', 'discount_percentage', 'valid_from', 'valid_until')
    list_editable = ('is_active', 'bonus_points', 'discount_percentage')
    list_filter = ('offer_type', 'is_active', 'valid_from', 'valid_until')
    search_fields = ('name', 'description')
