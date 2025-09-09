.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
  :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
  :alt: License: AGPL-3

|badge1|


# Account Analytic Distribution Simple

This module replaces the complex analytic distribution widget with a **native many2one field** that allows selecting ANY analytic account directly, with the exact style and functionality of Odoo's native fields.

## Supported Models

- **Account Move Lines** (invoice lines, journal entry lines)

## Functionality

- **Native many2one field**: Uses Odoo's standard widget with all its features
- **Autocomplete and search**: Full search and filtering functionality
- **Identical style**: Exactly the same as other many2one fields in the system
- **Single account**: Selection of one analytic account only
- **Automatic synchronization**: The original `analytic_distribution` field remains synchronized
- **Integrated readonly view**: Displays the account name when in readonly mode

## Advantages over the original widget

1. **No plan limitations**: Access to all analytic accounts without restrictions
2. **Native interface**: Same experience as other system fields
3. **Advanced search**: Autocomplete, filters, and all many2one features
4. **Better performance**: Uses Odoo's optimized components
5. **Seamless integration**: No custom JavaScript or additional assets required

## Technical Implementation

- **Computed field**: `analytic_account_single` as Many2one pointing to `account.analytic.account`
- **Bidirectional synchronization**:
  - `_compute_analytic_account_single()`: Converts JSON → Many2one
  - `_inverse_analytic_account_single()`: Converts Many2one → JSON (100%)
- **View inheritance**:
  - `account.move.line`: Hides original field in invoice and journal entry forms
- **Models extended**:
  - `AccountMoveLine` for invoice lines and journal entries

## Installation

1. Place the module in your addons directory
2. Update the module list
3. Install the `account_analytic_distribution_ungrouped` module
4. Reload the browser page (Ctrl+F5) to load the new assets

## Usage

Once installed, the analytic distribution field will be displayed as a simple many2one field in:

### Invoice Lines
In invoice lines and journal entry lines you can:
1. Select any analytic account from the dropdown
2. The selected account will be automatically assigned 100%
3. View the account name when in readonly mode

## Future Enhancements

Support for bank statement lines is planned for future versions when used in conjunction with OCA reconciliation modules.

## Compatibility

- Odoo 16.0
- Requires the `account` and `analytic` modules
