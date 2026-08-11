\# 🏦 Sistema Bancario



Sistema web de gestión bancaria desarrollado con Python y Django.



El proyecto permite administrar clientes, cuentas bancarias y movimientos financieros, incorporando generación de reportes, control de acceso por roles y un sistema de auditoría de operaciones.



\---



\## 📋 Descripción



El Sistema Bancario es una aplicación web desarrollada con Django que permite gestionar las principales operaciones de una entidad bancaria.



El sistema incorpora:



\- Gestión de clientes.

\- Gestión de cuentas bancarias.

\- Depósitos.

\- Retiros.

\- Transferencias.

\- Consulta del historial de movimientos.

\- Generación de reportes en PDF.

\- Exportación de información a Excel.

\- Sistema de auditoría.

\- Control de acceso mediante roles.

\- Dashboard administrativo.

\- Autenticación de usuarios.



\---



\## 🚀 Funcionalidades



\### 👥 Clientes



Permite:



\- Registrar clientes.

\- Editar clientes.

\- Eliminar clientes.

\- Consultar clientes.

\- Buscar clientes.

\- Paginar resultados.

\- Exportar información.



\### 💳 Cuentas



Permite:



\- Crear cuentas bancarias.

\- Generar números de cuenta.

\- Editar cuentas.

\- Eliminar cuentas.

\- Consultar cuentas.

\- Buscar cuentas.

\- Visualizar saldo.

\- Consultar estado de las cuentas.

\- Generar reportes PDF.

\- Exportar información a Excel.



\### 💰 Movimientos bancarios



El sistema permite realizar:



\- Depósitos.

\- Retiros.

\- Transferencias entre cuentas.

\- Consulta del historial de movimientos.



Cada operación modifica el saldo de la cuenta y registra la información correspondiente.



\### 📊 Reportes



El sistema permite generar reportes en:



\- PDF.

\- Excel.



Los reportes incluyen información de:



\- Dashboard.

\- Clientes.

\- Cuentas.

\- Movimientos.

\- Auditoría.



\### 🔐 Auditoría



El sistema registra las operaciones realizadas por los usuarios.



La auditoría permite consultar:



\- Usuario.

\- Módulo.

\- Acción.

\- Descripción.

\- Fecha y hora.



También permite exportar la información de auditoría a:



\- PDF.

\- Excel.



\### 👤 Control de acceso



El sistema utiliza grupos de Django para controlar el acceso.



\#### Administrador



Tiene acceso completo al sistema.



\#### Supervisor



Tiene acceso a:



\- Reportes.

\- Auditoría.

\- Funcionalidades administrativas autorizadas.



\#### Cajero



Tiene acceso a las operaciones bancarias correspondientes, como:



\- Clientes.

\- Cuentas.

\- Depósitos.

\- Retiros.

\- Transferencias.

\- Historial.



Los accesos restringidos también están protegidos directamente en las vistas para evitar el acceso mediante URL.



\---



\## 🛠️ Tecnologías utilizadas



\- Python

\- Django 5.2.16

\- SQLite para desarrollo

\- PostgreSQL mediante `psycopg2-binary`

\- MySQL mediante `mysqlclient`

\- ReportLab

\- OpenPyXL

\- Pillow

\- HTML5

\- CSS3

\- JavaScript

\- Bootstrap

\- Bootstrap Icons



\---



\## 📁 Estructura del proyecto



```text

Sistema\_Bancario/

│

├── auditoria/

│   ├── migrations/

│   ├── templates/

│   ├── admin.py

│   ├── models.py

│   ├── reportes.py

│   ├── signals.py

│   ├── urls.py

│   ├── utils.py

│   └── views.py

│

├── banco/

│   ├── static/

│   ├── utils/

│   ├── settings.py

│   ├── urls.py

│   ├── views.py

│   ├── asgi.py

│   └── wsgi.py

│

├── clientes/

│   ├── migrations/

│   ├── admin.py

│   ├── forms.py

│   ├── models.py

│   ├── urls.py

│   └── views.py

│

├── cuentas/

│   ├── migrations/

│   ├── templates/

│   ├── admin.py

│   ├── forms.py

│   ├── models.py

│   ├── urls.py

│   └── views.py

│

├── movimientos/

│   ├── migrations/

│   ├── admin.py

│   ├── models.py

│   ├── urls.py

│   └── views.py

│

├── reportes/

│   ├── migrations/

│   ├── templates/

│   ├── admin.py

│   ├── models.py

│   ├── urls.py

│   ├── utils.py

│   └── views.py

│

├── usuarios/

│   ├── migrations/

│   ├── templatetags/

│   ├── admin.py

│   ├── decorators.py

│   ├── models.py

│   ├── urls.py

│   └── views.py

│

├── static/

│   ├── css/

│   ├── img/

│   └── js/

│

├── templates/

│   ├── clientes/

│   ├── movimientos/

│   ├── registration/

│   ├── base.html

│   ├── dashboard.html

│   ├── navbar.html

│   └── sidebar.html

│

├── manage.py

├── requirements.txt

├── .gitignore

└── .env

