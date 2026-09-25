"""
Camada de acesso ao banco de dados SQLite.
Usa a biblioteca padrão do Python (sqlite3) - não precisa instalar nada.
O banco inteiro fica em um único arquivo: database/ifood_clone.db
"""
import os
import sqlite3

# Caminho do arquivo do banco (fica dentro da pasta database/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "banco_dados", "ifood_clone.db")

# Exposto para as rotas poderem tratar erros de UNIQUE/constraint,
# do mesmo jeito que faziam com mysql.connector.IntegrityError
IntegrityError = sqlite3.IntegrityError


def get_connection():
    """Abre e retorna uma nova conexão com o arquivo SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # o SQLite exige isso a cada conexão
    conn.row_factory = sqlite3.Row  # permite acessar colunas por nome (linha["coluna"])
    return conn


def _row_to_dict(row):
    return dict(row) if row is not None else None


def run_query(query, params=None, fetch=False, fetchone=False, commit=False):
    """
    Executa uma query de forma segura (query parametrizada, evita SQL Injection).
    - fetch=True      -> retorna todas as linhas (list[dict])
    - fetchone=True   -> retorna uma linha (dict) ou None
    - commit=True     -> confirma alterações (INSERT/UPDATE/DELETE)
                          e retorna o lastrowid quando aplicável
    """
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
    """Cria as tabelas a partir do schema_sqlite.sql, se ainda não existirem."""
    schema_path = os.path.join(BASE_DIR, "banco_dados", "schema_sqlite.sql")
    conn = get_connection()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()