Menu structure
~~~~~~~~~~~~~~

After installation, a top-level menu **Entities** appears with the following
structure:

::

  Entities
  ├── Management
  │   ├── Primary Entities
  │   └── Secondary Members
  └── Technical  (managers only)
      └── Relationships (Members)

Managing primary entities
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to **Entities > Management > Primary Entities**.
2. Click **Create** to add a new primary entity (defaults to *Company* type).
3. Fill in the name, optional *Entity Global Code*, and contact details.
4. Once the entity has members, use the **Members** stat button on the form to
   view and manage them directly.

Managing secondary members
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to **Entities > Management > Secondary Members**.
2. Click **Create** to add a new secondary member (defaults to *Person* type).
3. Fill in the name, optional *Entity Global Code*, and contact details.
4. In the **Belongs to Entities** tab you can add or edit the entities this
   member belongs to (editable inline list). Each relationship may have:

   * A **local member code** (unique within each entity).
   * A **sequence** number for display ordering.
   * Free-text **notes**.

Managing relationships directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Managers can go to **Entities > Technical > Relationships (Members)** to view
and edit the full relationship table. The list view is editable with drag & drop
reordering via the sequence handle.

Constraints:

* A member cannot appear twice in the same entity and company (SQL unique
  constraint).
* The local member code must be unique within each primary entity.

Bulk wizard: mark/unmark entity type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From any **Contacts** list view:

1. Select one or more contacts using the checkboxes.
2. Open the **Actions** dropdown and choose **Mark/Unmark Entity Type**.
3. Pick one of the four options:

   * Mark as Primary Entity
   * Unmark as Primary Entity
   * Mark as Secondary Member
   * Unmark as Secondary Member

4. Click **Apply**.

The wizard validates that the operation does not conflict with the contacts'
current type (e.g. you cannot mark a secondary member as a primary entity
without unmarking it first). If conflicts are detected, a user-friendly error
message lists the affected contact names.

Cascade deletion behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~

When a partner (either primary entity or secondary member) is deleted, only the
**relationships** (``general.entity.member``) referencing it are removed.
The other partner involved in the relationship is **never** deleted.

Archiving relationships
~~~~~~~~~~~~~~~~~~~~~~~

Relationships support the ``active`` field. You can archive a relationship
(uncheck the *Active* toggle) to hide it from default views without losing the
data. Archived relationships can be found using the *Inactive* search filter.
