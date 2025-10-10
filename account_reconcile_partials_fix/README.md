# Account Reconciliation Partials Custom

## Description

This module customizes the behavior of the `_create_reconciliation_partials` method from the `account.move.line` model to adapt it to Moval Agroingeniería's specific requirements.

## Functionality

The module inherits the `account.move.line` model and overrides the `_create_reconciliation_partials` method that handles:

1. Creating partial reconciliations between accounting move lines
2. Managing currency exchange differences when applicable
3. Returning an `account.partial.reconcile` recordset

## Overridden Method

### `_create_reconciliation_partials(self)`

This method:
- Prepares values for creating partial reconciliations
- Creates `account.partial.reconcile` records
- Handles exchange difference entries if necessary
- Returns the recordset of created partial reconciliations

## Customization

The current code is identical to the original method. To customize:

1. Modify the logic in `models/account_move_line.py`
2. Adjust values in `vals_list` according to your needs
3. Customize `partials` creation if necessary
4. Modify exchange difference handling if applicable

## Installation

1. Place the module in `moval_addons/general/`
2. Update module list
3. Install from Apps

## Dependencies

- `account`: Odoo base accounting module

## Author

Moval Agroingeniería - https://www.moval.es