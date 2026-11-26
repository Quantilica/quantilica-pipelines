-- DDL do registro dos conjuntos publicados (schema `publicacao`): conjunto, medida,
-- entidade e carga. Referência versionada ao lado de `publicacao_ddl.py`, que cria as
-- tabelas de dados; a origem é a migração `p137_publicacao.py` do portal (sem os GRANT, que
-- dependem de variável de ambiente). Um teste do portal falha se este arquivo divergir da
-- migração. Idempotente. Não edite à mão: veja o teste do portal para regravar.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'publicacao') THEN
        IF has_database_privilege(current_user, current_database(), 'CREATE') THEN
            CREATE SCHEMA publicacao;
        ELSE
            RAISE EXCEPTION
                'schema publicacao ausente e o papel % nao pode cria-lo: rode antes, como dono do banco: CREATE SCHEMA IF NOT EXISTS publicacao AUTHORIZATION %;',
                current_user, current_user;
        END IF;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS publicacao.conjunto (
    id text PRIMARY KEY,
    fonte text NOT NULL,
    slug text NOT NULL,
    schema_versao integer NOT NULL,
    estado text NOT NULL DEFAULT 'rascunho',
    titulo text NOT NULL,
    titulo_curto text NOT NULL DEFAULT '',
    descricao text NOT NULL DEFAULT '',
    catalogo_dataset_id text,
    declaracao jsonb NOT NULL,
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_publicacao_conjunto_estado
        CHECK (estado IN ('rascunho', 'publicado', 'aposentado')),
    CONSTRAINT ck_publicacao_conjunto_id CHECK (id = fonte || '/' || slug),
    CONSTRAINT uq_publicacao_conjunto_fonte_slug UNIQUE (fonte, slug)
);

CREATE TABLE IF NOT EXISTS publicacao.medida (
    conjunto_id text NOT NULL
        REFERENCES publicacao.conjunto (id) ON DELETE CASCADE,
    medida_id text NOT NULL,
    ordem integer NOT NULL DEFAULT 0,
    rotulo text NOT NULL,
    descricao text NOT NULL DEFAULT '',
    unidade text NOT NULL DEFAULT '',
    tipo text NOT NULL,
    aditiva boolean NOT NULL DEFAULT false,
    conjunto_titulo text NOT NULL DEFAULT '',
    busca tsvector GENERATED ALWAYS AS (
        to_tsvector(
            'portuguese',
            coalesce(conjunto_titulo, '') || ' ' || coalesce(rotulo, '') || ' '
            || coalesce(descricao, '') || ' ' || coalesce(unidade, '')
        )
    ) STORED,
    PRIMARY KEY (conjunto_id, medida_id),
    CONSTRAINT ck_publicacao_medida_tipo
        CHECK (tipo IN ('bigint', 'double', 'numeric'))
);

CREATE INDEX IF NOT EXISTS ix_publicacao_medida_busca ON publicacao.medida USING gin (busca);

CREATE TABLE IF NOT EXISTS publicacao.entidade (
    tipo text NOT NULL,
    chave text NOT NULL,
    rotulo text NOT NULL DEFAULT '',
    atributos jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (tipo, chave)
);

CREATE TABLE IF NOT EXISTS publicacao.carga (
    conjunto_id text NOT NULL
        REFERENCES publicacao.conjunto (id) ON DELETE CASCADE,
    nivel text NOT NULL,
    assinatura text NOT NULL DEFAULT '',
    linhas integer NOT NULL DEFAULT 0,
    periodo_min text,
    periodo_max text,
    carregado_em timestamptz NOT NULL DEFAULT now(),
    detalhes jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (conjunto_id, nivel)
);
