from django import forms
from .models import AbstractSubmission, ScientificTheme

class AbstractSubmissionForm(forms.ModelForm):

    title = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your abstract title"
        })
    )

    abstract = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = AbstractSubmission
        fields = ["title", "pdf_file"]
