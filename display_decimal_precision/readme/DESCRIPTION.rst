This module allows separating **calculation precision** from
**display precision** for decimal (float) fields in Odoo.

While Odoo internally computes values using a fixed precision,
the number of decimals shown to the user is often required to be different
(e.g. show 2 decimals while computing with 6).

This module introduces:

* A configurable **display precision layer** based on logical categories
  (e.g. *Product Price*, *Unit of Measure*).
* Global configuration through **Settings** (``res.config.settings``),
  stored in system parameters.
* Automatic application of display precision to field metadata sent to
  the UI and to QWeb reports.

The stored value is **never altered**: only the way decimals are
*displayed* is affected.

.. note::

   Currency rounding and monetary precision are **not modified** by this
   module and remain governed by standard Odoo currency settings.
