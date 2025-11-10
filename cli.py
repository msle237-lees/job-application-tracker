#!/usr/bin/env python3
"""
@file cli.py
@brief Job Application Tracker CLI using Click with multi-table JSON storage + shell completion.

@details
  Splits data into multiple logical "tables" stored as JSON lists:
    - companies.json
    - applications.json
    - contacts.json
    - stages.json

  New in this version:
    - Remove commands:
        * remove-company (--company-id or --name) with optional --cascade
        * remove-application (--application-id) removes related stages
        * remove-contact (--contact-id)
        * remove-stage (--stage-id)
      Each supports --yes / -y to skip confirmation.
    - Shell completion:
        * `completion --shell [bash|zsh|fish|powershell]` prints a completion script.
        * Dynamic value completion for --table, --company-id/--company-name, --application-id,
          --contact-id, --stage-id, and common --status values.

  Each command uses ClickException for friendly errors + non-zero exit codes.
  Includes generic helpers to read/write tables, ensure files, print tables,
  and generate simple IDs.

  Exit behavior:
    - Success => exit code 0
    - Validation/I/O error => ClickException => exit code 1
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import click

# Best-effort import for printing completion scripts programmatically (Click 8+)
try:
    from click.shell_completion import get_completion_script  # type: ignore
except Exception:  # pragma: no cover - compatibility
    get_completion_script = None  # Fallback path used if unavailable

# =============================================================================
# Paths / Globals
# =============================================================================
CWD = os.getcwd()
LOG_DIR = os.path.join(CWD, "logs")
DATA_DIR = os.path.join(CWD, "data")
LOG_FILE = os.path.join(LOG_DIR, "cli.log")

# Ensure directories exist before configuring logging
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

# Table metadata (filename + preferred column order for display)
TABLES: Dict[str, Dict[str, Any]] = {
    "companies": {
        "file": os.path.join(DATA_DIR, "companies.json"),
        "columns": [
            "company_id",
            "name",
            "location",
            "industry",
            "website",
            "source",
            "rating",
            "created_at",
        ],
        "id_field": "company_id",
        "id_prefix": "cmp_",
    },
    "applications": {
        "file": os.path.join(DATA_DIR, "applications.json"),
        "columns": [
            "application_id",
            "company_id",
            "position",
            "status",
            "employment_type",
            "salary_min",
            "salary_max",
            "currency",
            "job_url",
            "applied_at",
            "last_update",
            "notes",
        ],
        "id_field": "application_id",
        "id_prefix": "app_",
    },
    "contacts": {
        "file": os.path.join(DATA_DIR, "contacts.json"),
        "columns": [
            "contact_id",
            "company_id",
            "name",
            "title",
            "email",
            "phone",
            "notes",
            "last_contacted",
        ],
        "id_field": "contact_id",
        "id_prefix": "ctc_",
    },
    "stages": {
        "file": os.path.join(DATA_DIR, "stages.json"),
        "columns": [
            "stage_id",
            "application_id",
            "stage",
            "date",
            "outcome",
            "notes",
        ],
        "id_field": "stage_id",
        "id_prefix": "stg_",
    },
}

# Common statuses to suggest for completion (free-form still allowed)
COMMON_STATUSES: List[str] = [
    "new",
    "applied",
    "recruiter",
    "phone",
    "technical",
    "onsite",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
]

# =============================================================================
# Helpers
# =============================================================================
def _ensure_table_file(table: str) -> None:
    """
    @brief Ensure the JSON file for a given table exists (as an empty list).

    @param table The logical table name (e.g., "companies").
    @throws click.ClickException If the file cannot be created.
    """
    meta = TABLES.get(table)
    if not meta:
        raise click.ClickException(f"Unknown table: {table}")
    path = meta["file"]
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)
        except OSError as e:
            logging.exception("Failed to create table file: %s", path)
            raise click.ClickException(f"Failed to create {path}: {e}")


def _read_table(table: str) -> List[Dict[str, Any]]:
    """
    @brief Read a table (JSON list) from disk.

    @param table Table name.
    @return List of records (dict).
    @throws click.ClickException On file/JSON errors or unknown table.
    """
    meta = TABLES.get(table)
    if not meta:
        raise click.ClickException(f"Unknown table: {table}")
    _ensure_table_file(table)
    path = meta["file"]
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            return json.loads(text) if text else []
    except json.JSONDecodeError as e:
        logging.exception("Corrupted JSON in %s", path)
        raise click.ClickException(f"Corrupted data file: {path} ({e})")
    except OSError as e:
        logging.exception("Failed to read %s", path)
        raise click.ClickException(f"Failed to read {path}: {e}")


def _write_table(table: str, rows: List[Dict[str, Any]]) -> None:
    """
    @brief Write a table (JSON list) to disk.

    @param table Table name.
    @param rows Records to persist.
    @throws click.ClickException On file errors or unknown table.
    """
    meta = TABLES.get(table)
    if not meta:
        raise click.ClickException(f"Unknown table: {table}")
    path = meta["file"]
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except OSError as e:
        logging.exception("Failed to write %s", path)
        raise click.ClickException(f"Failed to write {path}: {e}")


def _new_id(prefix: str) -> str:
    """
    @brief Generate a simple unique-ish ID using time_ns.

    @param prefix String prefix (e.g., "cmp_").
    @return New ID string.
    """
    return f"{prefix}{time.time_ns()}"


def _lookup_company_id_by_name(name: str, companies: List[Dict[str, Any]]) -> Optional[str]:
    """
    @brief Find a company_id by case-insensitive name.

    @param name Company name to search.
    @param companies Pre-loaded companies table.
    @return company_id or None if not found.
    """
    target = name.strip().lower()
    for c in companies:
        if c.get("name", "").strip().lower() == target:
            return c.get("company_id")
    return None


def _print_table(headers: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    """
    @brief Print tabular data with dynamic column widths.

    @param headers Column names in desired order.
    @param rows Iterable of dict-like rows.
    """
    str_rows: List[List[str]] = []
    widths = [len(h) for h in headers]
    for r in rows:
        row_vals: List[str] = []
        for i, h in enumerate(headers):
            val = r.get(h, "")
            sval = "" if val is None else str(val)
            row_vals.append(sval)
            widths[i] = max(widths[i], len(sval))
        str_rows.append(row_vals)

    header_row = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep = "-+-".join("-" * widths[i] for i in range(len(headers)))
    click.echo(header_row)
    click.echo(sep)
    for r in str_rows:
        click.echo(" | ".join(r[i].ljust(widths[i]) for i in range(len(headers))))


def _ensure_all_tables() -> None:
    """
    @brief Ensure all known tables exist.
    """
    for t in TABLES.keys():
        _ensure_table_file(t)


def _filter_delete(rows: List[Dict[str, Any]], predicate) -> Tuple[List[Dict[str, Any]], int]:
    """
    @brief Return a new list excluding rows where predicate(row) is True.

    @param rows Input list.
    @param predicate Function returning True to delete.
    @return (filtered_rows, removed_count)
    """
    kept: List[Dict[str, Any]] = []
    removed = 0
    for r in rows:
        if predicate(r):
            removed += 1
        else:
            kept.append(r)
    return kept, removed


# =============================================================================
# Shell completion helpers (dynamic value providers)
# =============================================================================
def _completion_items(strings: List[Tuple[str, Optional[str]]]) -> List[Any]:
    """
    @brief Build Click CompletionItem list with optional help text.

    @param strings List of (value, help_text) tuples.
    @return List of CompletionItem objects.
    """
    items: List[Any] = []
    try:
        # Available on Click 8+
        CompletionItem = click.shell_completion.CompletionItem  # type: ignore[attr-defined]
        for value, help_text in strings:
            if help_text:
                items.append(CompletionItem(value=value, help=help_text))
            else:
                items.append(CompletionItem(value=value))
    except Exception:
        # Fallback to plain strings if older Click
        items = [s[0] for s in strings]  # type: ignore[assignment]
    return items


def complete_tables(_ctx, _param, incomplete: str):
    """
    @brief Complete table names from TABLES.

    @param _ctx Click context (unused).
    @param _param Param (unused).
    @param incomplete Current partial token.
    @return List of CompletionItem.
    """
    vals = [k for k in TABLES.keys() if k.startswith(incomplete.lower())]
    return _completion_items([(v, "table") for v in sorted(vals)])


def complete_company_ids(_ctx, _param, incomplete: str):
    """
    @brief Complete company IDs, with company name as help.

    @param _ctx Click context.
    @param _param Param.
    @param incomplete Current partial token.
    @return Completion items with help text.
    """
    try:
        companies = _read_table("companies")
    except click.ClickException:
        companies = []
    out: List[Tuple[str, Optional[str]]] = []
    for c in companies:
        cid = str(c.get("company_id", ""))
        name = str(c.get("name", ""))
        if cid.startswith(incomplete):
            out.append((cid, name))
    return _completion_items(out)


def complete_company_names(_ctx, _param, incomplete: str):
    """
    @brief Complete company names.

    @param incomplete Current partial company name.
    @return Completion items.
    """
    try:
        companies = _read_table("companies")
    except click.ClickException:
        companies = []
    out: List[Tuple[str, Optional[str]]] = []
    for c in companies:
        name = str(c.get("name", ""))
        if name.lower().startswith(incomplete.lower()):
            out.append((name, c.get("company_id")))
    return _completion_items(out)


def complete_application_ids(_ctx, _param, incomplete: str):
    """
    @brief Complete application IDs, with position as help text.

    @param incomplete Current partial ID.
    @return Completion items.
    """
    try:
        apps = _read_table("applications")
    except click.ClickException:
        apps = []
    out: List[Tuple[str, Optional[str]]] = []
    for a in apps:
        aid = str(a.get("application_id", ""))
        pos = str(a.get("position", ""))
        if aid.startswith(incomplete):
            out.append((aid, pos))
    return _completion_items(out)


def complete_contact_ids(_ctx, _param, incomplete: str):
    """
    @brief Complete contact IDs, with contact name as help.

    @param incomplete Current partial ID.
    @return Completion items.
    """
    try:
        contacts = _read_table("contacts")
    except click.ClickException:
        contacts = []
    out: List[Tuple[str, Optional[str]]] = []
    for c in contacts:
        cid = str(c.get("contact_id", ""))
        nm = str(c.get("name", ""))
        if cid.startswith(incomplete):
            out.append((cid, nm))
    return _completion_items(out)


def complete_stage_ids(_ctx, _param, incomplete: str):
    """
    @brief Complete stage IDs, with stage text as help.

    @param incomplete Current partial ID.
    @return Completion items.
    """
    try:
        stages = _read_table("stages")
    except click.ClickException:
        stages = []
    out: List[Tuple[str, Optional[str]]] = []
    for s in stages:
        sid = str(s.get("stage_id", ""))
        stg = str(s.get("stage", ""))
        if sid.startswith(incomplete):
            out.append((sid, stg))
    return _completion_items(out)


def complete_status(_ctx, _param, incomplete: str):
    """
    @brief Complete common statuses (free-form still accepted).

    @param incomplete Current partial.
    @return Completion items.
    """
    vals = [s for s in COMMON_STATUSES if s.startswith(incomplete.lower())]
    return _completion_items([(v, "status") for v in vals])


def complete_job_urls(_ctx, _param, incomplete: str):
    """
    @brief Complete application job URLs.

    @param incomplete Partial URL.
    @return Completion items.
    """
    try:
        apps = _read_table("applications")
    except click.ClickException:
        apps = []
    out: List[Tuple[str, Optional[str]]] = []
    for a in apps:
        url = str(a.get("job_url", ""))
        if url and url.startswith(incomplete):
            out.append((url, a.get("application_id")))
    return _completion_items(out)


# =============================================================================
# CLI
# =============================================================================
@click.group()
def cli() -> None:
    """
    @brief Root command group for the Job Application Tracker CLI.
    @return None
    """
    pass


# --------------------------- completion (script printer) ---------------------
@cli.command("completion")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish", "powershell"], case_sensitive=False),
    required=True,
    help="Shell to generate completion script for.",
)
def completion_cmd(shell: str) -> None:
    """
    @brief Print a shell completion script for this CLI.

    @details
      Redirect the output to the appropriate file and source it in your shell init.
      Example for bash:
        python cli.py completion --shell bash > ~/.config/bash_completion.d/cli.sh
        echo 'source ~/.config/bash_completion.d/cli.sh' >> ~/.bashrc
        source ~/.bashrc

    @param shell Target shell (bash|zsh|fish|powershell).
    @throws click.ClickException If Click's completion script generator is unavailable.
    """
    # Determine the program name users will type. Prefer the root command's info_name.
    ctx = click.get_current_context()
    root = ctx.find_root()
    prog_name = root.info_name or os.path.basename(__file__) or "cli"

    if get_completion_script is None:
        # Fallback instructions (older Click)
        raise click.ClickException(
            "Completion script generator not available in this Click version.\n"
            "Use the env-var approach instead (replace 'cli' with your alias/command):\n"
            "  bash:        _CLI_COMPLETE=bash_source cli > ~/.config/bash_completion.d/cli.sh\n"
            "  zsh:         _CLI_COMPLETE=zsh_source  cli > ~/.zfunc/_cli && compinit\n"
            "  fish:        _CLI_COMPLETE=fish_source cli > ~/.config/fish/completions/cli.fish\n"
            "  powershell:  $env:_CLI_COMPLETE='powershell_source'; cli"
        )

    # Print the script to stdout
    script = get_completion_script(prog_name=prog_name, shell=shell)  # type: ignore[call-arg]
    click.echo(script)


# --------------------------- init -------------------------------------------
@cli.command()
def init() -> None:
    """
    @brief Initialize directories and JSON tables.

    @details
      Ensures logs/, data/, and all table files exist. Writes a startup log entry.
    @return None
    @throws click.ClickException On file creation errors.
    """
    _ensure_all_tables()
    logging.info("CLI initialized (multi-table).")
    click.echo("Initialized Job Application Tracker tables: companies, applications, contacts, stages.")


# --------------------------- list -------------------------------------------
@cli.command("list")
@click.option(
    "--table",
    "table",
    type=click.Choice(list(TABLES.keys()), case_sensitive=False),
    required=True,
    shell_complete=complete_tables,
    help="Which table to display.",
)
def list_table(table: str) -> None:
    """
    @brief List rows from a specified table.

    @param table One of: companies, applications, contacts, stages.
    @return None
    @throws click.ClickException On read/JSON errors.
    """
    table = table.lower()
    meta = TABLES[table]
    rows = _read_table(table)
    if not rows:
        click.echo(f"No rows in table '{table}'.")
        return
    _print_table(meta["columns"], rows)


# --------------------------- add-company ------------------------------------
@cli.command("add-company")
@click.option("--name", prompt="Company Name", shell_complete=complete_company_names, help="Company name to add.")
@click.option("--location", prompt="Company Location", default="", show_default=True, help="Company location.")
@click.option("--industry", prompt=False, default="", show_default=True, help="Industry (e.g., Software).")
@click.option("--website", prompt=False, default="", show_default=True, help="Website URL.")
@click.option("--source", prompt=False, default="", show_default=True, help="How you found it (e.g., LinkedIn).")
@click.option("--rating", prompt=False, default="", show_default=True, help="Your personal rating (1-5 or text).")
def add_company(
    name: str,
    location: str,
    industry: str,
    website: str,
    source: str,
    rating: str,
) -> None:
    """
    @brief Insert a new company row.

    @param name Company name (unique by name).
    @param location Company location.
    @param industry Company industry label.
    @param website Company website.
    @param source Where you found the company.
    @param rating Personal rating.

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    companies = _read_table("companies")

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
        "created_at": int(time.time()),
    }
    companies.append(row)
    _write_table("companies", companies)
    logging.info("Added company: %s (%s)", name, company_id)
    click.echo(f'Added company: "{name}" (id={company_id})')


