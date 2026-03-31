from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from rewards.models import ReferralEvent, RewardCoin, SpinHistory
from rewards.services import (
    award_daily_login_reward,
    ensure_default_scratch_prizes,
    ensure_default_reward_rules,
    get_or_create_reward_coin,
    issue_scratch_cards,
    process_referral_for_user,
    spin_wheel,
)
from wallet.services import get_or_create_wallet


@override_settings(DISABLE_CELERY=True)
class RewardAutomationTests(TestCase):
    def setUp(self):
        ensure_default_reward_rules()
        User = get_user_model()
        self.referrer = User.objects.create_user(
            email="reward-referrer@example.com",
            password="pass12345",
            username="rewardreferrer",
            mobile="9000000501",
            is_active=True,
        )
        self.invitee = User.objects.create_user(
            email="reward-invitee@example.com",
            password="pass12345",
            username="rewardinvitee",
            mobile="9000000502",
            is_active=True,
            referred_by=self.referrer,
        )

    def test_referral_reward_creates_event_and_wallet_credit(self):
        event = process_referral_for_user(self.invitee)
        self.assertIsNotNone(event)
        self.assertEqual(event.status, ReferralEvent.Status.REWARDED)
        self.assertTrue(ReferralEvent.objects.filter(referrer=self.referrer, referred_user=self.invitee).exists())
        self.assertGreater(get_or_create_wallet(self.referrer).balance, 0)

    def test_daily_login_reward_only_applies_once_per_day(self):
        first = award_daily_login_reward(self.referrer)
        second = award_daily_login_reward(self.referrer)
        coin_account = get_or_create_reward_coin(self.referrer)

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertGreaterEqual(coin_account.available_spins, 1)

    def test_spin_wheel_consumes_spin_and_creates_history(self):
        coin_account = get_or_create_reward_coin(self.referrer)
        coin_account.available_spins = 1
        coin_account.save(update_fields=["available_spins", "updated_at"])

        spin = spin_wheel(self.referrer)
        coin_account.refresh_from_db()

        self.assertIsInstance(spin, SpinHistory)
        self.assertEqual(coin_account.available_spins, 0)

    def test_scratch_prize_options_drive_generated_card_titles(self):
        ensure_default_scratch_prizes()
        cards = issue_scratch_cards(self.referrer, count=1, metadata={"source": "test"})
        self.assertTrue(cards)
        self.assertIsNotNone(cards[0].title)
        self.assertIn("scratch_prize_description", cards[0].metadata)
        self.assertIn("scratch_prize_badge", cards[0].metadata)
        self.assertIn(cards[0].metadata["scratch_prize_badge"], {"Demo preset", "Live prize"})
