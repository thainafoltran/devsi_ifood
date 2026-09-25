import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "banco_dados", "ifood_clone.db")


IntegrityError = sqlite3.IntegrityError


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON") 
    conn.row_factory = sqlite3.Row  
    return conn


def _row_to_dict(row):
    return dict(row) if row is not None else None


def run_query(query, params=None, fetch=False, fetchone=False, commit=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())

        result = None
        if fetch:
            result = [dict(r) for r in cursor.fetchall()]
        elif fetchone:
            result = _row_to_dict(cursor.fetchone())

        if commit:
            conn.commit()
            result = cursor.lastrowid

        return result
    finally:
        cursor.close()
        conn.close()


def init_db():

    schema_path = os.path.join(BASE_DIR, "banco_dados", "schema_sqlite.sql")
    conn = get_connection()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()