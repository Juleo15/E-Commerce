from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):

    class Meta:
        model = Order
        fields = [
            "full_name",
            "phone",
            "address",
            "city",
            "state",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your full name"
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your phone number"
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your delivery address",
                    "rows": 3
                }
            ),

            "city": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your city"
                }
            ),

            "state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your state"
                }
            ),
        }