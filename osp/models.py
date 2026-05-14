from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Unit(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    president = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='presided_units')

    def __str__(self):
        return self.name


class Firefighter(models.Model):
    UNIFORM_SIZE_XS = 'XS'
    UNIFORM_SIZE_S = 'S'
    UNIFORM_SIZE_M = 'M'
    UNIFORM_SIZE_L = 'L'
    UNIFORM_SIZE_XL = 'XL'
    UNIFORM_SIZE_2XL = '2XL'
    UNIFORM_SIZE_3XL = '3XL'
    UNIFORM_SIZE_4XL = '4XL'

    UNIFORM_SIZE_CHOICES = [
        (UNIFORM_SIZE_XS, 'XS'),
        (UNIFORM_SIZE_S, 'S'),
        (UNIFORM_SIZE_M, 'M'),
        (UNIFORM_SIZE_L, 'L'),
        (UNIFORM_SIZE_XL, 'XL'),
        (UNIFORM_SIZE_2XL, '2XL'),
        (UNIFORM_SIZE_3XL, '3XL'),
        (UNIFORM_SIZE_4XL, '4XL'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='firefighters')
    first_name = models.CharField(max_length=120)
    middle_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120)
    pesel = models.CharField(max_length=11, default='')
    birth_date = models.DateField()
    address = models.CharField(max_length=300, default='', blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    rank = models.CharField(max_length=100, blank=True)
    id_card_number = models.CharField(max_length=50, blank=True)
    joined_at = models.DateField(null=True, blank=True)
    driving_license_categories = models.CharField(max_length=50, blank=True)
    medical_check_valid_until = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    uniform_size = models.CharField(max_length=5, blank=True, choices=UNIFORM_SIZE_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.unit})"


class Request(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_ARCHIVED = 'ARCHIVED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Roboczy'),
        (STATUS_SUBMITTED, 'Złożony'),
        (STATUS_ACCEPTED, 'Zaakceptowany'),
        (STATUS_REJECTED, 'Odrzucony'),
        (STATUS_ARCHIVED, 'Zarchiwizowany'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='requests')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=250)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='signed_requests')
    signed_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='archived_requests')
    archived_at = models.DateTimeField(null=True, blank=True)
    equipment_resources = models.ManyToManyField('Equipment', blank=True, related_name='requests')
    personnel_resources = models.ManyToManyField('PersonnelResource', blank=True, related_name='requests')

    def __str__(self):
        return f"{self.title} - {self.unit} [{self.status}]"


class RequestResponse(models.Model):
    ACTION_ACCEPT = 'ACCEPT'
    ACTION_REJECT = 'REJECT'
    ACTION_COMMENT = 'COMMENT'

    ACTION_CHOICES = [
        (ACTION_ACCEPT, 'Zaakceptuj'),
        (ACTION_REJECT, 'Odrzuć'),
        (ACTION_COMMENT, 'Komentarz'),
    ]

    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_COMMENT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.responder} on {self.request}"


class Equipment(models.Model):
    CONDITION_READY = 'READY'
    CONDITION_SERVICE = 'SERVICE'
    CONDITION_UNAVAILABLE = 'UNAVAILABLE'

    CONDITION_CHOICES = [
        (CONDITION_READY, 'Gotowy'),
        (CONDITION_SERVICE, 'W serwisie'),
        (CONDITION_UNAVAILABLE, 'Niedostępny'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='equipment')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=120, blank=True)
    inventory_number = models.CharField(max_length=100)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default=CONDITION_READY)
    inspection_valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('unit', 'inventory_number')

    def __str__(self):
        return f"{self.name} ({self.unit})"


