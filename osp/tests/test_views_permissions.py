from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from osp.models import Unit, Firefighter, Request, RequestResponse
from django.contrib.auth.models import Group

User = get_user_model()


class OspViewsTest(TestCase):
    def setUp(self):
        # create groups
        self.pres_group, _ = Group.objects.get_or_create(name='president')
        self.off_group, _ = Group.objects.get_or_create(name='official')
        # users
        self.president = User.objects.create_user('pres', password='pass')
        self.president.groups.add(self.pres_group)
        self.official = User.objects.create_user('off', password='pass')
        self.official.groups.add(self.off_group)
        self.other = User.objects.create_user('other', password='pass')
        # unit
        self.unit = Unit.objects.create(name='OSP Test')
        self.client = Client()

    def test_happy_path_request_flow(self):
        # president creates and submits request
        self.client.login(username='pres', password='pass')
        url = reverse('osp:request_create', args=[self.unit.pk])
        resp = self.client.post(url, {'title': 'Need funding', 'description': 'Please', 'submit': '1'})
        self.assertEqual(resp.status_code, 302)
        req = Request.objects.first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, Request.STATUS_SUBMITTED)
        # official responds
        self.client.logout()
        self.client.login(username='off', password='pass')
        resp = self.client.post(reverse('osp:request_respond', args=[req.pk]), {'message': 'Accepted', 'action': 'ACCEPT'})
        self.assertEqual(resp.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, Request.STATUS_ACCEPTED)
        self.assertEqual(req.responses.count(), 1)

    def test_unauthorized_cannot_add_firefighter(self):
        # other user (no group) tries to add firefighter
        self.client.login(username='other', password='pass')
        resp = self.client.post(reverse('osp:firefighter_add', args=[self.unit.pk]), {'first_name': 'Jan', 'last_name': 'Kowalski'})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Firefighter.objects.count(), 0)

    def test_cannot_respond_twice_to_finalized(self):
        # president makes request
        self.client.login(username='pres', password='pass')
        self.client.post(reverse('osp:request_create', args=[self.unit.pk]), {'title': 'R', 'description': 'D', 'submit': '1'})
        req = Request.objects.first()
        # official accepts
        self.client.logout()
        self.client.login(username='off', password='pass')
        self.client.post(reverse('osp:request_respond', args=[req.pk]), {'message': 'OK', 'action': 'ACCEPT'})
        # second response should be rejected (400)
        resp = self.client.post(reverse('osp:request_respond', args=[req.pk]), {'message': 'Another', 'action': 'REJECT'})
        self.assertEqual(resp.status_code, 400)

    def test_panel_shows_units_assigned_by_president_field(self):
        self.unit.president = self.president
        self.unit.save(update_fields=['president'])

        self.client.login(username='pres', password='pass')
        resp = self.client.get(reverse('osp:panel'))

        self.assertEqual(resp.status_code, 200)
        units = list(resp.context['units'])
        self.assertIn(self.unit, units)

    def test_request_pdf_available_for_authorized_user(self):
        self.client.login(username='pres', password='pass')
        self.client.post(reverse('osp:request_create', args=[self.unit.pk]), {'title': 'PDF', 'description': 'Treść', 'submit': '1'})
        req = Request.objects.first()

        resp = self.client.get(reverse('osp:request_pdf', args=[req.pk]))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn(f'wniosek-{req.pk}.pdf', resp['Content-Disposition'])

    def test_request_pdf_forbidden_for_unauthorized_user(self):
        self.client.login(username='pres', password='pass')
        self.client.post(reverse('osp:request_create', args=[self.unit.pk]), {'title': 'PDF', 'description': 'Treść', 'submit': '1'})
        req = Request.objects.first()

        self.client.logout()
        self.client.login(username='other', password='pass')
        resp = self.client.get(reverse('osp:request_pdf', args=[req.pk]))

        self.assertEqual(resp.status_code, 403)
