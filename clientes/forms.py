from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):

    class Meta:
        model = Cliente

        fields = [
            "dni",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "direccion",
            "telefono",
            "correo",
            "estado",
        ]

        widgets = {
            "dni": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese DNI"
            }),

            "nombres": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese nombres"
            }),

            "apellidos": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese apellidos"
            }),

            "fecha_nacimiento": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "direccion": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese dirección"
            }),

            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese teléfono"
            }),

            "correo": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "correo@empresa.com"
            }),

            "estado": forms.Select(attrs={
                "class": "form-select"
            }),
        }

    def clean_dni(self):
        dni = self.cleaned_data["dni"]

        if not dni.isdigit():
            raise forms.ValidationError(
                "El DNI solo debe contener números."
            )

        if len(dni) != 8:
            raise forms.ValidationError(
                "El DNI debe tener exactamente 8 dígitos."
            )

        return dni