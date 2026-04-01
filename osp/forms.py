from django import forms
from .models import Equipment, Firefighter, PersonnelResource, Request, RequestResponse


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
