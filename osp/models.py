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

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Roboczy'),
        (STATUS_SUBMITTED, 'Złożony'),
        (STATUS_ACCEPTED, 'Zaakceptowany'),
        (STATUS_REJECTED, 'Odrzucony'),
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