# --------------------------- add-application --------------------------------
@cli.command("add-application")
@click.option("--company-name", shell_complete=complete_company_names, help="Company name (will be resolved to company_id).")
@click.option("--company-id", shell_complete=complete_company_ids, help="Company ID (overrides company-name if provided).")
@click.option("--position", prompt="Position", help="Job title / position.")
@click.option("--status", default="new", show_default=True, shell_complete=complete_status, help="Application status.")
@click.option("--employment-type", default="", show_default=True, help="Full-time/Contract/Intern, etc.")
@click.option("--salary-min", type=int, default=None, help="Minimum salary (int).")
@click.option("--salary-max", type=int, default=None, help="Maximum salary (int).")
@click.option("--currency", default="USD", show_default=True, help="Currency code.")
@click.option("--job-url", default="", show_default=True, shell_complete=complete_job_urls, help="URL of the job posting.")
@click.option("--notes", default="", show_default=True, help="Free-form notes.")
def add_application(
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

    @details
      You can provide either --company-id or --company-name (resolved to ID).
      --company-id takes precedence if both are provided.

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    companies = _read_table("companies")
    applications = _read_table("applications")

    resolved_company_id = company_id
    if not resolved_company_id:
        if not company_name:
            raise click.ClickException("You must provide either --company-id or --company-name.")
        resolved_company_id = _lookup_company_id_by_name(company_name, companies)
        if not resolved_company_id:
            raise click.ClickException(f'Company "{company_name}" not found. Add it first via add-company.')

    app_id = _new_id(TABLES["applications"]["id_prefix"])
    now = int(time.time())
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
    _write_table("applications", applications)
    logging.info("Added application: %s (company_id=%s)", app_id, resolved_company_id)
    click.echo(f"Added application: id={app_id}")


# --------------------------- add-contact ------------------------------------
@cli.command("add-contact")
@click.option("--company-name", shell_complete=complete_company_names, help="Company name (will be resolved to company_id).")
@click.option("--company-id", shell_complete=complete_company_ids, help="Company ID (overrides company-name if provided).")
@click.option("--name", "person_name", prompt="Contact Name", help="Contact full name.")
@click.option("--title", default="", show_default=True, help="Contact title/role.")
@click.option("--email", default="", show_default=True, help="Contact email.")
@click.option("--phone", default="", show_default=True, help="Contact phone.")
@click.option("--notes", default="", show_default=True, help="Notes about the contact.")
def add_contact(
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

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    companies = _read_table("companies")
    contacts = _read_table("contacts")

    resolved_company_id = company_id
    if not resolved_company_id:
        if not company_name:
            raise click.ClickException("You must provide either --company-id or --company-name.")
        resolved_company_id = _lookup_company_id_by_name(company_name, companies)
        if not resolved_company_id:
            raise click.ClickException(f'Company "{company_name}" not found. Add it first via add-company.')

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
    _write_table("contacts", contacts)
    logging.info("Added contact: %s (company_id=%s)", contact_id, resolved_company_id)
    click.echo(f"Added contact: id={contact_id}")


# --------------------------- add-stage --------------------------------------
@cli.command("add-stage")
@click.option("--application-id", required=True, shell_complete=complete_application_ids, help="Application ID to append a stage.")
@click.option("--stage", prompt="Stage", help="E.g., Applied, Recruiter Screen, Phone, Onsite, Offer.")
@click.option("--date", default="", show_default=True, help="YYYY-MM-DD or epoch; free text accepted.")
@click.option("--outcome", default="", show_default=True, help="E.g., scheduled, passed, failed, pending.")
@click.option("--notes", default="", show_default=True, help="Notes for this stage.")
def add_stage(application_id: str, stage: str, date: str, outcome: str, notes: str) -> None:
    """
    @brief Append a stage (pipeline event) to an application.

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    applications = _read_table("applications")
    stages = _read_table("stages")

    if not any(a.get("application_id") == application_id for a in applications):
        raise click.ClickException(f"Application not found: {application_id}")

    stage_id = _new_id(TABLES["stages"]["id_prefix"])
    row = {
        "stage_id": stage_id,
        "application_id": application_id,
        "stage": stage,
        "date": date,
        "outcome": outcome,
        "notes": notes,
    }
    stages.append(row)
    _write_table("stages", stages)

    for a in applications:
        if a.get("application_id") == application_id:
            a["last_update"] = int(time.time())
            break
    _write_table("applications", applications)

    logging.info("Added stage: %s (application_id=%s)", stage_id, application_id)
    click.echo(f"Added stage: id={stage_id}")


# ============================ REMOVE COMMANDS ================================
@cli.group("remove")
def remove_group() -> None:
    """
    @brief Group of remove (delete) commands.
    @return None
    """
    pass


@remove_group.command("company")
@click.option("--company-id", shell_complete=complete_company_ids, help="Company ID to remove.")
@click.option("--name", "company_name", shell_complete=complete_company_names, help="Company name to remove (case-insensitive).")
@click.option("--cascade", is_flag=True, help="Also remove related applications, stages, and contacts.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
def remove_company(company_id: Optional[str], company_name: Optional[str], cascade: bool, yes: bool) -> None:
    """
    @brief Remove a company. Optionally cascade delete related data.

    @details
      If --cascade is not provided and there are related rows, the command aborts.

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    if not company_id and not company_name:
        raise click.ClickException("Provide --company-id or --name.")

    companies = _read_table("companies")
    applications = _read_table("applications")
    contacts = _read_table("contacts")
    stages = _read_table("stages")

    resolved_company_id = company_id
    if not resolved_company_id:
        resolved_company_id = _lookup_company_id_by_name(company_name or "", companies)
        if not resolved_company_id:
            raise click.ClickException("Company not found.")

    # Gather related for summary / safety
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

    # Delete company
    companies_filtered, n_companies = _filter_delete(
        companies, lambda r: r.get("company_id") == resolved_company_id
    )

    # Cascade deletes
    n_apps = n_contacts = n_stages = 0
    if cascade:
        applications_filtered, n_apps = _filter_delete(
            applications, lambda r: r.get("company_id") == resolved_company_id
        )
        app_ids_to_remove = {a.get("application_id") for a in related_apps}
        stages_filtered, n_stages = _filter_delete(
            stages, lambda r: r.get("application_id") in app_ids_to_remove
        )
        contacts_filtered, n_contacts = _filter_delete(
            contacts, lambda r: r.get("company_id") == resolved_company_id
        )
        _write_table("applications", applications_filtered)
        _write_table("stages", stages_filtered)
        _write_table("contacts", contacts_filtered)

    _write_table("companies", companies_filtered)

    logging.info(
        "Removed company %s (cascade=%s): companies=%d, apps=%d, stages=%d, contacts=%d",
        resolved_company_id, cascade, n_companies, n_apps, n_stages, n_contacts
    )
    click.echo(
        f"Removed: companies={n_companies}, applications={n_apps}, stages={n_stages}, contacts={n_contacts}"
    )


@remove_group.command("application")
@click.option("--application-id", required=True, shell_complete=complete_application_ids, help="Application ID to remove.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
def remove_application(application_id: str, yes: bool) -> None:
    """
    @brief Remove an application and its stages.

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    applications = _read_table("applications")
    stages = _read_table("stages")

    if not any(a.get("application_id") == application_id for a in applications):
        raise click.ClickException(f"Application not found: {application_id}")

    if not yes:
        click.echo(f"About to delete application {application_id} and its stages.")
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    applications_filtered, n_apps = _filter_delete(
        applications, lambda r: r.get("application_id") == application_id
    )
    stages_filtered, n_stages = _filter_delete(
        stages, lambda r: r.get("application_id") == application_id
    )

    _write_table("applications", applications_filtered)
    _write_table("stages", stages_filtered)

    logging.info("Removed application %s: applications=%d, stages=%d", application_id, n_apps, n_stages)
    click.echo(f"Removed: applications={n_apps}, stages={n_stages}")


@remove_group.command("contact")
@click.option("--contact-id", required=True, shell_complete=complete_contact_ids, help="Contact ID to remove.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
def remove_contact(contact_id: str, yes: bool) -> None:
    """
    @brief Remove a contact.

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    contacts = _read_table("contacts")

    if not any(c.get("contact_id") == contact_id for c in contacts):
        raise click.ClickException(f"Contact not found: {contact_id}")

    if not yes:
        click.echo(f"About to delete contact {contact_id}.")
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    contacts_filtered, n_contacts = _filter_delete(
        contacts, lambda r: r.get("contact_id") == contact_id
    )
    _write_table("contacts", contacts_filtered)

    logging.info("Removed contact %s: contacts=%d", contact_id, n_contacts)
    click.echo(f"Removed: contacts={n_contacts}")


@remove_group.command("stage")
@click.option("--stage-id", required=True, shell_complete=complete_stage_ids, help="Stage ID to remove.")
@click.option("-y", "--yes", is_flag=True, help="Do not prompt for confirmation.")
def remove_stage(stage_id: str, yes: bool) -> None:
    """
    @brief Remove a single stage (pipeline event).

    @return None
    @throws click.ClickException On validation or I/O errors.
    """
    stages = _read_table("stages")

    if not any(s.get("stage_id") == stage_id for s in stages):
        raise click.ClickException(f"Stage not found: {stage_id}")

    if not yes:
        click.echo(f"About to delete stage {stage_id}.")
        if not click.confirm("Proceed?"):
            raise click.ClickException("Aborted by user.")

    stages_filtered, n_stages = _filter_delete(
        stages, lambda r: r.get("stage_id") == stage_id
    )
    _write_table("stages", stages_filtered)

    logging.info("Removed stage %s: stages=%d", stage_id, n_stages)
    click.echo(f"Removed: stages={n_stages}")


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
def update_application(
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

    @details
      Selects the application by --application-id or --job-url (ID takes precedence).
      Only provided fields are updated. Updates last_update timestamp.

    @return None
    @throws click.ClickException If selection fails or I/O errors occur.
    """
    import time

    if not application_id and not job_url:
        raise click.ClickException("Provide --application-id or --job-url to select the application.")

    applications = _read_table("applications")

    # Find target row
    target = None
    for a in applications:
        if application_id and a.get("application_id") == application_id:
            target = a
            break
        if (not application_id) and job_url and a.get("job_url") == job_url:
            target = a
            break

    if target is None:
        sel = application_id or job_url or "<unknown>"
        raise click.ClickException(f"Application not found for selector: {sel}")

    # Apply updates (only fields provided)
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

    target["last_update"] = int(time.time())

    _write_table("applications", applications)
    logging.info(
        "Updated application %s (via %s)",
        target.get("application_id"),
        "application-id" if application_id else "job-url",
    )
    click.echo(f'Updated application id={target.get("application_id")}')


# =============================================================================
# Entrypoint
# =============================================================================
if __name__ == "__main__":
    cli()
