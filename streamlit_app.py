import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

import streamlit as st


ROOT = Path(__file__).resolve().parent
LEGACY_CLIENTS = ROOT / "clientes.csv"
LEGACY_CONTACTS = ROOT / "contactos.csv"
DEFAULT_DATA_DIR = ROOT / ".jf_clientes"
DB_PATH = Path(os.environ.get("JF_CLIENTES_DB", DEFAULT_DATA_DIR / "clientes.sqlite3")).expanduser().resolve()


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if DB_PATH.parent == DEFAULT_DATA_DIR:
        DB_PATH.parent.chmod(0o700)
    try:
        descriptor = os.open(DB_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(descriptor)
    DB_PATH.chmod(0o600)

    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def normalized(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def initialize_database() -> None:
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
                legacy_client TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                activity_date TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        imported = connection.execute(
            "SELECT 1 FROM app_meta WHERE key = 'legacy_csv_imported'"
        ).fetchone()
        if imported:
            return

        client_ids: dict[str, int] = {}
        if LEGACY_CLIENTS.exists():
            with LEGACY_CLIENTS.open(encoding="utf-8-sig", newline="") as source:
                for row in csv.DictReader(source):
                    name = (row.get("nombre") or "").strip()
                    if not name:
                        continue
                    cursor = connection.execute(
                        "INSERT INTO clients (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                        (name, row.get("telefono", ""), row.get("email", ""), row.get("notas", "")),
                    )
                    client_ids[normalized(name)] = cursor.lastrowid

        if LEGACY_CONTACTS.exists():
            with LEGACY_CONTACTS.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.reader(source))
            if rows and normalized(rows[0][0]) in {"cliente", "client"}:
                rows.pop(0)
            for row in rows:
                if len(row) < 2 or not row[1].strip():
                    continue
                client_name, name = row[0].strip(), row[1].strip()
                connection.execute(
                    """INSERT INTO contacts
                       (client_id, legacy_client, name, role, phone, email)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        client_ids.get(normalized(client_name)),
                        client_name,
                        name,
                        row[2] if len(row) > 2 else "",
                        row[3] if len(row) > 3 else "",
                        row[4] if len(row) > 4 else "",
                    ),
                )

        connection.execute(
            "INSERT INTO app_meta (key, value) VALUES ('legacy_csv_imported', '1')"
        )


def rows(query: str, parameters: tuple = ()) -> list[sqlite3.Row]:
    with database() as connection:
        return connection.execute(query, parameters).fetchall()


def execute(query: str, parameters: tuple = ()) -> None:
    with database() as connection:
        connection.execute(query, parameters)


def client_label(client: sqlite3.Row) -> str:
    return client["name"] + (f" · {client['email']}" if client["email"] else "")


st.set_page_config(page_title="JF Clientes", page_icon=":material/contacts:", layout="centered")
initialize_database()
st.title("JF Clientes")
st.caption("Clientes, contactos y seguimiento")

clients = rows("SELECT * FROM clients ORDER BY name COLLATE NOCASE, id")

with st.expander("Añadir cliente", expanded=not clients):
    with st.form("new_client"):
        new_name = st.text_input("Nombre")
        new_phone = st.text_input("Teléfono")
        new_email = st.text_input("Email")
        new_notes = st.text_area("Notas")
        submitted = st.form_submit_button("Guardar cliente", type="primary")
    if submitted:
        if not new_name.strip():
            st.error("El nombre es obligatorio.")
        else:
            execute(
                "INSERT INTO clients (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                (new_name.strip(), new_phone.strip(), new_email.strip(), new_notes.strip()),
            )
            st.rerun()

if not clients:
    st.info("Añade un cliente para empezar.")
    st.stop()

selected_id = st.selectbox(
    "Seleccionar cliente",
    options=[client["id"] for client in clients],
    format_func=lambda client_id: client_label(next(c for c in clients if c["id"] == client_id)),
)
selected = next(client for client in clients if client["id"] == selected_id)

details_tab, contacts_tab, activities_tab = st.tabs(["Datos", "Contactos", "Actividades"])

with details_tab:
    st.subheader(selected["name"])
    with st.form("edit_client"):
        name = st.text_input("Nombre", value=selected["name"])
        phone = st.text_input("Teléfono", value=selected["phone"])
        email = st.text_input("Email", value=selected["email"])
        notes = st.text_area("Notas", value=selected["notes"])
        save_client = st.form_submit_button("Guardar cambios", type="primary")
    if save_client:
        if not name.strip():
            st.error("El nombre es obligatorio.")
        else:
            execute(
                "UPDATE clients SET name = ?, phone = ?, email = ?, notes = ? WHERE id = ?",
                (name.strip(), phone.strip(), email.strip(), notes.strip(), selected_id),
            )
            st.rerun()
    with st.expander("Eliminar cliente"):
        confirm_client = st.checkbox(
            "Confirmo eliminar este cliente y todos sus contactos y actividades.",
            key="confirm_client_delete",
        )
        if st.button("Eliminar cliente", disabled=not confirm_client):
            execute("DELETE FROM clients WHERE id = ?", (selected_id,))
            st.rerun()

with contacts_tab:
    contacts = rows("SELECT * FROM contacts WHERE client_id = ? ORDER BY name COLLATE NOCASE", (selected_id,))
    st.subheader("Contactos")
    if contacts:
        st.dataframe(
            [{"Nombre": c["name"], "Cargo": c["role"], "Teléfono": c["phone"], "Email": c["email"]} for c in contacts],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("Todavía no hay contactos.")

    with st.expander("Añadir contacto"):
        with st.form("new_contact"):
            contact_name = st.text_input("Nombre", key="new_contact_name")
            contact_role = st.text_input("Cargo", key="new_contact_role")
            contact_phone = st.text_input("Teléfono", key="new_contact_phone")
            contact_email = st.text_input("Email", key="new_contact_email")
            add_contact = st.form_submit_button("Guardar contacto", type="primary")
        if add_contact:
            if not contact_name.strip():
                st.error("El nombre es obligatorio.")
            else:
                execute(
                    """INSERT INTO contacts (client_id, name, role, phone, email)
                       VALUES (?, ?, ?, ?, ?)""",
                    (selected_id, contact_name.strip(), contact_role.strip(), contact_phone.strip(), contact_email.strip()),
                )
                st.rerun()

    if contacts:
        contact_id = st.selectbox(
            "Editar contacto",
            options=[contact["id"] for contact in contacts],
            format_func=lambda item_id: next(c["name"] for c in contacts if c["id"] == item_id),
        )
        contact = next(item for item in contacts if item["id"] == contact_id)
        with st.form("edit_contact"):
            edit_contact_name = st.text_input("Nombre", value=contact["name"], key="edit_contact_name")
            edit_contact_role = st.text_input("Cargo", value=contact["role"], key="edit_contact_role")
            edit_contact_phone = st.text_input("Teléfono", value=contact["phone"], key="edit_contact_phone")
            edit_contact_email = st.text_input("Email", value=contact["email"], key="edit_contact_email")
            save_contact = st.form_submit_button("Guardar cambios")
        if save_contact:
            if not edit_contact_name.strip():
                st.error("El nombre es obligatorio.")
            else:
                execute(
                    """UPDATE contacts SET name = ?, role = ?, phone = ?, email = ?
                       WHERE id = ? AND client_id = ?""",
                    (edit_contact_name.strip(), edit_contact_role.strip(), edit_contact_phone.strip(), edit_contact_email.strip(), contact_id, selected_id),
                )
                st.rerun()
        with st.expander("Eliminar contacto"):
            confirm_contact = st.checkbox("Confirmo eliminar este contacto.", key="confirm_contact_delete")
            if st.button("Eliminar contacto", disabled=not confirm_contact):
                execute("DELETE FROM contacts WHERE id = ? AND client_id = ?", (contact_id, selected_id))
                st.rerun()

with activities_tab:
    activities = rows(
        "SELECT * FROM activities WHERE client_id = ? ORDER BY activity_date DESC, id DESC",
        (selected_id,),
    )
    st.subheader("Actividades")
    if activities:
        st.dataframe(
            [{"Fecha": a["activity_date"], "Actividad": a["title"], "Notas": a["details"]} for a in activities],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("Todavía no hay actividades.")

    with st.expander("Añadir actividad"):
        with st.form("new_activity"):
            activity_title = st.text_input("Actividad", key="new_activity_title")
            activity_date = st.date_input("Fecha", value=date.today(), key="new_activity_date")
            activity_details = st.text_area("Notas", key="new_activity_details")
            add_activity = st.form_submit_button("Guardar actividad", type="primary")
        if add_activity:
            if not activity_title.strip():
                st.error("La actividad es obligatoria.")
            else:
                execute(
                    """INSERT INTO activities (client_id, activity_date, title, details)
                       VALUES (?, ?, ?, ?)""",
                    (selected_id, activity_date.isoformat(), activity_title.strip(), activity_details.strip()),
                )
                st.rerun()

    if activities:
        activity_id = st.selectbox(
            "Editar actividad",
            options=[activity["id"] for activity in activities],
            format_func=lambda item_id: next(a["title"] for a in activities if a["id"] == item_id),
        )
        activity = next(item for item in activities if item["id"] == activity_id)
        with st.form("edit_activity"):
            edit_activity_title = st.text_input("Actividad", value=activity["title"], key="edit_activity_title")
            edit_activity_date = st.date_input(
                "Fecha", value=date.fromisoformat(activity["activity_date"]), key="edit_activity_date"
            )
            edit_activity_details = st.text_area("Notas", value=activity["details"], key="edit_activity_details")
            save_activity = st.form_submit_button("Guardar cambios")
        if save_activity:
            if not edit_activity_title.strip():
                st.error("La actividad es obligatoria.")
            else:
                execute(
                    """UPDATE activities SET activity_date = ?, title = ?, details = ?
                       WHERE id = ? AND client_id = ?""",
                    (edit_activity_date.isoformat(), edit_activity_title.strip(), edit_activity_details.strip(), activity_id, selected_id),
                )
                st.rerun()
        with st.expander("Eliminar actividad"):
            confirm_activity = st.checkbox("Confirmo eliminar esta actividad.", key="confirm_activity_delete")
            if st.button("Eliminar actividad", disabled=not confirm_activity):
                execute("DELETE FROM activities WHERE id = ? AND client_id = ?", (activity_id, selected_id))
                st.rerun()