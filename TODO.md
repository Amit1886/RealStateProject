# Coupon Management Implementation Plan

## Models (commerce/models.py)
- [x] Add Coupon model with types (discount, offer, spin-win, scratch), discount details, limits, expiry
- [x] Add UserCoupon model for user-specific coupons
- [x] Add CouponUsage model to track usage and prevent loss

## Views (commerce/views.py)
- [x] Admin CRUD views for coupons
- [x] User views: coupon list, apply coupon, spin/scratch logic
- [x] Dashboard view with coupon slider

## URLs (commerce/urls.py)
- [x] Add coupon management URLs for admin and user

## Forms (commerce/forms.py)
- [x] Coupon creation/edit forms with validation

## Admin (commerce/admin.py)
- [x] Register coupon models in admin interface

## Templates
- [x] Create coupon management templates
- [x] Update dashboard with modern coupon slider

## Followup Steps
- [x] Run migrations for new models
- [x] Test coupon application and loss prevention
- [x] Integrate with order/payment flow
