from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from osp.models import Equipment, Firefighter, PersonnelResource, Request, RequestResponse, RescueOperation, Unit
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

    def test_full_ksrg_flow_requires_decision_then_sign_then_archive(self):
        self.client.login(username='pres', password='pass')
        self.client.post(reverse('osp:request_create', args=[self.unit.pk]), {'title': 'Flow', 'description': 'Desc', 'submit': '1'})
        req = Request.objects.first()

        # cannot sign before official decision
        sign_resp = self.client.post(reverse('osp:request_sign', args=[req.pk]), {'confirm': True})
        self.assertEqual(sign_resp.status_code, 400)

        self.client.logout()
        self.client.login(username='off', password='pass')
        self.client.post(reverse('osp:request_respond', args=[req.pk]), {'message': 'OK', 'action': 'ACCEPT'})

        # official cannot archive before president signature
        archive_before_sign = self.client.post(reverse('osp:request_archive', args=[req.pk]), {'confirm': True})
        self.assertEqual(archive_before_sign.status_code, 400)

        self.client.logout()
        self.client.login(username='pres', password='pass')
        sign_after_decision = self.client.post(reverse('osp:request_sign', args=[req.pk]), {'confirm': True})
        self.assertEqual(sign_after_decision.status_code, 302)

        self.client.logout()
        self.client.login(username='off', password='pass')
        archive_resp = self.client.post(reverse('osp:request_archive', args=[req.pk]), {'confirm': True})
        self.assertEqual(archive_resp.status_code, 302)

        req.refresh_from_db()
        self.assertEqual(req.status, Request.STATUS_ARCHIVED)
        self.assertIsNotNone(req.signed_at)
        self.assertIsNotNone(req.archived_at)

    def test_request_can_store_sis_resources(self):
        equipment = Equipment.objects.create(
            unit=self.unit,
            name='Motopompa',
            category='Pompy',
            inventory_number='EQ-001',
        )
        personnel = PersonnelResource.objects.create(
            unit=self.unit,
            role_name='Dowódca zastępu',
        )

        self.client.login(username='pres', password='pass')
        resp = self.client.post(
            reverse('osp:request_create', args=[self.unit.pk]),
            {
                'title': 'Zgłoszenie KSRG',
                'description': 'Potrzebne wsparcie',
                'submit': '1',
                'equipment_resources': [equipment.pk],
                'personnel_resources': [personnel.pk],
            },
        )
        self.assertEqual(resp.status_code, 302)

        req = Request.objects.first()
        self.assertEqual(req.equipment_resources.count(), 1)
        self.assertEqual(req.personnel_resources.count(), 1)

    def test_unauthorized_cannot_add_equipment(self):
        self.client.login(username='other', password='pass')
        resp = self.client.post(
            reverse('osp:equipment_add', args=[self.unit.pk]),
            {'name': 'Agregat', 'inventory_number': 'EQ-999'},
        )
        self.assertEqual(resp.status_code, 403)

    def test_president_can_register_rescue_operation(self):
        self.client.login(username='pres', password='pass')
        resp = self.client.post(
            reverse('osp:rescue_operation_create', args=[self.unit.pk]),
            {
                'title': 'Pożar hali',
                'incident_type': 'Pożar',
                'location': 'Magazyn A',
                'description': 'Silne zadymienie obiektu.',
                'priority': RescueOperation.PRIORITY_HIGH,
                'occurred_at': '2026-04-03T10:00',
            },
        )
        self.assertEqual(resp.status_code, 302)
        operation = RescueOperation.objects.first()
        self.assertIsNotNone(operation)
        self.assertEqual(operation.status, RescueOperation.STATUS_REGISTERED)

    def test_official_can_post_psp_message_and_update_status(self):
        operation = RescueOperation.objects.create(
            unit=self.unit,
            created_by=self.president,
            title='Wypadek drogowy',
            incident_type='Wypadek',
            location='DK-7',
            description='Kolizja dwóch pojazdów.',
            occurred_at=timezone.now(),
        )

        self.client.login(username='off', password='pass')
        msg_resp = self.client.post(
            reverse('osp:rescue_operation_add_message', args=[operation.pk]),
            {'kind': 'STATUS', 'message': 'PSP na miejscu, rozpoczynamy zabezpieczenie.'},
        )
        self.assertEqual(msg_resp.status_code, 302)

        status_resp = self.client.post(
            reverse('osp:rescue_operation_update_status', args=[operation.pk]),
            {'status': RescueOperation.STATUS_IN_PROGRESS, 'action_started_at': '2026-04-03T10:10'},
        )
        self.assertEqual(status_resp.status_code, 302)

        operation.refresh_from_db()
        self.assertEqual(operation.status, RescueOperation.STATUS_IN_PROGRESS)
        self.assertEqual(operation.messages.count(), 1)
        self.assertEqual(operation.messages.first().sender_type, 'PSP')

    def test_full_rescue_flow_finalize_and_archive(self):
        operation = RescueOperation.objects.create(
            unit=self.unit,
            created_by=self.president,
            title='Podtopienie posesji',
            incident_type='Miejscowe zagrożenie',
            location='OSP Test 12',
            description='Wypompowanie wody.',
            occurred_at=timezone.now(),
            status=RescueOperation.STATUS_IN_PROGRESS,
        )

        self.client.login(username='off', password='pass')
        finalize_resp = self.client.post(
            reverse('osp:rescue_operation_finalize', args=[operation.pk]),
            {'final_report': 'Działania zakończone, miejsce przekazano właścicielowi.', 'closed_at': '2026-04-03T11:30'},
        )
        self.assertEqual(finalize_resp.status_code, 302)

        archive_resp = self.client.post(
            reverse('osp:rescue_operation_archive', args=[operation.pk]),
            {'confirm': True},
        )
        self.assertEqual(archive_resp.status_code, 302)

        operation.refresh_from_db()
        self.assertEqual(operation.status, RescueOperation.STATUS_ARCHIVED)
        self.assertIsNotNone(operation.archived_at)

    def test_rescue_reports_require_authorization(self):
        operation = RescueOperation.objects.create(
            unit=self.unit,
            created_by=self.president,
            title='Pożar traw',
            incident_type='Pożar',
            location='Łąki',
            description='Pożar nieużytków.',
            occurred_at=timezone.now(),
        )

        self.client.login(username='other', password='pass')
        pdf_resp = self.client.get(reverse('osp:rescue_operation_report_pdf', args=[operation.pk]))
        csv_resp = self.client.get(reverse('osp:rescue_operation_report_csv', args=[operation.pk]))

        self.assertEqual(pdf_resp.status_code, 403)
        self.assertEqual(csv_resp.status_code, 403)
