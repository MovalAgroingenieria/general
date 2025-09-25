# Google Meet Integration for Appointment Booking

Este módulo extiende el módulo **Zehntech Appointment Booking CE** para generar automáticamente enlaces de Google Meet usando una cuenta específica de Google para todas las citas online.

## Características

- ✅ Generación automática de enlaces de Google Meet para citas
- ✅ Integración con cuenta corporativa específica (movalagroingenieria)
- ✅ Compatible con TLDV para grabación automática de reuniones
- ✅ Reemplaza enlaces de videollamada de Odoo por Google Meet
- ✅ Configuración por tipo de cita (habilitar/deshabilitar Google Meet)
- ✅ Plantillas personalizables para descripciones de reuniones
- ✅ Autenticación OAuth segura
- ✅ No modifica el código original de Zehntech

## Requisitos Previos

### 1. Módulos de Odoo
- `appointment_booking_ce` (Zehntech) - Debe estar instalado
- `calendar` (Odoo core)
- `website` (Odoo core)

### 2. Librerías de Python
Instalar las siguientes librerías en el entorno virtual de Odoo:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 3. Configuración en Google Cloud Console

1. **Crear proyecto en Google Cloud Console**:
   - Ir a https://console.cloud.google.com/
   - Crear un nuevo proyecto o seleccionar uno existente

2. **Habilitar APIs necesarias**:
   - Google Calendar API
   - Google Meet API (si está disponible)

3. **Crear credenciales OAuth 2.0**:
   - Ir a "Credenciales" → "Crear credenciales" → "ID de cliente OAuth 2.0"
   - Tipo de aplicación: "Aplicación web"
   - URIs de redirección autorizados: `https://tu-dominio.com/google_meet/oauth/callback`

4. **Obtener Client ID y Client Secret**

## Instalación

### 1. Instalar el módulo

1. Copiar el módulo a la carpeta de addons:
   ```
   /path/to/odoo/addons/moval_google_meet_integration/
   ```

2. Actualizar la lista de aplicaciones en Odoo
3. Buscar e instalar "Google Meet Integration for Appointment Booking"

### 2. Configurar Google Meet

1. **Ir a Configuración → Ajustes Generales**
2. **Buscar sección "Google Meet Integration"**
3. **Activar "Enable Google Meet Integration"**
4. **Completar los campos**:
   - **Google Account Email**: `movalagroingenieria@gmail.com`
   - **Client ID**: El Client ID de Google Cloud Console
   - **Client Secret**: El Client Secret de Google Cloud Console
   - **Calendar ID**: `primary` (o ID específico del calendario)

5. **Autorizar la integración**:
   - Hacer clic en "Authorize Google Meet"
   - Iniciar sesión con la cuenta de Google (`movalagroingenieria@gmail.com`)
   - Conceder permisos necesarios
   - Verificar que aparezca "✓ Google Meet integration is authorized"

6. **Probar la conexión**:
   - Hacer clic en "Test Connection"
   - Verificar que aparezca mensaje de éxito

### 3. Configurar tipos de cita

1. **Ir a Calendario → Configuración → Tipos de reserva**
2. **Para cada tipo de cita que quiera usar Google Meet**:
   - Abrir el formulario del tipo de cita
   - En la sección "Video Conference Settings":
     - Activar "Use Google Meet"
     - Activar "Auto Record with TLDV" (si se desea)
   - En la pestaña "Google Meet Settings":
     - Personalizar plantilla de descripción si es necesario

## Uso

### Funcionamiento Automático

Una vez configurado, el sistema funciona automáticamente:

1. **Cliente reserva cita online** → El sistema genera automáticamente un enlace de Google Meet
2. **Se crea evento en Google Calendar** → Con la cuenta `movalagroingenieria@gmail.com`
3. **Cliente recibe confirmación** → Con el enlace de Google Meet incluido
4. **TLDV detecta la reunión** → Y la graba automáticamente (si está configurado)

### Gestión Manual

- **Ver enlaces generados**: En el formulario del evento de calendario
- **Regenerar enlace**: Botón "Regenerate Google Meet" en eventos
- **Verificar estado**: Indicador visual en vistas de lista y kanban

## Estructura del Módulo

```
moval_google_meet_integration/
├── __manifest__.py                    # Configuración del módulo
├── __init__.py                       # Importaciones principales
├── models/
│   ├── __init__.py
│   ├── res_config_settings.py        # Configuración Google API
│   ├── google_meet_service.py        # Servicio Google Calendar API
│   ├── calendar_booking.py           # Extensión calendar.booking.type
│   └── calendar_event.py             # Extensión calendar.event
├── controllers/
│   ├── __init__.py
│   └── main.py                       # Controlador OAuth y reservas
├── views/
│   ├── res_config_settings_views.xml # Vista configuración
│   ├── calendar_booking_views.xml    # Vistas tipos de cita
│   └── calendar_event_views.xml      # Vistas eventos
└── security/
    └── ir.model.access.csv           # Permisos de acceso
```

## Flujo de Integración

1. **Reserva de cita**:
   ```
   Cliente completa formulario web
   → Zehntech crea evento calendar.event
   → Nuestro módulo intercepta la creación
   → Se genera Google Meet si está habilitado
   → Se actualiza meeting_url con enlace de Google Meet
   ```

2. **Generación de Google Meet**:
   ```
   Crear evento en Google Calendar
   → Configurar conferenceData para Meet
   → Obtener enlace de Meet generado
   → Almacenar en campos google_meet_url y meeting_url
   → TLDV detecta reunión automáticamente
   ```

## Puntos de Extensión

### Modelo calendar.booking.type
- `use_google_meet`: Activar/desactivar Google Meet por tipo
- `google_meet_auto_record`: Control grabación TLDV
- `google_meet_description_template`: Plantilla personalizada

### Modelo calendar.event
- `google_meet_url`: Enlace de Google Meet generado
- `google_event_id`: ID del evento en Google Calendar
- `google_meet_generated`: Estado de generación

### Controlador
- Intercepción en `/website/calendar/book`
- Callback OAuth en `/google_meet/oauth/callback`

## Solución de Problemas

### Error: "Google APIs not installed"
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Error: "Connection test failed"
- Verificar credenciales Google Cloud Console
- Confirmar que APIs están habilitadas
- Verificar URI de redirección configurada

### Error: "Authorization failed"
- Verificar que la cuenta de Google tiene permisos
- Confirmar Client ID y Client Secret
- Verificar que el dominio está autorizado en Google Cloud Console

### Google Meet no se genera automáticamente
- Verificar que "Use Google Meet" está activado en el tipo de cita
- Confirmar que la integración está autorizada
- Revisar logs de Odoo para errores específicos

## Compatibilidad

- **Odoo**: 16.0 Community Edition
- **Zehntech Appointment Booking**: v16.0.1.1.0+
- **Python**: 3.8+
- **Google APIs**: Versión actual

## Licencia

AGPL-3.0 - Ver archivo LICENSE para más detalles.

## Soporte

Para soporte técnico, contactar con el equipo de desarrollo de Moval Agroingeniería.