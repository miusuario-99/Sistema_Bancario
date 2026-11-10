from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm


class UsuarioForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombres",
        max_length=150,
        required=True,
    )

    last_name = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=True,
    )

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Este correo electrónico ya está registrado."
            )

        return email

    groups = forms.ModelMultipleChoiceField(
        label="Grupos",
        queryset=Group.objects.filter(
            name__in=["Supervisor", "Cajero"]
        ).order_by("name"),
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "groups",
            "password1",
            "password2",
        ]
        labels = {
            "username": "Nombre de usuario",
        }