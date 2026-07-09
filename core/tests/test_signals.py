from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Category, FamilyMember, FamilyProfile, Transaction


def make_user(username):
    return User.objects.create_user(username=username, password='pass')


def make_family_user(username):
    user = make_user(username)
    FamilyProfile.objects.create(user=user, member_1='Alice', member_2='Bob')
    return user


def make_category(user, name='Food', cat_type=Category.EXPENSE):
    return Category.objects.create(
        name=name, user=user, type=cat_type,
        scope=Category.PERSONAL, color='#FF0000',
    )


TXN_DATE = date(2026, 6, 15)


class PropagateSignalCreateTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.member_a = make_user('member_a')
        self.member_b = make_user('member_b')
        FamilyMember.objects.create(family_profile=self.family.family_profile, user=self.member_a)
        FamilyMember.objects.create(family_profile=self.family.family_profile, user=self.member_b)
        self.cat = make_category(self.family, 'Food')

    def _make_family_txn(self, amount=-10, description='Lunch'):
        return Transaction.objects.create(
            user=self.family,
            category=self.cat,
            amount=Decimal(str(amount)),
            date=TXN_DATE,
            description=description,
            notes='note',
            is_recurring=False,
        )

    # ── propagation on create ─────────────────────────────────────────────

    def test_create_propagates_to_each_member(self):
        self._make_family_txn()
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 1)
        self.assertEqual(Transaction.objects.filter(user=self.member_b).count(), 1)

    def test_amount_halved_on_create(self):
        self._make_family_txn(amount=-10)
        copy = Transaction.objects.get(user=self.member_a)
        self.assertEqual(copy.amount, Decimal('-5.00'))

    def test_odd_cent_amount_rounded_half_up(self):
        self._make_family_txn(amount=-7)
        copy = Transaction.objects.get(user=self.member_a)
        self.assertEqual(copy.amount, Decimal('-3.50'))

    def test_fields_inherited_on_create(self):
        self._make_family_txn(description='Pizza night')
        copy = Transaction.objects.get(user=self.member_a)
        self.assertEqual(copy.date, TXN_DATE)
        self.assertEqual(copy.description, 'Pizza night')
        self.assertEqual(copy.notes, 'note')

    def test_paid_by_is_none_on_copy(self):
        self._make_family_txn()
        copy = Transaction.objects.get(user=self.member_a)
        self.assertIsNone(copy.paid_by)

    def test_is_recurring_false_on_copy(self):
        self._make_family_txn()
        copy = Transaction.objects.get(user=self.member_a)
        self.assertFalse(copy.is_recurring)

    def test_source_transaction_fk_set_on_copy(self):
        original = self._make_family_txn()
        copy = Transaction.objects.get(user=self.member_a)
        self.assertEqual(copy.source_transaction, original)

    def test_original_not_modified(self):
        original = self._make_family_txn(amount=-10)
        original.refresh_from_db()
        self.assertEqual(original.amount, Decimal('-10'))
        self.assertEqual(original.user, self.family)
        self.assertIsNone(original.source_transaction)

    # ── propagation on update ─────────────────────────────────────────────

    def test_update_propagates_to_existing_copies(self):
        original = self._make_family_txn(amount=-10, description='Old')
        original.description = 'New'
        original.amount = Decimal('-20')
        original.save()
        copy = Transaction.objects.get(user=self.member_a)
        self.assertEqual(copy.description, 'New')
        self.assertEqual(copy.amount, Decimal('-10.00'))

    def test_update_does_not_create_extra_copies(self):
        original = self._make_family_txn()
        original.description = 'Updated'
        original.save()
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 1)

    # ── recursion guard ───────────────────────────────────────────────────

    def test_derived_copy_does_not_re_propagate(self):
        original = self._make_family_txn()
        # Total transactions: 1 (family) + 1 (member_a) + 1 (member_b) = 3
        self.assertEqual(Transaction.objects.count(), 3)

    def test_no_infinite_loop_on_copy_save(self):
        original = self._make_family_txn()
        copy = Transaction.objects.get(user=self.member_a)
        # Re-saving the derived copy must not create more transactions.
        before = Transaction.objects.count()
        copy.notes = 'changed'
        copy.save()
        self.assertEqual(Transaction.objects.count(), before)


class PropagateSignalNonFamilyTest(TestCase):

    def setUp(self):
        self.regular_user = make_user('regular')
        self.cat = make_category(self.regular_user, 'Food')

    def test_individual_user_does_not_propagate(self):
        Transaction.objects.create(
            user=self.regular_user,
            category=self.cat,
            amount=Decimal('-10'),
            date=TXN_DATE,
            description='Solo lunch',
            is_recurring=False,
        )
        # Only 1 transaction created — no copies.
        self.assertEqual(Transaction.objects.count(), 1)


class PropagateSignalNoMembersTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.cat = make_category(self.family, 'Food')

    def test_family_with_no_members_creates_no_copies(self):
        Transaction.objects.create(
            user=self.family,
            category=self.cat,
            amount=Decimal('-10'),
            date=TXN_DATE,
            description='Alone',
            is_recurring=False,
        )
        self.assertEqual(Transaction.objects.count(), 1)


class PropagateSignalCategoryResolutionTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.member = make_user('member')
        FamilyMember.objects.create(family_profile=self.family.family_profile, user=self.member)
        self.family_cat = make_category(self.family, 'Food')

    def test_category_matched_from_member_own_categories(self):
        member_cat = make_category(self.member, 'Food')
        Transaction.objects.create(
            user=self.family, category=self.family_cat,
            amount=Decimal('-10'), date=TXN_DATE,
            description='Test', is_recurring=False,
        )
        copy = Transaction.objects.get(user=self.member)
        self.assertEqual(copy.category, member_cat)

    def test_global_category_reused(self):
        global_cat = Category.objects.create(
            name='Food', type=Category.EXPENSE, scope=Category.GLOBAL, color='#00FF00',
        )
        Transaction.objects.create(
            user=self.family, category=self.family_cat,
            amount=Decimal('-10'), date=TXN_DATE,
            description='Test', is_recurring=False,
        )
        copy = Transaction.objects.get(user=self.member)
        self.assertEqual(copy.category, global_cat)

    def test_falls_back_to_home_when_no_category_match(self):
        Transaction.objects.create(
            user=self.family, category=self.family_cat,
            amount=Decimal('-10'), date=TXN_DATE,
            description='Test', is_recurring=False,
        )
        copy = Transaction.objects.get(user=self.member)
        self.assertEqual(copy.category.name.lower(), 'home')

    def test_home_category_auto_created_if_missing(self):
        self.assertFalse(Category.objects.filter(name__iexact='home').exists())
        Transaction.objects.create(
            user=self.family, category=self.family_cat,
            amount=Decimal('-10'), date=TXN_DATE,
            description='Test', is_recurring=False,
        )
        self.assertTrue(
            Category.objects.filter(user=self.member, name__iexact='home').exists()
        )

    def test_existing_home_category_reused_not_duplicated(self):
        home = Category.objects.create(
            name='home', user=self.member, type=Category.EXPENSE,
            scope=Category.PERSONAL, color='#0000FF',
        )
        Transaction.objects.create(
            user=self.family, category=self.family_cat,
            amount=Decimal('-10'), date=TXN_DATE,
            description='Test', is_recurring=False,
        )
        copy = Transaction.objects.get(user=self.member)
        self.assertEqual(copy.category, home)
        self.assertEqual(Category.objects.filter(user=self.member, name__iexact='home').count(), 1)
