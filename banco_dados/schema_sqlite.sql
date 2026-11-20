-- =====================================================================
-- DevSI - 2ª avaliação | Banco: SQLite 3 | Script de criação (idempotente)
-- =====================================================================
PRAGMA foreign_keys = ON;

-- ---------- AUTENTICAÇÃO / CONTAS ----------
CREATE TABLE IF NOT EXISTS contas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(120) NOT NULL,
    email         VARCHAR(160) NOT NULL UNIQUE,
    senha_hash    VARCHAR(255),                                   -- NULL em contas sociais
    tipo_login    VARCHAR(10)  NOT NULL DEFAULT 'local'
                  CHECK (tipo_login IN ('local','google','facebook')),
    provider_id   VARCHAR(64),
    foto_url      VARCHAR(500),
    telefone      VARCHAR(20),
    ativo         INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    data_criacao  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_contas_provider ON contas(tipo_login, provider_id);

CREATE TABLE IF NOT EXISTS codigos_login (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id      INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    canal         VARCHAR(10) NOT NULL CHECK (canal IN ('email','sms','whatsapp')),
    destino       VARCHAR(160) NOT NULL,
    codigo_hash   CHAR(64) NOT NULL,                              -- HMAC-SHA256 do código de 6 dígitos
    tentativas    INTEGER NOT NULL DEFAULT 0,
    usado         INTEGER NOT NULL DEFAULT 0 CHECK (usado IN (0,1)),
    criado_em     DATETIME NOT NULL,
    expira_em     DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_codigos_conta ON codigos_login(conta_id, usado);

-- ---------- LOCAIS (ENDEREÇOS DO USUÁRIO) ----------
CREATE TABLE IF NOT EXISTS enderecos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id      INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    apelido       VARCHAR(30)  NOT NULL,
    cep           CHAR(8)      NOT NULL,
    logradouro    VARCHAR(150) NOT NULL,
    numero        VARCHAR(10)  NOT NULL,
    complemento   VARCHAR(80),
    bairro        VARCHAR(80)  NOT NULL,
    cidade        VARCHAR(80)  NOT NULL,
    uf            CHAR(2)      NOT NULL,
    latitude      REAL CHECK (latitude  BETWEEN -90  AND 90),
    longitude     REAL CHECK (longitude BETWEEN -180 AND 180),
    principal     INTEGER NOT NULL DEFAULT 0 CHECK (principal IN (0,1)),
    data_criacao  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_enderecos_conta ON enderecos(conta_id);

-- ---------- RESTAURANTES E PRODUTOS ----------
CREATE TABLE IF NOT EXISTS restaurantes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id           INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    nome               VARCHAR(120) NOT NULL,
    categoria          VARCHAR(40)  NOT NULL,
    descricao          VARCHAR(500),
    endereco           VARCHAR(200) NOT NULL,
    cidade             VARCHAR(80)  NOT NULL,
    latitude           REAL CHECK (latitude  BETWEEN -90  AND 90),
    longitude          REAL CHECK (longitude BETWEEN -180 AND 180),
    telefone           VARCHAR(20),
    taxa_entrega       REAL NOT NULL DEFAULT 0 CHECK (taxa_entrega >= 0),
    tempo_entrega_min  INTEGER NOT NULL DEFAULT 30 CHECK (tempo_entrega_min > 0),
    tempo_entrega_max  INTEGER NOT NULL DEFAULT 45,
    avaliacao          REAL NOT NULL DEFAULT 0 CHECK (avaliacao BETWEEN 0 AND 5),
    ativo              INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    data_criacao       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (tempo_entrega_min <= tempo_entrega_max)
);
CREATE INDEX IF NOT EXISTS ix_restaurantes_categoria ON restaurantes(categoria);

CREATE TABLE IF NOT EXISTS produtos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id  INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    nome            VARCHAR(120) NOT NULL,
    descricao       VARCHAR(500),
    categoria       VARCHAR(30)  NOT NULL
                    CHECK (categoria IN ('Lanche','Refeição','Bebida','Sobremesa','Entrada','Combo')),
    preco           REAL NOT NULL CHECK (preco >= 0),
    imagem_url      VARCHAR(500),
    disponivel      INTEGER NOT NULL DEFAULT 1 CHECK (disponivel IN (0,1)),
    data_criacao    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_produtos_rest ON produtos(restaurante_id);

-- ---------- FAVORITOS ----------
CREATE TABLE IF NOT EXISTS favoritos_restaurantes (
    conta_id        INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    restaurante_id  INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (conta_id, restaurante_id)
);
CREATE TABLE IF NOT EXISTS favoritos_produtos (
    conta_id    INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    produto_id  INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (conta_id, produto_id)
);

-- ---------- CESTA ----------
CREATE TABLE IF NOT EXISTS cestas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id        INTEGER NOT NULL UNIQUE REFERENCES contas(id) ON DELETE CASCADE,
    restaurante_id  INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    atualizada_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cesta_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cesta_id        INTEGER NOT NULL REFERENCES cestas(id) ON DELETE CASCADE,
    produto_id      INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    quantidade      INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 20),
    observacao      VARCHAR(140),
    UNIQUE (cesta_id, produto_id)
);

