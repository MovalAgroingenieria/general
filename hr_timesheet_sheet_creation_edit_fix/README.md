# HR Timesheet Sheet Creation and Edit Fix

## Description

This module add by-pass method _check_can_update_timesheet to always return true

## Functionality

The module inherits the `account.analytic.line` model and overrides the `_check_can_update_timesheet` method.

## Overridden Method

### `_check_can_update_timesheet(self)`

This method:
- Return true to enable creation and editing of timesheets and their lines


## Installation

1. Place the module in `moval_addons/general/`
2. Update module list
3. Install from Apps

## Dependencies

- `hr_timesheet_sheet`: Odoo base accounting module

## Author

Moval Agroingeniería - https://www.moval.es