class PersonnelResource(models.Model):
    READINESS_AVAILABLE = 'AVAILABLE'
    READINESS_ON_CALL = 'ON_CALL'
    READINESS_UNAVAILABLE = 'UNAVAILABLE'

    READINESS_CHOICES = [
        (READINESS_AVAILABLE, 'Dostępny'),
        (READINESS_ON_CALL, 'Pod telefonem'),
        (READINESS_UNAVAILABLE, 'Niedostępny'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='personnel_resources')
    firefighter = models.ForeignKey(Firefighter, on_delete=models.SET_NULL, null=True, blank=True, related_name='personnel_entries')
    role_name = models.CharField(max_length=120)
    readiness = models.CharField(max_length=20, choices=READINESS_CHOICES, default=READINESS_AVAILABLE)
    qualifications = models.CharField(max_length=250, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.firefighter:
            return f"{self.firefighter} - {self.role_name}"
        return f"{self.role_name} ({self.unit})"


class SisAuditLog(models.Model):
    EVENT_RESOURCE_UPDATE = 'RESOURCE_UPDATE'
    EVENT_REQUEST_FLOW = 'REQUEST_FLOW'

    EVENT_CHOICES = [
        (EVENT_RESOURCE_UPDATE, 'Zmiana zasobów SiS'),
        (EVENT_REQUEST_FLOW, 'Zmiana obiegu KSRG'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='sis_audit_logs')
    request = models.ForeignKey(Request, on_delete=models.CASCADE, null=True, blank=True, related_name='sis_audit_logs')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.unit} ({self.created_at:%Y-%m-%d %H:%M})"


class RescueOperation(models.Model):
    STATUS_REGISTERED = 'REGISTERED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_CLOSED = 'CLOSED'
    STATUS_ARCHIVED = 'ARCHIVED'

    STATUS_CHOICES = [
        (STATUS_REGISTERED, 'Zarejestrowane'),
        (STATUS_IN_PROGRESS, 'W trakcie'),
        (STATUS_CLOSED, 'Zamknięte'),
        (STATUS_ARCHIVED, 'Zarchiwizowane'),
    ]

    PRIORITY_LOW = 'LOW'
    PRIORITY_MEDIUM = 'MEDIUM'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_CRITICAL = 'CRITICAL'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Niski'),
        (PRIORITY_MEDIUM, 'Średni'),
        (PRIORITY_HIGH, 'Wysoki'),
        (PRIORITY_CRITICAL, 'Krytyczny'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='rescue_operations')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_rescue_operations')
    title = models.CharField(max_length=250)
    incident_type = models.CharField(max_length=120)
    location = models.CharField(max_length=250)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REGISTERED)
    occurred_at = models.DateTimeField()
    action_started_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    final_report = models.TextField(blank=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_rescue_operations',
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.unit})"


class RescueMessage(models.Model):
    SENDER_OSP = 'OSP'
    SENDER_PSP = 'PSP'

    SENDER_CHOICES = [
        (SENDER_OSP, 'OSP'),
        (SENDER_PSP, 'PSP'),
    ]

    KIND_INFO = 'INFO'
    KIND_STATUS = 'STATUS'
    KIND_DECISION = 'DECISION'

    KIND_CHOICES = [
        (KIND_INFO, 'Informacja'),
        (KIND_STATUS, 'Status operacyjny'),
        (KIND_DECISION, 'Decyzja/ustalenie'),
    ]

    operation = models.ForeignKey(RescueOperation, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_INFO)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_sender_type_display()} - {self.operation_id} ({self.created_at:%Y-%m-%d %H:%M})"


class RescueAuditLog(models.Model):
    EVENT_FLOW = 'FLOW'
    EVENT_REPORTING = 'REPORTING'

    EVENT_CHOICES = [
        (EVENT_FLOW, 'Obieg działań ratowniczych'),
        (EVENT_REPORTING, 'Raportowanie działań ratowniczych'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='rescue_audit_logs')
    operation = models.ForeignKey(RescueOperation, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.operation_id}"


# ==================== OSP REPORTING MODELS ====================


class OSPReport(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_ARCHIVED = 'ARCHIVED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Roboczy'),
        (STATUS_SUBMITTED, 'Przesłany'),
        (STATUS_ACCEPTED, 'Zaakceptowany'),
        (STATUS_ARCHIVED, 'Zarchiwizowany'),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='osp_reports')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_osp_reports')
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    report_start_date = models.DateField()
    report_end_date = models.DateField()
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_osp_reports')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_osp_reports')
    approved_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('unit', 'report_start_date', 'report_end_date')

    def __str__(self):
        return f"{self.title} ({self.unit}) [{self.report_start_date} - {self.report_end_date}]"


