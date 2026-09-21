"""
Camada de acesso ao banco de dados MySQL.
Usa mysql-connector-python com queries parametrizadas (evita SQL Injection).
"""
import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Abre e retorna uma nova conexão com o MySQL."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "ifood_clone"),
        )
        return conn
    except Error as e:
        print(f"[ERRO] Falha ao conectar no MySQL: {e}")
        raise


def run_query(query, params=None, fetch=False, fetchone=False, commit=False):
    """
    Executa uma query de forma segura.
    - fetch=True      -> retorna todas as linhas (list[dict])
    - fetchone=True   -> retorna uma linha (dict) ou None
    - commit=True     -> confirma alterações (INSERT/UPDATE/DELETE)
                          e retorna o lastrowid quando aplicável
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())

        result = None
        if fetch:
            result = cursor.fetchall()
        elif fetchone:
            result = cursor.fetchone()

        if commit:
            conn.commit()
            result = cursor.lastrowid

        return result
    finally:
        cursor.close()
        conn.close()