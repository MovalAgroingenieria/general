This module adds configurable vote types and per-partner vote records.

Vote types support Jinja2 formulas with the ``partner`` variable, integer or
decimal results, and optional domain filters to define which partners are
included in each computation.

The module also provides tools to recompute votes manually or by cron and keeps
only vote lines that still match each vote type domain.
