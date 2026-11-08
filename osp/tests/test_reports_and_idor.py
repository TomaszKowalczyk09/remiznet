from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from osp.forms import FirefighterForm, FuelUsageForm, OSPReportForm
from osp.models import (
    Equipment,
    EquipmentMaintenance,
    Firefighter,
    OSPReport,
    RescueOperation,
    SisAuditLog,
    TrainingRecord,
    Unit,
)
from osp.templatetags.custom_filters import sum as sum_filter

User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ReportsMaintenanceIdorTest(TestCase):
    def setUp(self):
        president_group, _ = Group.objects.get_or_create(name='president')
        official_group, _ = Group.objects.get_or_create(name='official')

        self.president = User.objects.create_user('pres', password='pass')
        self.president.groups.add(president_group)
        self.official = User.objects.create_user('off', password='pass')
        self.official.groups.add(official_group)
        self.other_president = User.objects.create_user('other_pres', password='pass')
        self.other_president.groups.add(president_group)

        self.unit = Unit.objects.create(name='OSP Test', president=self.president)
        self.other_unit = Unit.objects.create(name='OSP Inna', president=self.other_president)

        self.firefighter = Firefighter.objects.create(
            unit=self.unit,
            first_name='Jan',
            last_name='Kowalski',
            pesel='44051401359',
            birth_date=date(1990, 1, 1),
        )
        self.equipment = Equipment.objects.create(
            unit=self.unit,
            name='Agregat',
            inventory_number='EQ-1',
        )
        self.client = Client()

    def _create_report(self, status=OSPReport.STATUS_DRAFT):
        return OSPReport.objects.create(
            unit=self.unit,
            created_by=self.president,
            title='Raport kwartalny',
            report_start_date=date(2026, 1, 1),
            report_end_date=date(2026, 3, 31),
            status=status,
        )

    def test_report_flow_submit_approve_archive(self):
        report = self._create_report()

        self.client.login(username='pres', password='pass')
        get_resp = self.client.get(reverse('osp:osp_report_submit', args=[report.pk]))
        self.assertEqual(get_resp.status_code, 405)

        submit_resp = self.client.post(reverse('osp:osp_report_submit', args=[report.pk]))
        self.assertEqual(submit_resp.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, OSPReport.STATUS_SUBMITTED)
        self.assertIsNotNone(report.submitted_at)

        self.client.logout()
        self.client.login(username='off', password='pass')
        approve_resp = self.client.post(reverse('osp:osp_report_approve', args=[report.pk]))
        self.assertEqual(approve_resp.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, OSPReport.STATUS_ACCEPTED)
        self.assertEqual(report.approved_by, self.official)

        archive_resp = self.client.post(reverse('osp:osp_report_archive', args=[report.pk]))
        self.assertEqual(archive_resp.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, OSPReport.STATUS_ARCHIVED)
        self.assertIsNotNone(report.archived_at)

        self.assertEqual(
            SisAuditLog.objects.filter(event_type=SisAuditLog.EVENT_REPORT_FLOW).count(),
            3,
        )

    def test_only_official_can_approve_report(self):
        report = self._create_report(status=OSPReport.STATUS_SUBMITTED)

        self.client.login(username='pres', password='pass')
        resp = self.client.post(reverse('osp:osp_report_approve', args=[report.pk]))

        self.assertEqual(resp.status_code, 403)
        report.refresh_from_db()
        self.assertEqual(report.status, OSPReport.STATUS_SUBMITTED)

    def test_president_cannot_create_report_for_foreign_unit(self):
        self.client.login(username='other_pres', password='pass')
        resp = self.client.post(
            reverse('osp:osp_report_create', args=[self.unit.pk]),
            {
                'title': 'Obcy raport',
                'description': '',
                'report_start_date': '2026-01-01',
                'report_end_date': '2026-01-31',
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(OSPReport.objects.count(), 0)

    def test_president_cannot_add_equipment_to_foreign_unit(self):
        self.client.login(username='other_pres', password='pass')
        resp = self.client.post(
            reverse('osp:equipment_add', args=[self.unit.pk]),
            {'name': 'Obcy sprzęt', 'inventory_number': 'EQ-X'},
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Equipment.objects.filter(name='Obcy sprzęt').count(), 0)

    def test_maintenance_add_edit_delete(self):
        self.client.login(username='pres', password='pass')
        add_resp = self.client.post(
            reverse('osp:equipment_maintenance_add', args=[self.unit.pk]),
            {
                'equipment': self.equipment.pk,
                'maintenance_type': EquipmentMaintenance.MAINTENANCE_TYPE_INSPECTION,
                'status': EquipmentMaintenance.STATUS_SCHEDULED,
                'scheduled_date': '2026-05-01',
                'completed_date': '',
                'description': 'Przegląd roczny',
                'technician': 'Serwis ABC',
                'cost': '250.00',
                'notes': '',
            },
        )
        self.assertEqual(add_resp.status_code, 302)
        maintenance = EquipmentMaintenance.objects.get()
        self.assertEqual(maintenance.equipment, self.equipment)

        edit_resp = self.client.post(
            reverse('osp:equipment_maintenance_edit', args=[maintenance.pk]),
            {
                'equipment': self.equipment.pk,
                'maintenance_type': EquipmentMaintenance.MAINTENANCE_TYPE_INSPECTION,
                'status': EquipmentMaintenance.STATUS_COMPLETED,
                'scheduled_date': '2026-05-01',
                'completed_date': '2026-05-02',
                'description': 'Przegląd roczny wykonany',
                'technician': 'Serwis ABC',
                'cost': '250.00',
                'notes': '',
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        maintenance.refresh_from_db()
        self.assertEqual(maintenance.status, EquipmentMaintenance.STATUS_COMPLETED)

        delete_resp = self.client.post(reverse('osp:equipment_maintenance_delete', args=[maintenance.pk]))
        self.assertEqual(delete_resp.status_code, 302)
        self.assertEqual(EquipmentMaintenance.objects.count(), 0)

    def test_foreign_president_cannot_manage_maintenance(self):
        maintenance = EquipmentMaintenance.objects.create(
            equipment=self.equipment,
            maintenance_type=EquipmentMaintenance.MAINTENANCE_TYPE_INSPECTION,
            scheduled_date=date(2026, 5, 1),
            description='Przegląd',
            technician='Serwis',
        )
        self.client.login(username='other_pres', password='pass')

        resp = self.client.get(reverse('osp:equipment_maintenance_edit', args=[maintenance.pk]))

        self.assertEqual(resp.status_code, 403)

    def test_training_add_edit_delete(self):
        self.client.login(username='pres', password='pass')
        add_resp = self.client.post(
            reverse('osp:training_record_add', args=[self.firefighter.pk]),
            {
                'training_name': 'Kurs pierwszej pomocy',
                'training_date': '2026-02-01',
                'duration_hours': '8',
                'status': TrainingRecord.STATUS_COMPLETED,
                'instructor_name': 'Jan Instruktor',
                'certification_expiration': '2028-02-01',
                'completion_certificate': 'CERT-1',
                'notes': '',
            },
        )
        self.assertEqual(add_resp.status_code, 302)
        training = TrainingRecord.objects.get()
        self.assertEqual(training.firefighter, self.firefighter)

        edit_resp = self.client.post(
            reverse('osp:training_record_edit', args=[training.pk]),
            {
                'training_name': 'Kurs pierwszej pomocy - powtórka',
                'training_date': '2026-02-01',
                'duration_hours': '6',
                'status': TrainingRecord.STATUS_COMPLETED,
                'instructor_name': 'Jan Instruktor',
                'certification_expiration': '2028-02-01',
                'completion_certificate': 'CERT-1',
                'notes': '',
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        training.refresh_from_db()
        self.assertEqual(training.duration_hours, 6)

        delete_resp = self.client.post(reverse('osp:training_record_delete', args=[training.pk]))
        self.assertEqual(delete_resp.status_code, 302)
        self.assertEqual(TrainingRecord.objects.count(), 0)

    def test_monthly_report_filters_by_occurred_at(self):
        RescueOperation.objects.create(
            unit=self.unit,
            created_by=self.president,
            title='Działanie styczniowe',
            incident_type='Pożar',
            location='Rynek',
            description='Pożar',
            occurred_at=timezone.make_aware(timezone.datetime(2025, 1, 15, 10, 0)),
        )
        self.client.login(username='off', password='pass')

        resp = self.client.get(reverse('osp:rescue_monthly_report'), {'year': 2025, 'month': 1})

        self.assertEqual(resp.status_code, 200)
        titles = [op.title for op in resp.context['operations']]
        self.assertIn('Działanie styczniowe', titles)

    def test_monthly_report_rejects_invalid_period(self):
        self.client.login(username='off', password='pass')

        resp = self.client.get(reverse('osp:rescue_monthly_report'), {'year': 'abc', 'month': 13})

        self.assertEqual(resp.status_code, 400)

    def test_osp_report_form_rejects_reversed_period(self):
        form = OSPReportForm(
            data={
                'title': 'Raport',
                'description': '',
                'report_start_date': '2026-03-31',
                'report_end_date': '2026-01-01',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('report_end_date', form.errors)

    def test_firefighter_form_rejects_duplicate_pesel(self):
        form = FirefighterForm(
            data={
                'unit': self.unit.pk,
                'first_name': 'Adam',
                'last_name': 'Nowak',
                'pesel': '44051401359',
                'birth_date': '1991-01-01',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('pesel', form.errors)

    def test_fuel_usage_form_rejects_date_outside_report_period(self):
        report = self._create_report()
        form = FuelUsageForm(
            data={
                'equipment': self.equipment.pk,
                'date': '2026-06-01',
                'liters': '10.00',
                'unit_price': '6.00',
                'odometer_reading': '1000',
                'notes': '',
            },
            unit=self.unit,
            report=report,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_report_and_related_pages_render(self):
        report = self._create_report()
        maintenance = EquipmentMaintenance.objects.create(
            equipment=self.equipment,
            maintenance_type=EquipmentMaintenance.MAINTENANCE_TYPE_INSPECTION,
            scheduled_date=date(2026, 5, 1),
            description='Przegląd',
            technician='Serwis',
        )
        TrainingRecord.objects.create(
            firefighter=self.firefighter,
            training_name='Szkolenie',
            training_date=date(2026, 2, 1),
            duration_hours=4,
        )

        self.client.login(username='pres', password='pass')
        urls = [
            reverse('osp:osp_report_list'),
            reverse('osp:osp_report_detail', args=[report.pk]),
            reverse('osp:osp_report_create', args=[self.unit.pk]),
            reverse('osp:equipment_maintenance_list', args=[self.unit.pk]),
            reverse('osp:equipment_maintenance_add', args=[self.unit.pk]),
            reverse('osp:equipment_maintenance_edit', args=[maintenance.pk]),
            reverse('osp:equipment_maintenance_delete', args=[maintenance.pk]),
            reverse('osp:training_record_list', args=[self.firefighter.pk]),
            reverse('osp:training_record_add', args=[self.firefighter.pk]),
            reverse('osp:vehicle_insurance_list', args=[self.unit.pk]),
            reverse('osp:equipment_list'),
            reverse('osp:personnel_list'),
            reverse('osp:firefighter_list'),
            reverse('osp:request_list'),
            reverse('osp:rescue_operation_list'),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_custom_sum_filter_returns_decimal(self):
        class Item:
            def __init__(self, value):
                self.value = value

        items = [Item(Decimal('1.50')), Item(None), Item(Decimal('2.25'))]

        self.assertEqual(sum_filter(items, 'value'), Decimal('3.75'))
