from django import forms
class SignRequestForm(forms.Form):
    confirm = forms.BooleanField(label="Potwierdzam podpisanie wniosku", required=True)
from .models import Firefighter, Request, RequestResponse


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

    class Meta:
        model = Request
        fields = ['title', 'description']
        labels = {
            'title': 'Tytuł',
            'description': 'Opis',
        }


class ResponseForm(forms.ModelForm):
    class Meta:
        model = RequestResponse
        fields = ['message', 'action']
        labels = {
            'message': 'Wiadomość',
            'action': 'Decyzja',
        }
