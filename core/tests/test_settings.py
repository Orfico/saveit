# core/tests/test_settings.py
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from core.models import FamilyMember, FamilyProfile


def make_user(username, password='pass'):
    return User.objects.create_user(username=username, password=password)


def make_family_user(username, password='pass'):
    user = make_user(username, password)
    FamilyProfile.objects.create(user=user, member_1='Alice', member_2='Bob')
    return user


class SettingsViewTest(TestCase):

    def setUp(self):
        self.user = make_user('solo')
        self.client.login(username='solo', password='pass')

    def test_settings_page_renders_for_standard_user(self):
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 200)

    def test_settings_page_renders_for_family_user(self):
        family = make_family_user('familyuser')
        self.client.login(username='familyuser', password='pass')
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Family Members')

    def test_settings_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('core:settings'))
        self.assertRedirects(response, f'/login/?next=/settings/')


class AddFamilyMemberViewTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.individual = make_user('member')
        self.client.login(username='family', password='pass')
        self.url = reverse('core:settings_add_member')

    def test_add_member_by_username(self):
        response = self.client.post(self.url, {'username': 'member'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            FamilyMember.objects.filter(
                family_profile=self.family.family_profile, user=self.individual
            ).exists()
        )

    def test_add_member_shows_success_message(self):
        response = self.client.post(self.url, {'username': 'member'}, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any('member' in str(m).lower() or 'added' in str(m).lower() for m in messages))

    def test_add_nonexistent_user_shows_error(self):
        response = self.client.post(self.url, {'username': 'nobody'}, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any('not found' in str(m).lower() or 'no user' in str(m).lower() for m in messages))
        self.assertEqual(FamilyMember.objects.count(), 0)

    def test_add_self_is_rejected(self):
        response = self.client.post(self.url, {'username': 'family'}, follow=True)
        self.assertEqual(FamilyMember.objects.count(), 0)

    def test_add_another_family_account_is_rejected(self):
        other_family = make_family_user('otherfamily')
        response = self.client.post(self.url, {'username': 'otherfamily'}, follow=True)
        self.assertEqual(FamilyMember.objects.count(), 0)

    def test_adding_same_member_twice_is_idempotent(self):
        self.client.post(self.url, {'username': 'member'})
        self.client.post(self.url, {'username': 'member'})
        self.assertEqual(FamilyMember.objects.count(), 1)

    def test_standard_user_cannot_add_members(self):
        self.client.login(username='member', password='pass')
        self.client.post(self.url, {'username': 'family'})
        self.assertEqual(FamilyMember.objects.count(), 0)


class RemoveFamilyMemberViewTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.individual = make_user('member')
        self.fm = FamilyMember.objects.create(
            family_profile=self.family.family_profile, user=self.individual
        )
        self.client.login(username='family', password='pass')

    def test_remove_member(self):
        url = reverse('core:settings_remove_member', args=[self.fm.pk])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FamilyMember.objects.filter(pk=self.fm.pk).exists())

    def test_cannot_remove_other_familys_member(self):
        other_family = make_family_user('otherfamily')
        other_member = make_user('othermember')
        other_fm = FamilyMember.objects.create(
            family_profile=other_family.family_profile, user=other_member
        )
        url = reverse('core:settings_remove_member', args=[other_fm.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(FamilyMember.objects.filter(pk=other_fm.pk).exists())


class SwitchAccountViewTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.individual = make_user('member')
        FamilyMember.objects.create(
            family_profile=self.family.family_profile, user=self.individual
        )

    def test_family_cannot_switch_to_linked_member(self):
        """Family accounts must not access individual members' private accounts."""
        self.client.login(username='family', password='pass')
        url = reverse('core:account_switch', args=[self.individual.pk])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        # Must still be logged in as the family user, not the individual
        self.assertEqual(int(self.client.session['_auth_user_id']), self.family.pk)

    def test_member_can_switch_to_linked_family_account(self):
        self.client.login(username='member', password='pass')
        url = reverse('core:account_switch', args=[self.family.pk])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.family.pk)

    def test_switch_stores_original_user_in_session(self):
        self.client.login(username='member', password='pass')
        url = reverse('core:account_switch', args=[self.family.pk])
        self.client.post(url)
        self.assertEqual(self.client.session['_switch_from'], self.individual.pk)

    def test_unrelated_user_cannot_switch(self):
        unrelated = make_user('unrelated')
        self.client.login(username='unrelated', password='pass')
        url = reverse('core:account_switch', args=[self.family.pk])
        response = self.client.post(url, follow=True)
        # Must NOT have switched — still logged in as unrelated
        self.assertEqual(int(self.client.session['_auth_user_id']), unrelated.pk)

    def test_cannot_switch_to_nonexistent_user(self):
        self.client.login(username='family', password='pass')
        url = reverse('core:account_switch', args=[99999])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.family.pk)


class SwitchBackViewTest(TestCase):

    def setUp(self):
        self.family = make_family_user('family')
        self.individual = make_user('member')
        FamilyMember.objects.create(
            family_profile=self.family.family_profile, user=self.individual
        )

    def _do_switch(self):
        """Helper: log in as family user, switch to member."""
        self.client.login(username='family', password='pass')
        self.client.post(reverse('core:account_switch', args=[self.individual.pk]))

    def test_switch_back_restores_original_user(self):
        self._do_switch()
        self.client.post(reverse('core:account_switch_back'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.family.pk)

    def test_switch_back_clears_session_marker(self):
        self._do_switch()
        self.client.post(reverse('core:account_switch_back'))
        self.assertNotIn('_switch_from', self.client.session)

    def test_switch_back_without_prior_switch_redirects(self):
        self.client.login(username='family', password='pass')
        response = self.client.post(reverse('core:account_switch_back'), follow=True)
        self.assertEqual(response.status_code, 200)
        # Must still be logged in as the family user
        self.assertEqual(int(self.client.session['_auth_user_id']), self.family.pk)


class FamilyMemberModelTest(TestCase):

    def test_unique_together_enforced(self):
        from django.db import IntegrityError
        family = make_family_user('fam')
        member = make_user('mem')
        FamilyMember.objects.create(family_profile=family.family_profile, user=member)
        with self.assertRaises(IntegrityError):
            FamilyMember.objects.create(family_profile=family.family_profile, user=member)

    def test_str_representation(self):
        family = make_family_user('fam')
        member = make_user('mem')
        fm = FamilyMember.objects.create(family_profile=family.family_profile, user=member)
        self.assertIn('mem', str(fm))