-- ---------- PEDIDOS ----------
CREATE TABLE IF NOT EXISTS pedidos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id         INTEGER NOT NULL REFERENCES contas(id),
    restaurante_id   INTEGER NOT NULL REFERENCES restaurantes(id),
    endereco_id      INTEGER REFERENCES enderecos(id) ON DELETE SET NULL,
    endereco_texto   VARCHAR(300),                                -- cópia do endereço no momento do pedido
    tipo_entrega     VARCHAR(10) NOT NULL CHECK (tipo_entrega IN ('entrega','retirada')),
    subtotal         REAL NOT NULL CHECK (subtotal >= 0),
    taxa_frete       REAL NOT NULL DEFAULT 0 CHECK (taxa_frete >= 0),
    total            REAL NOT NULL CHECK (total >= 0),
    distancia_km     REAL,
    status           VARCHAR(25) NOT NULL DEFAULT 'recebido'
                     CHECK (status IN ('recebido','confirmado','em_preparo','saiu_para_entrega',
                                       'pronto_para_retirada','entregue','cancelado')),
    criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pedidos_conta ON pedidos(conta_id);
CREATE INDEX IF NOT EXISTS ix_pedidos_rest  ON pedidos(restaurante_id, status);

CREATE TABLE IF NOT EXISTS pedido_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id      INTEGER REFERENCES produtos(id) ON DELETE SET NULL,
    nome            VARCHAR(120) NOT NULL,                        -- cópia (histórico)
    preco_unitario  REAL NOT NULL CHECK (preco_unitario >= 0),
    quantidade      INTEGER NOT NULL CHECK (quantidade > 0),
    observacao      VARCHAR(140),
    total_item      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pagamentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL UNIQUE REFERENCES pedidos(id) ON DELETE CASCADE,
    forma           VARCHAR(15) NOT NULL
                    CHECK (forma IN ('pix','cartao_credito','cartao_debito','dinheiro')),
    valor           REAL NOT NULL CHECK (valor >= 0),
    status          VARCHAR(10) NOT NULL CHECK (status IN ('pendente','aprovado','recusado','estornado')),
    bandeira        VARCHAR(20),
    cartao_final    CHAR(4),                                      -- só os 4 últimos dígitos
    troco_para      REAL,
    transacao_id    VARCHAR(40),
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedido_status_historico (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id   INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    status      VARCHAR(25) NOT NULL,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);






#ENTREGA 1 
-- -- ============================================================
-- -- APP entregas - Script de criação das tabelas (SQLite)
-- -- Entrega 1: Autenticação (contas), Restaurantes e Produtos
-- -- ============================================================

-- PRAGMA foreign_keys = ON;

-- -- ------------------------------------------------------------
-- -- Tabela: contas
-- -- ------------------------------------------------------------
-- CREATE TABLE IF NOT EXISTS contas (
--     id                INTEGER PRIMARY KEY AUTOINCREMENT,
--     nome              TEXT    NOT NULL,
--     email             TEXT    NOT NULL UNIQUE,
--     senha_hash        TEXT    NULL,
--     tipo_login        TEXT    NOT NULL DEFAULT 'local'
--                               CHECK (tipo_login IN ('local','google','facebook')),
--     provider_id       TEXT    NULL,
--     telefone          TEXT    NULL,
--     foto_url          TEXT    NULL,
--     ativo             INTEGER NOT NULL DEFAULT 1,
--     data_criacao      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
--     data_atualizacao  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
--     UNIQUE (tipo_login, provider_id)
-- );

-- -- ------------------------------------------------------------
-- -- Tabela: restaurantes
-- -- ------------------------------------------------------------
-- CREATE TABLE IF NOT EXISTS restaurantes (
--     id                  INTEGER PRIMARY KEY AUTOINCREMENT,
--     conta_id            INTEGER NOT NULL,
--     nome                TEXT    NOT NULL,
--     categoria           TEXT    NOT NULL,
--     descricao           TEXT    NULL,
--     endereco            TEXT    NOT NULL,
--     cidade              TEXT    NOT NULL,
--     telefone            TEXT    NULL,
--     taxa_entrega        REAL    NOT NULL DEFAULT 0.00,
--     tempo_entrega_min   INTEGER NOT NULL DEFAULT 30,
--     tempo_entrega_max   INTEGER NOT NULL DEFAULT 45,
--     avaliacao           REAL    NOT NULL DEFAULT 0.0 CHECK (avaliacao BETWEEN 0 AND 5),
--     imagem_url          TEXT    NULL,
--     ativo               INTEGER NOT NULL DEFAULT 1,
--     data_criacao        TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
--     data_atualizacao    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
--     FOREIGN KEY (conta_id) REFERENCES contas(id) ON DELETE CASCADE
-- );

-- CREATE INDEX IF NOT EXISTS idx_restaurantes_categoria ON restaurantes(categoria);
-- CREATE INDEX IF NOT EXISTS idx_restaurantes_cidade ON restaurantes(cidade);

-- -- ------------------------------------------------------------
-- -- Tabela: produtos (refeições e lanches do restaurante)
-- -- ------------------------------------------------------------
-- CREATE TABLE IF NOT EXISTS produtos (
--     id                INTEGER PRIMARY KEY AUTOINCREMENT,
--     restaurante_id    INTEGER NOT NULL,
--     nome              TEXT    NOT NULL,
--     descricao         TEXT    NULL,
--     categoria         TEXT    NOT NULL,
--     preco             REAL    NOT NULL CHECK (preco >= 0),
--     imagem_url        TEXT    NULL,
--     disponivel        INTEGER NOT NULL DEFAULT 1,
--     data_criacao      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
--     data_atualizacao  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
--     FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
-- );

-- CREATE INDEX IF NOT EXISTS idx_produtos_restaurante ON produtos(restaurante_id);
-- CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria);