from django import forms
from .models import (
    Equipment,
    Firefighter,
    PersonnelResource,
    Request,
    RequestResponse,
    RescueMessage,
    RescueOperation,
    OSPReport,
    FuelUsage,
    VehicleInsurance,
    FirefighterTest,
    EquipmentMaintenance,
    TrainingRecord,
)


class SignRequestForm(forms.Form):
    confirm = forms.BooleanField(label="Potwierdzam podpisanie wniosku", required=True)


class ArchiveRequestForm(forms.Form):
    confirm = forms.BooleanField(label="Potwierdzam archiwizację wniosku", required=True)


class FirefighterForm(forms.ModelForm):
    pesel = forms.CharField(label="PESEL", max_length=11, required=True)
    birth_date = forms.DateField(label="Data urodzenia", required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(label="Adres zamieszkania", max_length=300, required=True)

    class Meta:
        model = Firefighter
        fields = [
            'first_name',
            'middle_name',
            'last_name',
            'pesel',
            'birth_date',
            'address',
            'postal_code',
            'city',
            'email',
            'phone',
            'rank',
            'id_card_number',
            'joined_at',
            'driving_license_categories',
            'medical_check_valid_until',
            'emergency_contact_name',
            'emergency_contact_phone',
            'uniform_size',
        ]
        labels = {
            'first_name': 'Imię',
            'middle_name': 'Drugie imię',
            'last_name': 'Nazwisko',
            'email': 'E-mail',
            'phone': 'Telefon',
            'rank': 'Stopień',
            'postal_code': 'Kod pocztowy',
            'city': 'Miejscowość',
            'id_card_number': 'Nr legitymacji',
            'joined_at': 'Data wstąpienia do OSP',
            'driving_license_categories': 'Kategorie prawa jazdy',
            'medical_check_valid_until': 'Badania ważne do',
            'emergency_contact_name': 'Kontakt awaryjny (osoba)',
            'emergency_contact_phone': 'Kontakt awaryjny (telefon)',
            'uniform_size': 'Rozmiar uniformu (Nomex)',
        }
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'joined_at': forms.DateInput(attrs={'type': 'date'}),
            'medical_check_valid_until': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_pesel(self):
        pesel = self.cleaned_data['pesel']
        if not pesel.isdigit() or len(pesel) != 11:
            raise forms.ValidationError("PESEL musi mieć 11 cyfr.")
        existing = Firefighter.objects.filter(pesel=pesel)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Strażak z tym numerem PESEL już istnieje.")
        return pesel


class RequestForm(forms.ModelForm):
    submit = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput())
    equipment_resources = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.none(),
        required=False,
        label='Sprzęt (SiS)',
        widget=forms.SelectMultiple(attrs={'size': 6}),
    )
    personnel_resources = forms.ModelMultipleChoiceField(
        queryset=PersonnelResource.objects.none(),
        required=False,
        label='Siły i środki osobowe (SiS)',
        widget=forms.SelectMultiple(attrs={'size': 6}),
    )

    class Meta:
        model = Request
        fields = ['title', 'description', 'equipment_resources', 'personnel_resources']
        labels = {
            'title': 'Tytuł',
            'description': 'Opis',
        }

    def __init__(self, *args, unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit is not None:
            self.fields['equipment_resources'].queryset = Equipment.objects.filter(unit=unit).order_by('name')
            self.fields['personnel_resources'].queryset = PersonnelResource.objects.filter(unit=unit).order_by('role_name')
        else:
            self.fields['equipment_resources'].queryset = Equipment.objects.none()
            self.fields['personnel_resources'].queryset = PersonnelResource.objects.none()


class ResponseForm(forms.ModelForm):
    class Meta:
        model = RequestResponse
        fields = ['message', 'action']
        labels = {
            'message': 'Wiadomość',
            'action': 'Decyzja',
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name', 'category', 'inventory_number', 'condition', 'inspection_valid_until', 'notes']
        labels = {
            'name': 'Nazwa sprzętu',
            'category': 'Kategoria',
            'inventory_number': 'Numer inwentarzowy',
            'condition': 'Stan',
            'inspection_valid_until': 'Przegląd ważny do',
            'notes': 'Uwagi',
        }
        widgets = {
            'inspection_valid_until': forms.DateInput(attrs={'type': 'date'}),
        }


class PersonnelResourceForm(forms.ModelForm):
    class Meta:
        model = PersonnelResource
        fields = ['firefighter', 'role_name', 'readiness', 'qualifications', 'notes']
        labels = {
            'firefighter': 'Strażak',
            'role_name': 'Rola',
            'readiness': 'Gotowość',
            'qualifications': 'Kwalifikacje',
            'notes': 'Uwagi',
        }

    def __init__(self, *args, unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit is not None:
            self.fields['firefighter'].queryset = Firefighter.objects.filter(unit=unit).order_by('last_name', 'first_name')
        else:
            self.fields['firefighter'].queryset = Firefighter.objects.none()


class RescueOperationForm(forms.ModelForm):
    class Meta:
        model = RescueOperation
        fields = ['title', 'incident_type', 'location', 'description', 'priority', 'occurred_at']
        labels = {
            'title': 'Tytuł działania',
            'incident_type': 'Typ zdarzenia',
            'location': 'Lokalizacja',
            'description': 'Opis operacyjny',
            'priority': 'Priorytet',
            'occurred_at': 'Data i czas zgłoszenia',
        }
        widgets = {
            'occurred_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class RescueMessageForm(forms.ModelForm):
    class Meta:
        model = RescueMessage
        fields = ['kind', 'message']
        labels = {
            'kind': 'Typ meldunku',
            'message': 'Treść meldunku',
        }


class RescueStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (RescueOperation.STATUS_REGISTERED, 'Zarejestrowane'),
            (RescueOperation.STATUS_IN_PROGRESS, 'W trakcie'),
        ],
        label='Nowy status',
    )
    action_started_at = forms.DateTimeField(
        required=False,
        label='Czas rozpoczęcia działań',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )


class RescueFinalReportForm(forms.ModelForm):
    class Meta:
        model = RescueOperation
        fields = ['final_report', 'closed_at']
        labels = {
            'final_report': 'Raport końcowy',
            'closed_at': 'Data i czas zakończenia',
        }
        widgets = {
            'final_report': forms.Textarea(attrs={'rows': 5}),
            'closed_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        closed_at = cleaned_data.get('closed_at')
        occurred_at = getattr(self.instance, 'occurred_at', None)
        if closed_at and occurred_at and closed_at < occurred_at:
            self.add_error('closed_at', 'Data zakończenia nie może być wcześniejsza niż data zgłoszenia.')
        return cleaned_data


class RescueArchiveForm(forms.Form):
    confirm = forms.BooleanField(label='Potwierdzam archiwizację działania', required=True)


# ==================== OSP REPORTING FORMS ====================


class OSPReportForm(forms.ModelForm):
    class Meta:
        model = OSPReport
        fields = ['title', 'description', 'report_start_date', 'report_end_date']
        labels = {
            'title': 'Tytuł raportu',
            'description': 'Opis/Uwagi',
            'report_start_date': 'Data rozpoczęcia okresu sprawozdawczego',
            'report_end_date': 'Data zakończenia okresu sprawozdawczego',
        }
        widgets = {
            'report_start_date': forms.DateInput(attrs={'type': 'date'}),
            'report_end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('report_start_date')
        end = cleaned_data.get('report_end_date')
        if start and end and start > end:
            self.add_error('report_end_date', 'Data zakończenia okresu nie może być wcześniejsza niż data rozpoczęcia.')
        return cleaned_data


class FuelUsageForm(forms.ModelForm):
    class Meta:
        model = FuelUsage
        fields = ['equipment', 'date', 'liters', 'unit_price', 'odometer_reading', 'notes']
        labels = {
            'equipment': 'Pojazd',
            'date': 'Data tankowania',
            'liters': 'Ilość paliwa (litry)',
            'unit_price': 'Cena za litr',
            'odometer_reading': 'Stan licznika (km)',
            'notes': 'Uwagi',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'liters': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'odometer_reading': forms.NumberInput(attrs={'min': '0'}),
        }

    def __init__(self, *args, unit=None, report=None, **kwargs):
        self.report = report
        super().__init__(*args, **kwargs)
        if unit is not None:
            self.fields['equipment'].queryset = Equipment.objects.filter(unit=unit).order_by('name')
        else:
            self.fields['equipment'].queryset = Equipment.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        fuel_date = cleaned_data.get('date')
        if self.report and fuel_date:
            if not (self.report.report_start_date <= fuel_date <= self.report.report_end_date):
                self.add_error('date', 'Data tankowania musi mieścić się w okresie raportu.')
        for field in ('liters', 'unit_price'):
            value = cleaned_data.get(field)
            if value is not None and value <= 0:
                self.add_error(field, 'Wartość musi być większa od zera.')
        return cleaned_data


class VehicleInsuranceForm(forms.ModelForm):
    class Meta:
        model = VehicleInsurance
        fields = ['equipment', 'registration_number', 'vin', 'insurance_provider', 'policy_number',
                  'policy_start_date', 'policy_end_date', 'coverage_type', 'premium_amount', 'notes']
        labels = {
            'equipment': 'Pojazd',
            'registration_number': 'Numer rejestracyjny',
            'vin': 'Numer VIN',
            'insurance_provider': 'Ubezpieczalnia',
            'policy_number': 'Numer polisy',
            'policy_start_date': 'Data rozpoczęcia ubezpieczenia',
            'policy_end_date': 'Data wygaśnięcia ubezpieczenia',
            'coverage_type': 'Rodzaj ubezpieczenia',
            'premium_amount': 'Kwota składki rocznej',
            'notes': 'Uwagi',
        }
        widgets = {
            'policy_start_date': forms.DateInput(attrs={'type': 'date'}),
            'policy_end_date': forms.DateInput(attrs={'type': 'date'}),
            'premium_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit is not None:
            self.fields['equipment'].queryset = Equipment.objects.filter(unit=unit).order_by('name')
        else:
            self.fields['equipment'].queryset = Equipment.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('policy_start_date')
        end = cleaned_data.get('policy_end_date')
        if start and end and end < start:
            self.add_error('policy_end_date', 'Data końca polisy nie może być wcześniejsza niż data początku.')
        premium = cleaned_data.get('premium_amount')
        if premium is not None and premium < 0:
            self.add_error('premium_amount', 'Składka nie może być ujemna.')
        return cleaned_data


class FirefighterTestForm(forms.ModelForm):
    class Meta:
        model = FirefighterTest
        fields = ['test_type', 'test_name', 'test_date', 'result', 'expiration_date',
                  'issued_by', 'certificate_number', 'notes']
        labels = {
            'test_type': 'Rodzaj badania',
            'test_name': 'Nazwa badania/certyfikatu',
            'test_date': 'Data badania',
            'result': 'Wynik',
            'expiration_date': 'Data wygaśnięcia',
            'issued_by': 'Wydane przez',
            'certificate_number': 'Numer certyfikatu',
            'notes': 'Uwagi',
        }
        widgets = {
            'test_date': forms.DateInput(attrs={'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        test_date = cleaned_data.get('test_date')
        expiration = cleaned_data.get('expiration_date')
        if test_date and expiration and expiration < test_date:
            self.add_error('expiration_date', 'Data wygaśnięcia nie może być wcześniejsza niż data badania.')
        return cleaned_data


class EquipmentMaintenanceForm(forms.ModelForm):
    class Meta:
        model = EquipmentMaintenance
        fields = ['equipment', 'maintenance_type', 'status', 'scheduled_date', 'completed_date',
                  'description', 'technician', 'cost', 'notes']
        labels = {
            'equipment': 'Sprzęt',
            'maintenance_type': 'Rodzaj serwisu',
            'status': 'Status',
            'scheduled_date': 'Data zaplanowana',
            'completed_date': 'Data wykonania',
            'description': 'Opis pracy',
            'technician': 'Technik/Serwis',
            'cost': 'Koszt',
            'notes': 'Uwagi',
        }
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'completed_date': forms.DateInput(attrs={'type': 'date'}),
            'cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit is not None:
            self.fields['equipment'].queryset = Equipment.objects.filter(unit=unit).order_by('name')
        else:
            self.fields['equipment'].queryset = Equipment.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        scheduled = cleaned_data.get('scheduled_date')
        completed = cleaned_data.get('completed_date')
        if scheduled and completed and completed < scheduled:
            self.add_error('completed_date', 'Data wykonania nie może być wcześniejsza niż data zaplanowana.')
        cost = cleaned_data.get('cost')
        if cost is not None and cost < 0:
            self.add_error('cost', 'Koszt nie może być ujemny.')
        return cleaned_data


class TrainingRecordForm(forms.ModelForm):
    class Meta:
        model = TrainingRecord
        fields = ['training_name', 'training_date', 'duration_hours', 'status',
                  'instructor_name', 'certification_expiration', 'completion_certificate', 'notes']
        labels = {
            'training_name': 'Nazwa szkolenia',
            'training_date': 'Data szkolenia',
            'duration_hours': 'Czas trwania (godziny)',
            'status': 'Status',
            'instructor_name': 'Prowadzący',
            'certification_expiration': 'Certyfikat ważny do',
            'completion_certificate': 'Numer certyfikatu',
            'notes': 'Uwagi',
        }
        widgets = {
            'training_date': forms.DateInput(attrs={'type': 'date'}),
            'certification_expiration': forms.DateInput(attrs={'type': 'date'}),
            'duration_hours': forms.NumberInput(attrs={'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        training_date = cleaned_data.get('training_date')
        expiration = cleaned_data.get('certification_expiration')
        if training_date and expiration and expiration < training_date:
            self.add_error('certification_expiration', 'Data ważności certyfikatu nie może być wcześniejsza niż data szkolenia.')
        hours = cleaned_data.get('duration_hours')
        if hours is not None and hours < 0:
            self.add_error('duration_hours', 'Liczba godzin nie może być ujemna.')
        return cleaned_data


class FuelUsageInlineForm(forms.ModelForm):
    class Meta:
        model = FuelUsage
        fields = ['equipment', 'date', 'liters', 'unit_price', 'odometer_reading', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'liters': forms.NumberInput(attrs={'type': 'number', 'step': '0.01', 'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'type': 'number', 'step': '0.01', 'class': 'form-control'}),
        }
