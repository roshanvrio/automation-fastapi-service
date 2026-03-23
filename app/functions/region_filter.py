import re
from typing import Optional

CLAUSE_PATTERN = re.compile(
    r"\b(ORDER\s+BY|GROUP\s+BY|LIMIT|OFFSET)\b",
    re.IGNORECASE,
)


def apply_region_filter(
    base_query: str,
    region: Optional[str],
    column_name: str = "region",
) -> str:
    """Append a region filter condition to a flat SQL query.

    Inserts ``WHERE column = :region`` or ``AND column = :region`` before
    any trailing GROUP BY / ORDER BY / LIMIT / OFFSET clause.

    Use this for simple (non-CTE) queries.  For CTE queries where the
    filter must go inside a specific block, use :func:`build_region_clause`
    instead.
    """
    if not region or region.strip().upper() == "ALL":
        return base_query

    condition = f"{column_name} = :region"
    query = base_query.strip()

    # Find where to insert (before ORDER BY / GROUP BY etc.)
    match = CLAUSE_PATTERN.search(query)

    if match:
        split_index = match.start()
        main_query = query[:split_index].strip()
        tail = query[split_index:]
    else:
        main_query = query
        tail = ""

    if _has_outer_where(main_query):
        main_query += f" AND {condition}"
    else:
        main_query += f" WHERE {condition}"

    return f"{main_query} {tail}".strip()


def build_region_clause(
    region: Optional[str],
    column_name: str = "region",
    alias: Optional[str] = None,
) -> str:
    """Return a SQL fragment for manual injection into CTE queries.

    Returns ``AND alias.column = :region`` when a region is provided,
    or an empty string otherwise.  The caller embeds the result via
    f-string at the exact position needed inside a CTE block.

    Example::

        rf = build_region_clause(region)
        query = f\"\"\"
            WITH cte AS (
                SELECT * FROM table
                WHERE status = 'OPEN'
                  {rf}
            )
            SELECT * FROM cte
        \"\"\"
    """
    if not region or region.strip().upper() == "ALL":
        return ""

    prefix = f"{alias}." if alias else ""
    return f"AND {prefix}{column_name} = :region"


def get_region_params(region: Optional[str]) -> dict:
    """Return a parameter dict suitable for parameterized query execution.

    Returns ``{"region": region}`` when a meaningful region is provided,
    otherwise an empty dict.
    """
    if not region or region.strip().upper() == "ALL":
        return {}
    return {"region": region}


def _has_outer_where(query: str) -> bool:
    """Return True if *query* contains a WHERE keyword (case-insensitive)."""
    return bool(re.search(r"\bWHERE\b", query, re.IGNORECASE))