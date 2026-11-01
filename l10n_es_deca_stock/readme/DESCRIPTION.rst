This module integrates the generic DECA transport document with the Inventory
application.

From any stock transfer (``stock.picking``) a user can prepare a DECA draft,
pre-filling the loading party, origin and destination locations, goods lines,
quantities and weights from the transfer. The document can then be issued and
printed from the DECA form.

A smart button on the transfer shows the related DECA documents and keeps a
bidirectional link between the transfer and its transport documents.

No applicability is inferred from warehouse names: creating a DECA from a
transfer is an explicit user action.
