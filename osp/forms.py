from django import forms
class SignRequestForm(forms.Form):
    confirm = forms.BooleanField(label="Potwierdzam podpisanie wniosku", required=True)
from .models import Firefighter, Request, RequestResponse


class FirefighterForm(forms.ModelForm):
    class Meta:
        model = Firefighter
        fields = ['first_name', 'last_name', 'email', 'phone', 'rank']


class RequestForm(forms.ModelForm):
    submit = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput())

    class Meta:
        model = Request
        fields = ['title', 'description']


class ResponseForm(forms.ModelForm):
    class Meta:
        model = RequestResponse
        fields = ['message', 'action']