class FuelUsage(models.Model):
    report = models.ForeignKey(OSPReport, on_delete=models.CASCADE, related_name='fuel_usage')
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, related_name='fuel_usage')
    date = models.DateField()
    liters = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    odometer_reading = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"Fuel {self.liters}L on {self.date} ({self.report})"

    def save(self, *args, **kwargs):
        self.total_cost = self.liters * self.unit_price
        super().save(*args, **kwargs)


class VehicleInsurance(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='vehicle_insurance')
    equipment = models.OneToOneField(Equipment, on_delete=models.CASCADE, related_name='insurance')
    registration_number = models.CharField(max_length=50)
    vin = models.CharField(max_length=100, blank=True)
    insurance_provider = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100)
    policy_start_date = models.DateField()
    policy_end_date = models.DateField()
    coverage_type = models.CharField(max_length=100, blank=True)
    premium_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['policy_end_date']

    def __str__(self):
        return f"{self.equipment} - {self.registration_number} ({self.insurance_provider})"


class FirefighterTest(models.Model):
    TEST_TYPE_MEDICAL = 'MEDICAL'
    TEST_TYPE_CERTIFICATION = 'CERTIFICATION'
    TEST_TYPE_TRAINING = 'TRAINING'

    TEST_TYPE_CHOICES = [
        (TEST_TYPE_MEDICAL, 'Badanie lekarskie'),
        (TEST_TYPE_CERTIFICATION, 'Certyfikat/kwalifikacja'),
        (TEST_TYPE_TRAINING, 'Szkolenie'),
    ]

    RESULT_PASS = 'PASS'
    RESULT_FAIL = 'FAIL'
    RESULT_PENDING = 'PENDING'

    RESULT_CHOICES = [
        (RESULT_PASS, 'Pozytywny'),
        (RESULT_FAIL, 'Negatywny'),
        (RESULT_PENDING, 'Oczekujący'),
    ]

    firefighter = models.ForeignKey(Firefighter, on_delete=models.CASCADE, related_name='tests')
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    test_name = models.CharField(max_length=250)
    test_date = models.DateField()
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    expiration_date = models.DateField(null=True, blank=True)
    issued_by = models.CharField(max_length=200, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-test_date']

    def __str__(self):
        return f"{self.firefighter} - {self.get_test_type_display()} ({self.test_date})"


class EquipmentMaintenance(models.Model):
    MAINTENANCE_TYPE_PREVENTIVE = 'PREVENTIVE'
    MAINTENANCE_TYPE_CORRECTIVE = 'CORRECTIVE'
    MAINTENANCE_TYPE_INSPECTION = 'INSPECTION'

    MAINTENANCE_TYPE_CHOICES = [
        (MAINTENANCE_TYPE_PREVENTIVE, 'Preventywna'),
        (MAINTENANCE_TYPE_CORRECTIVE, 'Naprawy'),
        (MAINTENANCE_TYPE_INSPECTION, 'Przegląd'),
    ]

    STATUS_SCHEDULED = 'SCHEDULED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Zaplanowana'),
        (STATUS_IN_PROGRESS, 'W trakcie'),
        (STATUS_COMPLETED, 'Ukończona'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_logs')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    technician = models.CharField(max_length=200)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.equipment} - {self.get_maintenance_type_display()} ({self.scheduled_date})"


class TrainingRecord(models.Model):
    STATUS_PLANNED = 'PLANNED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Zaplanowana'),
        (STATUS_COMPLETED, 'Ukończona'),
        (STATUS_CANCELLED, 'Anulowana'),
    ]

    firefighter = models.ForeignKey(Firefighter, on_delete=models.CASCADE, related_name='training_records')
    training_name = models.CharField(max_length=250)
    training_date = models.DateField()
    duration_hours = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    instructor_name = models.CharField(max_length=200, blank=True)
    certification_expiration = models.DateField(null=True, blank=True)
    completion_certificate = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-training_date']

    def __str__(self):
        return f"{self.firefighter} - {self.training_name} ({self.training_date})"
