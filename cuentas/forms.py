from django import forms
from .models import Cuenta


class CuentaForm(forms.ModelForm):

    class Meta:

        model = Cuenta

        fields = "__all__"


        widgets = {

            "numero_cuenta": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Número de cuenta"
                }
            ),


            "cliente": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),


            "tipo_cuenta": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),


            "saldo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Saldo inicial"
                }
            ),


            "estado": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

        }