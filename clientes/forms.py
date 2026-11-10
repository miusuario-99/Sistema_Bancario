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
        dni = self.cleaned_data["dni"].strip()
        return dni

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()

        existe = Cliente.objects.filter(
            correo__iexact=correo
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if existe:
            raise forms.ValidationError(
                "Este correo electrónico ya está registrado."
            )

        return correo