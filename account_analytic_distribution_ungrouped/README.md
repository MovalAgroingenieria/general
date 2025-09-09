.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


# Account Analytic Distribution Simple

Este módulo reemplaza el widget complejo de distribución analítica con un campo **many2one nativo** que permite seleccionar CUALQUIER cuenta analítica directamente, con el estilo y funcionalidad exacta de los campos nativos de Odoo.

## Funcionalidad

- **Campo many2one nativo**: Usa el widget estándar de Odoo con todas sus características
- **Autocompletado y búsqueda**: Funcionalidad completa de búsqueda y filtrado
- **Estilo idéntico**: Exactamente igual a otros campos many2one del sistema
- **Una sola cuenta**: Selección de una cuenta analítica al 100%
- **Sincronización automática**: El campo original `analytic_distribution` se mantiene sincronizado
- **Vista readonly integrada**: Muestra el nombre de la cuenta cuando es de solo lectura

## Ventajas sobre el widget original

1. **Sin limitaciones de plan**: Acceso a todas las cuentas analíticas sin restricciones
2. **Interfaz nativa**: Misma experiencia que otros campos del sistema
3. **Búsqueda avanzada**: Autocompletado, filtros, y todas las características many2one
4. **Mejor rendimiento**: Usa los componentes optimizados de Odoo
5. **Integración perfecta**: No requiere JavaScript personalizado ni assets adicionales

## Implementación técnica

- **Campo computado**: `analytic_account_single` como Many2one hacia `account.analytic.account`
- **Sincronización bidireccional**:
  - `_compute_analytic_account_single()`: Convierte JSON → Many2one
  - `_inverse_analytic_account_single()`: Convierte Many2one → JSON (100%)
- **Herencia de vistas**: Oculta el campo original y muestra el nuevo campo inline

## Instalación

1. Coloca el módulo en tu directorio de addons
2. Actualiza la lista de módulos
3. Instala el módulo `account_analytic_distribution_ungrouped`
4. Recarga la página del navegador (Ctrl+F5) para cargar los nuevos assets

## Uso

Una vez instalado, el campo de distribución analítica en las líneas de factura se mostrará como una tabla donde puedes:

1. Seleccionar cualquier cuenta analítica del dropdown
2. Establecer el porcentaje deseado
3. Agregar múltiples líneas de distribución
4. Ver el total en tiempo real
5. Eliminar líneas no deseadas

## Compatibilidad

- Odoo 16.0
- Requiere los módulos `account` y `analytic`
