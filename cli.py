#!/usr/bin/env python3
"""
@file cli.py
@brief Job Application Tracker CLI using a pluggable Storage backend (JSON today, DB-ready).

@details
  Tables (logical schema):
    - companies:     company_id, name, location, industry, website, source, rating, created_at
    - applications:  application_id, company_id, position, status, employment_type, salary_min, salary_max, currency,
                     job_url, applied_at, last_update, notes
    - contacts:      contact_id, company_id, name, title, email, phone, notes, last_contacted
    - stages:        stage_id, application_id, stage, date, outcome, notes

  Storage Abstraction:
    - Storage (Protocol): ensure_all(), read(table), write(table, rows)
    - JSONStorage (default): persists each table as <data_dir>/<table>.json
    - DBStorage (skeleton): placeholder showing how to wire in a DB later

  Highlights:
    - Interactive prompts if IDs/names aren’t provided.
    - Shell completion command.
    - Consistent logging, validation, and error messaging.

  Usage:
    python cli.py init
    python cli.py add-company
    python cli.py add-application
    python cli.py update-application
    python cli.py remove application
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Protocol

import click

# =============================================================================
# Schema (backend-agnostic)
# =============================================================================
TABLES: Dict[str, Dict[str, Any]] = {
    "companies": {
        "columns": [
            "company_id", "name", "location", "industry", "website", "source", "rating", "created_at"
        ],
        "id_field": "company_id",
        "id_prefix": "cmp_",
    },
    "applications": {
        "columns": [
            "application_id", "company_id", "position", "status", "employment_type",
            "salary_min", "salary_max", "currency", "job_url", "applied_at", "last_update", "notes"
        ],
        "id_field": "application_id",
        "id_prefix": "app_",
    },
    "contacts": {
        "columns": [
            "contact_id", "company_id", "name", "title", "email", "phone", "notes", "last_contacted"
        ],
        "id_field": "contact_id",
        "id_prefix": "ctc_",
    },
    "stages": {
        "columns": [
            "stage_id", "application_id", "stage", "date", "outcome", "notes"
        ],
        "id_field": "stage_id",
        "id_prefix": "stg_",
    },
}

COMMON_STATUSES: List[str] = [
    "new", "applied", "recruiter", "phone", "technical", "onsite", "offer", "accepted", "rejected", "withdrawn",
]

# =============================================================================
# Logging / Globals
# =============================================================================
CWD = os.getcwd()
LOG_DIR = os.path.join(CWD, "logs")
LOG_FILE = os.path.join(LOG_DIR, "cli.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

# =============================================================================
# Storage Abstraction
# =============================================================================
class Storage(Protocol):
    """
    @brief Abstract storage protocol for table persistence.
    """
    def ensure_all(self) -> None:
        """@brief Ensure all table containers exist."""
        ...

    def read(self, table: str) -> List[Dict[str, Any]]:
        """
        @brief Read all rows for a table.
        @param table Table name.
        @return List of dict rows.
        """
        ...

    def write(self, table: str, rows: List[Dict[str, Any]]) -> None:
        """
        @brief Overwrite all rows for a table.
        @param table Table name.
        @param rows Whole-table rows to persist.
        """
        ...


class JSONStorage:
    """
    @brief JSON-backed implementation of Storage.
    @details Stores each table in <data_dir>/<table>.json.
    """
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, table: str) -> str:
        if table not in TABLES:
            raise click.ClickException(f"Unknown table: {table}")
        return os.path.join(self.data_dir, f"{table}.json")

    def ensure_all(self) -> None:
        """@brief Ensure all JSON files exist as empty lists."""
        for t in TABLES.keys():
            p = self._path(t)
            if not os.path.exists(p):
                try:
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump([], f)
                except OSError as e:
                    raise click.ClickException(f"Failed to create {p}: {e}")

    def read(self, table: str) -> List[Dict[str, Any]]:
        """@copydoc Storage.read"""
        p = self._path(table)
        try:
            with open(p, "r", encoding="utf-8") as f:
                text = f.read().strip()
                return json.loads(text) if text else []
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Corrupted data file: {p} ({e})")
        except OSError as e:
            raise click.ClickException(f"Failed to read {p}: {e}")

    def write(self, table: str, rows: List[Dict[str, Any]]) -> None:
        """@copydoc Storage.write"""
        p = self._path(table)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
        except OSError as e:
            raise click.ClickException(f"Failed to write {p}: {e}")


class DBStorage:  # Placeholder example for later
    """
    @brief Skeleton DB-backed storage implementation.
    @details Replace methods with real DB logic (e.g., SQLite/Postgres via SQLAlchemy).
    """
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        # TODO: initialize engine/session, create tables (migrations), etc.

    def ensure_all(self) -> None:
        # TODO: ensure schema exists
        raise NotImplementedError("DBStorage.ensure_all not implemented yet.")

    def read(self, table: str) -> List[Dict[str, Any]]:
        # TODO: SELECT * FROM <table>;
        raise NotImplementedError("DBStorage.read not implemented yet.")

    def write(self, table: str, rows: List[Dict[str, Any]]) -> None:
        # TODO: TRUNCATE/DELETE + bulk INSERT
        raise NotImplementedError("DBStorage.write not implemented yet.")

# =============================================================================
# Helpers (time, ids, printing, filters)
# =============================================================================
def _now_s() -> int:
    """@brief Current unix time (seconds)."""
    return int(time.time())

def _new_id(prefix: str) -> str:
    """@brief Generate unique-ish ID via time_ns."""
    return f"{prefix}{time.time_ns()}"

def _lookup_company_id_by_name(name: str, companies: Sequence[Dict[str, Any]]) -> Optional[str]:
    """@brief Find company_id by case-insensitive company name."""
    target = name.strip().lower()
    for c in companies:
        if c.get("name", "").strip().lower() == target:
            return c.get("company_id")
    return None

def _print_table(headers: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    """
    @brief Print a simple text table with dynamic column widths.
    @param headers Header names in order.
    @param rows Iterable of dict-like rows.
    """
    str_rows: List[List[str]] = []
    widths = [len(h) for h in headers]
    for r in rows:
        row_vals: List[str] = []
        for i, h in enumerate(headers):
            sval = "" if r.get(h) is None else str(r.get(h))
            row_vals.append(sval)
            widths[i] = max(widths[i], len(sval))
        str_rows.append(row_vals)

    header_row = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep = "-+-".join("-" * widths[i] for i in range(len(headers)))
    click.echo(header_row)
    click.echo(sep)
    for r in str_rows:
        click.echo(" | ".join(r[i].ljust(widths[i]) for i in range(len(headers))))

def _filter_delete(rows: List[Dict[str, Any]], predicate) -> Tuple[List[Dict[str, Any]], int]:
    """@brief Return (rows_without_matches, removed_count)."""
    kept: List[Dict[str, Any]] = []
    removed = 0
    for r in rows:
        if predicate(r):
            removed += 1
        else:
            kept.append(r)
    return kept, removed

# --------------------------- Interactive selection helpers ------------------
def _choice_label(row: Dict[str, Any], parts: Sequence[str]) -> str:
    """@brief Join selected fields for compact menu labels."""
    values = [str(row.get(p, "")) for p in parts]
    return " | ".join(v for v in values if v)

def _menu_select(
    rows: Sequence[Dict[str, Any]],
    id_field: str,
    label_fields: Sequence[str],
    prompt_text: str,
) -> Dict[str, Any]:
    """
    @brief Prompt the user to pick a row from a numbered list.
    @param rows Candidate rows.
    @param id_field Field that uniquely identifies rows.
    @param label_fields Fields to display for context.
    @param prompt_text Prompt content.
    @return Selected row.
    """
    if not rows:
        raise click.ClickException("No records available to choose from.")
    display = [f"[{i+1}] {_choice_label(r, label_fields)} ({r.get(id_field)})" for i, r in enumerate(rows)]
    click.echo("\n".join(display))
    idx = click.prompt(prompt_text, type=click.IntRange(1, len(rows)))
    return rows[idx - 1]

def _select_company_interactive(companies: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return _menu_select(companies, "company_id", ("name", "location", "industry"), "Select company number")

def _select_application_interactive(apps: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return _menu_select(apps, "application_id", ("application_id", "position", "company_id", "status"), "Select application number")

def _select_contact_interactive(contacts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return _menu_select(contacts, "contact_id", ("name", "title", "company_id"), "Select contact number")

def _select_stage_interactive(stages: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return _menu_select(stages, "stage_id", ("stage_id", "application_id", "stage", "date", "outcome"), "Select stage number")

# =============================================================================
# Shell completion helpers
# =============================================================================
def _get_storage_from_ctx(ctx: click.Context) -> Storage:
    """
    @brief Retrieve Storage from Click context, with a sane fallback.
    @param ctx Click context.
    @return Storage instance.
    """
    root = ctx.find_root()
    st = (root.obj or {}).get("storage")
    if st is None:
        # Fallback to default JSON dir if shell calls completion before CLI init.
        st = JSONStorage(data_dir=os.path.join(CWD, "data"))
        root.obj = {"storage": st}
    return st  # type: ignore[return-value]

def _completion_items(strings: List[Tuple[str, Optional[str]]]) -> List[Any]:
    """@brief Build Click CompletionItem list with optional help text."""
    items: List[Any] = []
    try:
        CompletionItem = click.shell_completion.CompletionItem  # type: ignore[attr-defined]
        for value, help_text in strings:
            items.append(CompletionItem(value=value, help=help_text) if help_text else CompletionItem(value=value))
    except Exception:
        items = [s[0] for s in strings]  # fallback
    return items

def complete_tables(ctx, _param, incomplete: str):
    vals = [k for k in TABLES.keys() if k.startswith(incomplete.lower())]
    return _completion_items([(v, "table") for v in sorted(vals)])

def complete_company_ids(ctx, _param, incomplete: str):
    st = _get_storage_from_ctx(ctx)
    try:
        companies = st.read("companies")
    except click.ClickException:
        companies = []
    out = []
    for c in companies:
        cid = str(c.get("company_id", ""))
        name = str(c.get("name", ""))
        if cid.startswith(incomplete):
            out.append((cid, name))
    return _completion_items(out)

def complete_company_names(ctx, _param, incomplete: str):
    st = _get_storage_from_ctx(ctx)
    try:
        companies = st.read("companies")
    except click.ClickException:
        companies = []
    out = []
    for c in companies:
        name = str(c.get("name", ""))
        if name.lower().startswith(incomplete.lower()):
            out.append((name, c.get("company_id")))
    return _completion_items(out)

def complete_application_ids(ctx, _param, incomplete: str):
    st = _get_storage_from_ctx(ctx)
    try:
        apps = st.read("applications")
    except click.ClickException:
        apps = []
    out = []
    for a in apps:
        aid = str(a.get("application_id", ""))
        pos = str(a.get("position", ""))
        if aid.startswith(incomplete):
            out.append((aid, pos))
    return _completion_items(out)

def complete_contact_ids(ctx, _param, incomplete: str):
    st = _get_storage_from_ctx(ctx)
    try:
        contacts = st.read("contacts")
    except click.ClickException:
        contacts = []
    out = []
    for c in contacts:
        cid = str(c.get("contact_id", ""))
        nm = str(c.get("name", ""))
        if cid.startswith(incomplete):
            out.append((cid, nm))
    return _completion_items(out)

def complete_stage_ids(ctx, _param, incomplete: str):
    st = _get_storage_from_ctx(ctx)
    try:
        stages = st.read("stages")
    except click.ClickException:
        stages = []
    out = []
    for s in stages:
        sid = str(s.get("stage_id", ""))
        stg = str(s.get("stage", ""))
        if sid.startswith(incomplete):
            out.append((sid, stg))
    return _completion_items(out)

def complete_status(_ctx, _param, incomplete: str):
    vals = [s for s in COMMON_STATUSES if s.startswith(incomplete.lower())]
    return _completion_items([(v, "status") for v in vals])

def complete_job_urls(ctx, _param, incomplete: str):
    st = _get_storage_from_ctx(ctx)
    try:
        apps = st.read("applications")
    except click.ClickException:
        apps = []
    out = []
    for a in apps:
        url = str(a.get("job_url", ""))
        if url and url.startswith(incomplete):
            out.append((url, a.get("application_id")))
    return _completion_items(out)

# =============================================================================
# CLI root
# =============================================================================
@click.group()
@click.option(
    "--backend",
    type=click.Choice(["json", "db"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Storage backend to use.",
)
@click.option(
    "--data-dir",
    default=os.path.join(CWD, "data"),
    show_default=True,
    help="Directory for JSON storage (when --backend=json).",
)
@click.option(
    "--dsn",
    default="",
    help="Database DSN/URL (when --backend=db).",
)
@click.pass_context
def cli(ctx: click.Context, backend: str, data_dir: str, dsn: str) -> None:
    """
    @brief Root command group. Initializes and stores the chosen Storage backend in context.
    """
    if backend.lower() == "json":
        storage: Storage = JSONStorage(data_dir=data_dir)
    else:
        storage = DBStorage(dsn=dsn)  # currently NotImplemented
    ctx.obj = {"storage": storage}

# --------------------------- completion (script) -----------------------------
@cli.command("completion")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish", "powershell"], case_sensitive=False),
    required=True,
    help="Shell to generate completion script for.",
)
def completion_cmd(shell: str) -> None:
    """
    @brief Print a shell completion script. See Click env-var notes if unavailable in your version.
    """
    try:
        from click.shell_completion import get_completion_script  # type: ignore
    except Exception:
        raise click.ClickException(
            "Completion script generator not available in this Click version.\n"
            "Use env-var approach instead (replace 'cli' with your alias/command):\n"
            "  bash:        _CLI_COMPLETE=bash_source cli > ~/.config/bash_completion.d/cli.sh\n"
            "  zsh:         _CLI_COMPLETE=zsh_source  cli > ~/.zfunc/_cli && compinit\n"
            "  fish:        _CLI_COMPLETE=fish_source cli > ~/.config/fish/completions/cli.fish\n"
            "  powershell:  $env:_CLI_COMPLETE='powershell_source'; cli"
        )

    ctx = click.get_current_context()
    root = ctx.find_root()
    prog_name = root.info_name or os.path.basename(__file__) or "cli"
    script = get_completion_script(prog_name=prog_name, shell=shell)  # type: ignore[call-arg]
    click.echo(script)

# --------------------------- init -------------------------------------------
@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """
    @brief Initialize storage and log startup.
    """
    st = _get_storage_from_ctx(ctx)
    st.ensure_all()
    logging.info("CLI initialized (backend ready).")
    click.echo("Initialized tables: companies, applications, contacts, stages.")

# --------------------------- list -------------------------------------------
@cli.command("list")
@click.option(
    "--table",
    type=click.Choice(list(TABLES.keys()), case_sensitive=False),
    shell_complete=complete_tables,
    help="Which table to display.",
)
@click.pass_context
def list_table(ctx: click.Context, table: Optional[str]) -> None:
    """
    @brief List rows from a specified table.
    @param table Table name; prompts if omitted.
    """
    if not table:
        table = click.prompt("Select table", type=click.Choice(list(TABLES.keys()), case_sensitive=False)).lower()

    st = _get_storage_from_ctx(ctx)
    # Ensure table is not None before calling st.read()
    assert table is not None
    rows = st.read(table)
    if not rows:
        click.echo(f"No rows in table '{table}'.")
        return
    _print_table(TABLES[table]["columns"], rows)

# --------------------------- add-company ------------------------------------
@cli.command("add-company")
@click.option("--name", prompt="Company Name", shell_complete=complete_company_names, help="Company name to add.")
@click.option("--location", prompt="Company Location", default="", show_default=True)
@click.option("--industry", prompt="Industry", default="", show_default=True)
@click.option("--website", prompt="Website URL", default="", show_default=True)
@click.option("--source", prompt="Source (LinkedIn, etc.)", default="", show_default=True)
@click.option("--rating", prompt="Rating (1-5 or text)", default="", show_default=True)
@click.pass_context
def add_company(
    ctx: click.Context,
    name: str,
    location: str,
    industry: str,
    website: str,
    source: str,
    rating: str,
) -> None:
    """
    @brief Insert a new company row (unique by name).
    """
    st = _get_storage_from_ctx(ctx)
    companies = st.read("companies")

    if _lookup_company_id_by_name(name, companies) is not None:
        raise click.ClickException(f'Company "{name}" already exists.')

    company_id = _new_id(TABLES["companies"]["id_prefix"])
    row = {
        "company_id": company_id,
        "name": name,
        "location": location,
        "industry": industry,
        "website": website,
        "source": source,
        "rating": rating,
        "created_at": _now_s(),
    }
    companies.append(row)
    st.write("companies", companies)
    logging.info("Added company: %s (%s)", name, company_id)
    click.echo(f'Added company: "{name}" (id={company_id})')

# --------------------------- add-application --------------------------------
@cli.command("add-application")
@click.option("--company-name", shell_complete=complete_company_names, help="Company name (resolves to company_id).")
@click.option("--company-id", shell_complete=complete_company_ids, help="Company ID (overrides company-name).")
@click.option("--position", prompt="Position", help="Job title / position.")
@click.option("--status", prompt="Status", default="new", show_default=True, shell_complete=complete_status)
@click.option("--employment-type", prompt="Employment Type", default="", show_default=True)
@click.option("--salary-min", type=int, prompt="Salary Min (int, blank for none)", default=None, show_default=False)
@click.option("--salary-max", type=int, prompt="Salary Max (int, blank for none)", default=None, show_default=False)
@click.option("--currency", prompt="Currency", default="USD", show_default=True)
@click.option("--job-url", prompt="Job URL", default="", show_default=True, shell_complete=complete_job_urls)
@click.option("--notes", prompt="Notes", default="", show_default=True)
@click.pass_context
def add_application(
    ctx: click.Context,
    company_name: Optional[str],
    company_id: Optional[str],
    position: str,
    status: str,
    employment_type: str,
    salary_min: Optional[int],
    salary_max: Optional[int],
    currency: str,
    job_url: str,
    notes: str,
) -> None:
    """
    @brief Insert a new application row.
    @details Provide --company-id or --company-name, or you will be prompted.
    """
    st = _get_storage_from_ctx(ctx)
    companies = st.read("companies")
    applications = st.read("applications")

    resolved_company_id = company_id
    if not resolved_company_id:
        if company_name:
            resolved_company_id = _lookup_company_id_by_name(company_name, companies)
            if not resolved_company_id:
                raise click.ClickException(f'Company "{company_name}" not found. Add it first via add-company.')
        else:
            if not companies:
                raise click.ClickException("No companies found. Add a company first (add-company).")
            chosen = _select_company_interactive(companies)
            resolved_company_id = str(chosen.get("company_id"))

    app_id = _new_id(TABLES["applications"]["id_prefix"])
    now = _now_s()
    row = {
        "application_id": app_id,
        "company_id": resolved_company_id,
        "position": position,
        "status": status,
        "employment_type": employment_type,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "job_url": job_url,
        "applied_at": now,
        "last_update": now,
        "notes": notes,
    }

    applications.append(row)
    st.write("applications", applications)
    logging.info("Added application: %s (company_id=%s)", app_id, resolved_company_id)
    click.echo(f"Added application: id={app_id}")

# --------------------------- add-contact ------------------------------------
@cli.command("add-contact")
@click.option("--company-name", shell_complete=complete_company_names, help="Company name (resolves to company_id).")
@click.option("--company-id", shell_complete=complete_company_ids, help="Company ID (overrides company-name).")
@click.option("--name", "person_name", prompt="Contact Name", help="Contact full name.")
@click.option("--title", prompt="Contact Title", default="", show_default=True)
@click.option("--email", prompt="Contact Email", default="", show_default=True)
@click.option("--phone", prompt="Contact Phone", default="", show_default=True)
@click.option("--notes", prompt="Notes", default="", show_default=True)
@click.pass_context
def add_contact(
    ctx: click.Context,
    company_name: Optional[str],
    company_id: Optional[str],
    person_name: str,
    title: str,
    email: str,
    phone: str,
    notes: str,
) -> None:
    """
    @brief Insert a new contact row linked to a company.
    """
    st = _get_storage_from_ctx(ctx)
    companies = st.read("companies")
    contacts = st.read("contacts")

    resolved_company_id = company_id
    if not resolved_company_id:
        if company_name:
            resolved_company_id = _lookup_company_id_by_name(company_name, companies)
            if not resolved_company_id:
                raise click.ClickException(f'Company "{company_name}" not found. Add it first via add-company.')
        else:
            if not companies:
                raise click.ClickException("No companies found. Add a company first (add-company).")
            chosen = _select_company_interactive(companies)
            resolved_company_id = str(chosen.get("company_id"))

    contact_id = _new_id(TABLES["contacts"]["id_prefix"])
    row = {
        "contact_id": contact_id,
        "company_id": resolved_company_id,
        "name": person_name,
        "title": title,
        "email": email,
        "phone": phone,
        "notes": notes,
        "last_contacted": "",
    }
    contacts.append(row)
    st.write("contacts", contacts)
    logging.info("Added contact: %s (company_id=%s)", contact_id, resolved_company_id)
    click.echo(f"Added contact: id={contact_id}")

# --------------------------- add-stage --------------------------------------
@cli.command("add-stage")
@click.option("--application-id", shell_complete=complete_application_ids, help="Application ID to append a stage.")
@click.option("--stage", prompt="Stage", help="E.g., Applied, Recruiter Screen, Phone, Onsite, Offer.")
@click.option("--date", prompt="Date (YYYY-MM-DD or epoch, blank OK)", default="", show_default=False)
@click.option("--outcome", prompt="Outcome", default="", show_default=True)
@click.option("--notes", prompt="Notes", default="", show_default=True)
@click.pass_context
def add_stage(ctx: click.Context, application_id: Optional[str], stage: str, date: str, outcome: str, notes: str) -> None:
    """
    @brief Append a stage (pipeline event) to an application.
    """
    st = _get_storage_from_ctx(ctx)
    applications = st.read("applications")
    stages = st.read("stages")

    resolved_app_id = application_id
    if not resolved_app_id:
        if not applications:
            raise click.ClickException("No applications found. Add an application first.")
        chosen = _select_application_interactive(applications)
        resolved_app_id = str(chosen.get("application_id"))

    if not any(a.get("application_id") == resolved_app_id for a in applications):
        raise click.ClickException(f"Application not found: {resolved_app_id}")

    stage_id = _new_id(TABLES["stages"]["id_prefix"])
    row = {
        "stage_id": stage_id,
        "application_id": resolved_app_id,
        "stage": stage,
        "date": date,
        "outcome": outcome,
        "notes": notes,
    }
    stages.append(row)
    st.write("stages", stages)

    for a in applications:
        if a.get("application_id") == resolved_app_id:
            a["last_update"] = _now_s()
            break
    st.write("applications", applications)

    logging.info("Added stage: %s (application_id=%s)", stage_id, resolved_app_id)
    click.echo(f"Added stage: id={stage_id}")

# ============================ REMOVE COMMANDS ================================
@cli.group("remove")
def remove_group() -> None:
    """@brief Group of remove (delete) commands."""
    pass

@remove_group.command("company")
@click.option("--company-id", shell_complete=complete_company_ids, help="Company ID to remove.")
@click.option("--name", "company_name", shell_complete=complete_company_names, help="Company name to remove.")
@click.option("--cascade", is_flag=True, help="Also remove related applications, stages, and contacts.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
@click.pass_context
def remove_company(ctx: click.Context, company_id: Optional[str], company_name: Optional[str], cascade: bool, yes: bool) -> None:
    """
    @brief Remove a company. Optionally cascade delete related rows.
    """
    st = _get_storage_from_ctx(ctx)
    companies = st.read("companies")
    applications = st.read("applications")
    contacts = st.read("contacts")
    stages = st.read("stages")

    resolved_company_id = company_id
    if not resolved_company_id:
        if company_name:
            resolved_company_id = _lookup_company_id_by_name(company_name, companies)
            if not resolved_company_id:
                raise click.ClickException("Company not found.")
        else:
            if not companies:
                raise click.ClickException("No companies to remove.")
            chosen = _select_company_interactive(companies)
            resolved_company_id = str(chosen.get("company_id"))

    related_apps = [a for a in applications if a.get("company_id") == resolved_company_id]
    related_contacts = [c for c in contacts if c.get("company_id") == resolved_company_id]
    related_app_ids = {a.get("application_id") for a in related_apps}
    related_stages = [s for s in stages if s.get("application_id") in related_app_ids]

    if (related_apps or related_contacts or related_stages) and not cascade:
        raise click.ClickException(
            "Company has related rows (applications/contacts/stages). "
            "Re-run with --cascade to delete them as well."
        )

    if not yes:
        click.echo(
            f"About to delete company {resolved_company_id} "
            f"(apps={len(related_apps)}, contacts={len(related_contacts)}, stages={len(related_stages)})"
            + (" with cascade." if cascade else ".")
        )
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    companies_filtered, n_companies = _filter_delete(companies, lambda r: r.get("company_id") == resolved_company_id)

    n_apps = n_contacts = n_stages = 0
    if cascade:
        applications_filtered, n_apps = _filter_delete(applications, lambda r: r.get("company_id") == resolved_company_id)
        app_ids_to_remove = {a.get("application_id") for a in related_apps}
        stages_filtered, n_stages = _filter_delete(stages, lambda r: r.get("application_id") in app_ids_to_remove)
        contacts_filtered, n_contacts = _filter_delete(contacts, lambda r: r.get("company_id") == resolved_company_id)
        st.write("applications", applications_filtered)
        st.write("stages", stages_filtered)
        st.write("contacts", contacts_filtered)

    st.write("companies", companies_filtered)

    logging.info(
        "Removed company %s (cascade=%s): companies=%d, apps=%d, stages=%d, contacts=%d",
        resolved_company_id, cascade, n_companies, n_apps, n_stages, n_contacts
    )
    click.echo(f"Removed: companies={n_companies}, applications={n_apps}, stages={n_stages}, contacts={n_contacts}")

@remove_group.command("application")
@click.option("--application-id", shell_complete=complete_application_ids, help="Application ID to remove.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
@click.pass_context
def remove_application(ctx: click.Context, application_id: Optional[str], yes: bool) -> None:
    """
    @brief Remove an application and its stages.
    """
    st = _get_storage_from_ctx(ctx)
    applications = st.read("applications")
    stages = st.read("stages")

    resolved_app_id = application_id
    if not resolved_app_id:
        if not applications:
            raise click.ClickException("No applications to remove.")
        chosen = _select_application_interactive(applications)
        resolved_app_id = str(chosen.get("application_id"))

    if not any(a.get("application_id") == resolved_app_id for a in applications):
        raise click.ClickException(f"Application not found: {resolved_app_id}")

    if not yes:
        click.echo(f"About to delete application {resolved_app_id} and its stages.")
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    applications_filtered, n_apps = _filter_delete(applications, lambda r: r.get("application_id") == resolved_app_id)
    stages_filtered, n_stages = _filter_delete(stages, lambda r: r.get("application_id") == resolved_app_id)

    st.write("applications", applications_filtered)
    st.write("stages", stages_filtered)

    logging.info("Removed application %s: applications=%d, stages=%d", resolved_app_id, n_apps, n_stages)
    click.echo(f"Removed: applications={n_apps}, stages={n_stages}")

@remove_group.command("contact")
@click.option("--contact-id", shell_complete=complete_contact_ids, help="Contact ID to remove.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
@click.pass_context
def remove_contact(ctx: click.Context, contact_id: Optional[str], yes: bool) -> None:
    """
    @brief Remove a contact.
    """
    st = _get_storage_from_ctx(ctx)
    contacts = st.read("contacts")

    resolved_id = contact_id
    if not resolved_id:
        if not contacts:
            raise click.ClickException("No contacts to remove.")
        chosen = _select_contact_interactive(contacts)
        resolved_id = str(chosen.get("contact_id"))

    if not any(c.get("contact_id") == resolved_id for c in contacts):
        raise click.ClickException(f"Contact not found: {resolved_id}")

    if not yes:
        click.echo(f"About to delete contact {resolved_id}.")
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    contacts_filtered, n_contacts = _filter_delete(contacts, lambda r: r.get("contact_id") == resolved_id)
    st.write("contacts", contacts_filtered)

    logging.info("Removed contact %s: contacts=%d", resolved_id, n_contacts)
    click.echo(f"Removed: contacts={n_contacts}")

@remove_group.command("stage")
@click.option("--stage-id", shell_complete=complete_stage_ids, help="Stage ID to remove.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
@click.pass_context
def remove_stage(ctx: click.Context, stage_id: Optional[str], yes: bool) -> None:
    """
    @brief Remove a single stage (pipeline event).
    """
    st = _get_storage_from_ctx(ctx)
    stages = st.read("stages")

    resolved_id = stage_id
    if not resolved_id:
        if not stages:
            raise click.ClickException("No stages to remove.")
        chosen = _select_stage_interactive(stages)
        resolved_id = str(chosen.get("stage_id"))

    if not any(s.get("stage_id") == resolved_id for s in stages):
        raise click.ClickException(f"Stage not found: {resolved_id}")

    if not yes:
        click.echo(f"About to delete stage {resolved_id}.")
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    stages_filtered, n_stages = _filter_delete(stages, lambda r: r.get("stage_id") == resolved_id)
    st.write("stages", stages_filtered)

    logging.info("Removed stage %s: stages=%d", resolved_id, n_stages)
    click.echo(f"Removed: stages={n_stages}")

# --------------------------- update-application -----------------------------
@cli.command("update-application")
@click.option("--application-id", shell_complete=complete_application_ids, help="Application ID to update.")
@click.option("--job-url", shell_complete=complete_job_urls, help="Alternatively, select the application by its job URL.")
@click.option("--position", default=None, help="New position/title.")
@click.option("--status", default=None, shell_complete=complete_status, help="New status.")
@click.option("--employment-type", default=None, help="New employment type.")
@click.option("--salary-min", type=int, default=None, help="New minimum salary (int).")
@click.option("--salary-max", type=int, default=None, help="New maximum salary (int).")
@click.option("--currency", default=None, help="New currency code (e.g., USD).")
@click.option("--notes", default=None, help="Replace notes text.")
@click.pass_context
def update_application(
    ctx: click.Context,
    application_id: str | None,
    job_url: str | None,
    position: str | None,
    status: str | None,
    employment_type: str | None,
    salary_min: int | None,
    salary_max: int | None,
    currency: str | None,
    notes: str | None,
) -> None:
    """
    @brief Update one application row.
    @details If no selector provided, prompts to choose an application, then interactively asks which fields to change.
    """
    st = _get_storage_from_ctx(ctx)
    applications = st.read("applications")

    # Resolve selection
    target: Optional[Dict[str, Any]] = None
    if application_id:
        target = next((a for a in applications if a.get("application_id") == application_id), None)
    elif job_url:
        target = next((a for a in applications if a.get("job_url") == job_url), None)
    else:
        if not applications:
            raise click.ClickException("No applications to update.")
        target = _select_application_interactive(applications)

    if target is None:
        sel = application_id or job_url or "<unknown>"
        raise click.ClickException(f"Application not found for selector: {sel}")

    # Interactive update mode if nothing passed
    if all(v is None for v in (position, status, employment_type, salary_min, salary_max, currency, notes)):
        click.echo("No update flags provided; entering interactive update mode.")
        if click.confirm("Update position?", default=False):
            position = click.prompt("New position", default=target.get("position", ""))
        if click.confirm("Update status?", default=False):
            status = click.prompt("New status", default=target.get("status", "new"))
        if click.confirm("Update employment type?", default=False):
            employment_type = click.prompt("New employment type", default=target.get("employment_type", ""))
        if click.confirm("Update salary min?", default=False):
            salary_min = click.prompt("New salary min (int or blank)", default=target.get("salary_min"), type=int)
        if click.confirm("Update salary max?", default=False):
            salary_max = click.prompt("New salary max (int or blank)", default=target.get("salary_max"), type=int)
        if click.confirm("Update currency?", default=False):
            currency = click.prompt("New currency", default=target.get("currency", "USD"))
        if click.confirm("Update notes?", default=False):
            notes = click.prompt("New notes", default=target.get("notes", ""))

    # Apply updates
    if position is not None:
        target["position"] = position
    if status is not None:
        target["status"] = status
    if employment_type is not None:
        target["employment_type"] = employment_type
    if salary_min is not None:
        target["salary_min"] = salary_min
    if salary_max is not None:
        target["salary_max"] = salary_max
    if currency is not None:
        target["currency"] = currency
    if notes is not None:
        target["notes"] = notes

    target["last_update"] = _now_s()
    st.write("applications", applications)

    logging.info(
        "Updated application %s (via %s)",
        target.get("application_id"),
        "application-id" if application_id else ("job-url" if job_url else "interactive"),
    )
    click.echo(f'Updated application id={target.get("application_id")}')

# =============================================================================
# Entrypoint
# =============================================================================
if __name__ == "__main__":
    cli()
