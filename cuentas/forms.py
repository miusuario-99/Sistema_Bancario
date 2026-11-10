from django import forms
from .models import Cuenta
from clientes.models import Cliente
from decimal import Decimal

class CuentaForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["numero_cuenta"].required = False
        self.fields["estado"].required = False

        # Mostrar clientes activos al crear una cuenta nueva.
        clientes_activos = Cliente.objects.filter(estado="A")

        if self.instance and self.instance.pk:
            # Al editar, conservar también el cliente actual,
            # aunque esté inactivo.
            cliente_actual = self.instance.cliente

            self.fields["cliente"].queryset = (
                clientes_activos
                | Cliente.objects.filter(pk=cliente_actual.pk)
            )

            # El saldo no se puede modificar al editar.
            self.fields["saldo"].disabled = True

        else:
            self.fields["cliente"].queryset = clientes_activos

            # Las cuentas nuevas deben comenzar con saldo cero.
            self.initial["saldo"] = Decimal("0.00")
            self.fields["saldo"].disabled = True

    def clean_saldo(self):
        saldo = self.cleaned_data.get("saldo")

        if self.instance and self.instance.pk:
            # Verificar el saldo actual almacenado en la base de datos.
            saldo_original = (
                type(self.instance).objects
                .get(pk=self.instance.pk)
                .saldo
            )

            if saldo != saldo_original:
                raise forms.ValidationError(
                    "El saldo no puede modificarse desde este formulario. "
                    "Utilice las operaciones bancarias autorizadas."
                )

        elif saldo != Decimal("0.00"):
            raise forms.ValidationError(
                "Las cuentas nuevas deben crearse con saldo cero. "
                "Utilice la operación de depósito para ingresar dinero."
            )

        return saldo

    def clean_cliente(self):
        cliente = self.cleaned_data["cliente"]

        # No permitir asignar cuentas nuevas a clientes inactivos.
        if not self.instance.pk and cliente.estado != "A":
            raise forms.ValidationError(
                "No se pueden crear cuentas para clientes inactivos."
            )

        # Al editar, si se cambia el cliente, debe estar activo.
        if (
            self.instance.pk
            and cliente.pk != self.instance.cliente_id
            and cliente.estado != "A"
        ):
            raise forms.ValidationError(
                "No se puede asignar la cuenta a un cliente inactivo."
            )

        return cliente

    class Meta:
        model = Cuenta
        fields = "__all__"

        widgets = {
            "numero_cuenta": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Número de cuenta",
                }
            ),

            "cliente": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "tipo_cuenta": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "saldo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Saldo inicial",
                }
            ),

            "estado": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }