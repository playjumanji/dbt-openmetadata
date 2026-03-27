import re
from typing import Optional, Tuple
import pytest

def parse_unique_id(run_result: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract (schema, table, column) from a dbt run_results entry.
    column is None for table-level tests.
    Strategy:
      1. Try to parse unique_id patterns like:
         test.<schema>.unique_<maybe_stg_><table>_<column>.<hash>
         or test.<schema>.<something>_<table>_<column>.<hash>
      2. If that fails, fallback to parsing compiled_code:
         - find the last FROM "adapter"."schema"."table" or FROM "schema"."table"
         - find column via '(\w+)\s+as\s+unique_field' or alias 'as unique_field'
    """
    uid = (run_result.get("unique_id") or "").strip()
    compiled = (run_result.get("compiled_code") or "").strip()

    # 1) Parse unique_id robustly
    if uid:
        # Remove trailing hash segment if it looks hex
        parts = uid.split(".")
        if parts and re.fullmatch(r"[0-9a-f]{6,}", parts[-1]):
            parts = parts[:-1]

        # Expect at least: test, schema, candidate
        if len(parts) >= 3 and parts[0] == "test":
            schema = parts[1]
            # candidate may contain multiple segments joined by underscores;
            # try to find a table + column at the tail.
            candidate = ".".join(parts[2:])  # join remaining to preserve underscores/dots
            # Remove common prefixes like unique, unique_stg, unique_table, etc.
            candidate = re.sub(r'^(unique(?:_stg|_table|)_)', '', candidate, flags=re.IGNORECASE)

            # If candidate contains known separators, assume last segment is column, previous is table
            segs = candidate.split("_")
            if len(segs) >= 2:
                column = segs[-1]
                table = "_".join(segs[:-1])
                return (schema or None, table or None, column or None)
            else:
                # single segment — treat as table-level
                return (schema or None, candidate or None, None)

    # 2) Fallback to compiled_code parsing
    schema = table = column = None

    if compiled:
        # Look for FROM clause. Prefer the last occurrence (in case of nested queries).
        from_matches = list(re.finditer(r'from\s+((?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+)){1,2})',
                                       compiled, re.IGNORECASE))
        if from_matches:
            last = from_matches[-1].group(1)
            # Split dotted identifiers (strip quotes and whitespace)
            parts = [p.strip().strip('"') for p in re.split(r'\s*\.\s*', last)]
            # last part = table, previous part = schema (or adapter then schema)
            if len(parts) >= 2:
                table = parts[-1]
                schema = parts[-2]
            elif len(parts) == 1:
                table = parts[0]

        # Detect column by aliasing to unique_field
        mcol = re.search(r'(\b[\w\."]+)\s+as\s+unique_field\b', compiled, re.IGNORECASE)
        if mcol:
            col_raw = mcol.group(1).strip().strip('"')
            # if col_raw is dotted like schema.table.col or table.col, take last part
            column = col_raw.split(".")[-1]

    return (schema or None, table or None, column or None)


def parse_from_compiled(compiled_code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse schema, table, column from dbt compiled SQL.
    column is None for table-level tests.

    Strategy:
      - Find the last FROM clause that points to a table (skip pure subquery FROMs).
      - Extract adapter/schema/table or schema/table, handling quoted identifiers and spaces.
      - For column: look for '<col> as unique_field' (dotted or aliased).
    """
    if not compiled_code:
        return (None, None, None)
    sql = compiled_code

    # Normalize whitespace (preserve case)
    sql_norm = re.sub(r'\s+', ' ', sql, flags=re.UNICODE).strip()

    # Regex to capture FROM target (handles quoted identifiers, dots, and spaces around dots,
    # or parenthesized subqueries)
    from_pattern = re.compile(
        r'\bfrom\b\s*('
        r'(?:\([^)]*\))'                                # a parenthesized subquery
        r'|'
        r'(?:(?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+))*)'  # dotted identifiers with optional spaces
        r')',
        flags=re.IGNORECASE
    )

    from_matches = list(from_pattern.finditer(sql_norm))
    schema = table = column = None

    # Helper to normalize a dotted identifier string into parts (strip quotes & whitespace)
    def split_identifier(s: str):
        parts = [p.strip().strip('"') for p in re.split(r'\s*\.\s*', s)]
        return [p for p in parts if p != '']

    # Choose the last FROM that looks like a table (not a pure subquery), walking backwards
    chosen = None
    for m in reversed(from_matches):
        token = m.group(1).strip()
        # If token starts with '(' and contains 'select', treat as subquery and skip
        if token.startswith('(') and re.search(r'\bselect\b', token, re.IGNORECASE):
            continue
        chosen = token
        break

    # If none chosen (all FROMs are subqueries), try to find a FROM inside common WITH or earlier FROMs by
    # checking earlier matches again but allow subquery that contains a FROM to locate an inner table.
    if chosen is None and from_matches:
        # try to inspect the earliest FROM's content for a table reference
        for m in from_matches:
            token = m.group(1).strip()
            # look inside token for a nested FROM that is a table reference
            inner = re.search(r'\bfrom\b\s*((?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+))*)', token, re.IGNORECASE)
            if inner:
                chosen = inner.group(1).strip()
                break

    if chosen:
        # strip surrounding parentheses if present
        chosen = chosen.strip()
        if chosen.startswith('(') and chosen.endswith(')'):
            chosen = chosen[1:-1].strip()

        # remove any trailing alias: " ... " as alias OR ... alias
        chosen_no_alias = re.split(r'\s+as\s+|\s+', chosen, flags=re.IGNORECASE)[0]
        parts = split_identifier(chosen_no_alias)
        if len(parts) >= 2:
            # pick last two as schema.table (adapter.schema.table -> take schema & table)
            table = parts[-1]
            schema = parts[-2]
        elif len(parts) == 1:
            table = parts[0]

    # Column detection: look for '<expr> as unique_field' in the SELECT list (prefer first occurrence)
    mcol = re.search(r'([\w\."`]+)\s+as\s+unique_field\b', sql, re.IGNORECASE)
    if mcol:
        col_raw = mcol.group(1).strip().strip('"').strip('`')
        column = col_raw.split('.')[-1]

    # If not found, also check for pattern like 'select .*?(\w+)\s+as\s+unique_field' across newlines
    if column is None:
        mcol2 = re.search(r'select\s+(.*?)\bfrom\b', sql, re.IGNORECASE | re.DOTALL)
        if mcol2:
            select_clause = mcol2.group(1)
            m_inner = re.search(r'([\w\."`]+)\s+as\s+unique_field', select_clause, re.IGNORECASE)
            if m_inner:
                col_raw = m_inner.group(1).strip().strip('"').strip('`')
                column = col_raw.split('.')[-1]

    return (schema or None, table or None, column or None)