-- ============================================================
-- Ifood Clone - Script de criação do banco de dados (MySQL)
-- Entrega 1: Autenticação (contas), Restaurantes e Produtos
-- ============================================================

CREATE DATABASE IF NOT EXISTS ifood_clone
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ifood_clone;

-- ------------------------------------------------------------
-- Tabela: contas
-- Guarda tanto contas criadas com email/senha (tipo_login=local)
-- quanto contas criadas via login social (tipo_login=google/facebook)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contas (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    nome              VARCHAR(150)        NOT NULL,
    email             VARCHAR(150)        NOT NULL,
    senha_hash        VARCHAR(255)        NULL,        -- NULL quando login social
    tipo_login        ENUM('local','google','facebook') NOT NULL DEFAULT 'local',
    provider_id       VARCHAR(120)        NULL,        -- id retornado pelo provedor (sub do Google, id do Facebook)
    telefone          VARCHAR(20)         NULL,
    foto_url          VARCHAR(255)        NULL,
    ativo             TINYINT(1)          NOT NULL DEFAULT 1,
    data_criacao      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao  DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_contas_email (email),
    UNIQUE KEY uq_contas_provider (tipo_login, provider_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Tabela: restaurantes
-- Cada restaurante pertence a uma conta (dono/parceiro)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS restaurantes (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    conta_id            INT             NOT NULL,
    nome                VARCHAR(150)    NOT NULL,
    categoria           VARCHAR(80)     NOT NULL,   -- ex: Lanches, Pizza, Japonesa
    descricao           TEXT            NULL,
    endereco            VARCHAR(255)    NOT NULL,
    cidade              VARCHAR(100)    NOT NULL,
    telefone            VARCHAR(20)     NULL,
    taxa_entrega        DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    tempo_entrega_min   INT             NOT NULL DEFAULT 30,
    tempo_entrega_max   INT             NOT NULL DEFAULT 45,
    avaliacao           DECIMAL(2,1)    NOT NULL DEFAULT 0.0,  -- 0.0 a 5.0
    imagem_url          VARCHAR(255)    NULL,
    ativo               TINYINT(1)      NOT NULL DEFAULT 1,
    data_criacao        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_restaurantes_conta
        FOREIGN KEY (conta_id) REFERENCES contas(id)
        ON DELETE CASCADE,
    CONSTRAINT chk_avaliacao CHECK (avaliacao BETWEEN 0 AND 5)
) ENGINE=InnoDB;

CREATE INDEX idx_restaurantes_categoria ON restaurantes(categoria);
CREATE INDEX idx_restaurantes_cidade ON restaurantes(cidade);

-- ------------------------------------------------------------
-- Tabela: produtos (refeições e lanches do restaurante)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produtos (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    restaurante_id    INT             NOT NULL,
    nome              VARCHAR(150)    NOT NULL,
    descricao         TEXT            NULL,
    categoria         VARCHAR(80)     NOT NULL,   -- ex: Lanche, Bebida, Sobremesa
    preco             DECIMAL(10,2)   NOT NULL,
    imagem_url        VARCHAR(255)    NULL,
    disponivel        TINYINT(1)      NOT NULL DEFAULT 1,
    data_criacao      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_produtos_restaurante
        FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id)
        ON DELETE CASCADE,
    CONSTRAINT chk_preco CHECK (preco >= 0)
) ENGINE=InnoDB;

CREATE INDEX idx_produtos_restaurante ON produtos(restaurante_id);
CREATE INDEX idx_produtos_categoria ON produtos(categoria);

-- ------------------------------------------------------------
-- Dado de exemplo (opcional, ajuda a testar o CRUD rapidamente)
-- ------------------------------------------------------------
-- INSERT INTO contas (nome, email, senha_hash, tipo_login)
-- VALUES ('Admin Teste', 'admin@teste.com', NULL, 'local');