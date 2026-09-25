-- ============================================================
-- Ifood Clone - Script de criação das tabelas (SQLite)
-- Entrega 1: Autenticação (contas), Restaurantes e Produtos
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Tabela: contas
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nome              TEXT    NOT NULL,
    email             TEXT    NOT NULL UNIQUE,
    senha_hash        TEXT    NULL,        -- NULL quando login social
    tipo_login        TEXT    NOT NULL DEFAULT 'local'
                              CHECK (tipo_login IN ('local','google','facebook')),
    provider_id       TEXT    NULL,
    telefone          TEXT    NULL,
    foto_url          TEXT    NULL,
    ativo             INTEGER NOT NULL DEFAULT 1,
    data_criacao      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    data_atualizacao  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (tipo_login, provider_id)
);

-- ------------------------------------------------------------
-- Tabela: restaurantes
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS restaurantes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id            INTEGER NOT NULL,
    nome                TEXT    NOT NULL,
    categoria           TEXT    NOT NULL,
    descricao           TEXT    NULL,
    endereco            TEXT    NOT NULL,
    cidade              TEXT    NOT NULL,
    telefone            TEXT    NULL,
    taxa_entrega        REAL    NOT NULL DEFAULT 0.00,
    tempo_entrega_min   INTEGER NOT NULL DEFAULT 30,
    tempo_entrega_max   INTEGER NOT NULL DEFAULT 45,
    avaliacao           REAL    NOT NULL DEFAULT 0.0 CHECK (avaliacao BETWEEN 0 AND 5),
    imagem_url          TEXT    NULL,
    ativo               INTEGER NOT NULL DEFAULT 1,
    data_criacao        TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    data_atualizacao    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (conta_id) REFERENCES contas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_restaurantes_categoria ON restaurantes(categoria);
CREATE INDEX IF NOT EXISTS idx_restaurantes_cidade ON restaurantes(cidade);

-- ------------------------------------------------------------
-- Tabela: produtos (refeições e lanches do restaurante)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produtos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id    INTEGER NOT NULL,
    nome              TEXT    NOT NULL,
    descricao         TEXT    NULL,
    categoria         TEXT    NOT NULL,
    preco             REAL    NOT NULL CHECK (preco >= 0),
    imagem_url        TEXT    NULL,
    disponivel        INTEGER NOT NULL DEFAULT 1,
    data_criacao      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    data_atualizacao  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_produtos_restaurante ON produtos(restaurante_id);
CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria);