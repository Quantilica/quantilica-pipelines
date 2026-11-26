"""Fixture do registro de fetchers, para derivar o caminho do ``lake.py``.

Por padrão o registro é a cópia mínima abaixo, sem rede. Com
``QUANTILICA_REGISTRO_PUBLICO=1`` os testes leem o registro público pela função
de cache do ``quantilica-cli`` (``quantilica.cli.sources.registro_publico``).
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest

_BASE = "https://github.com/Quantilica"

# Recorte do registro v2: `id`, `lake_source_id`, `repo` e `module` das fontes de
# lake_aliases.toml. O `lake_source_id` é a chave do lake e não muda num renome do
# fetcher (o `id` muda); aqui os dois coincidem.
_FETCHERS = {
    "b3": "b3_fetcher",
    "cvm": "cvm_fetcher",
    "comex": "comex_fetcher",
    "bcb-microdados": "bcb_microdados_fetcher",
    "rfb-cnpj": "rfb_cnpj_fetcher",
    "tesouro-direto": "tesouro_direto_fetcher",
    "pdet": "pdet_fetcher",
    "anac": "anac_fetcher",
}

REGISTRO_FIXTURE: dict[str, Any] = {
    "version": 2,
    "fetchers": [
        {
            "id": fid,
            "lake_source_id": fid,
            "module": module,
            "repo": f"{_BASE}/{fid}-fetcher",
        }
        for fid, module in _FETCHERS.items()
    ],
}


@pytest.fixture(scope="session")
def registro() -> dict[str, Any]:
    if os.environ.get("QUANTILICA_REGISTRO_PUBLICO") == "1":
        from quantilica.cli.sources import registro_publico

        doc = registro_publico()
        if not doc:
            pytest.skip("registro público indisponível (sem cli, rede ou cache)")
        return doc
    return REGISTRO_FIXTURE


# ---------------------------------------------------------------------------
# PostgreSQL descartável para os testes de contrato e de resultado
# ---------------------------------------------------------------------------
def _ausente(motivo: str) -> None:
    """No CI (``CI`` definido) a falta do banco ou do pacote reprova; local, pula."""
    if os.environ.get("CI"):
        pytest.fail(motivo, pytrace=False)
    pytest.skip(motivo)


@pytest.fixture(scope="session")
def pg_url() -> str:
    """URL do banco descartável (``QUANTILICA_TEST_DATABASE_URL``), nunca produção."""
    url = os.environ.get("QUANTILICA_TEST_DATABASE_URL")
    if not url:
        _ausente("QUANTILICA_TEST_DATABASE_URL ausente")
    try:
        import psycopg  # noqa: F401
        import quantilica_sql  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        _ausente(f"quantilica-sql não instalado ({exc})")
    return url  # type: ignore[return-value]


def _adaptador(classe: type, schema: str) -> Any:
    """Instância do adaptador gravando em ``schema`` (e não em ``ibge_sidra``)."""
    return type(classe.__name__, (classe,), {"schema": property(lambda _s: schema)})()


@pytest.fixture(scope="module")
def pg_conn(pg_url):
    """Conexão (autocommit) ao banco descartável; os schemas de teste são apagados
    pelas fixtures que os criam."""
    import psycopg

    conn = psycopg.connect(pg_url, autocommit=True)
    yield conn
    conn.close()


def _com_schema(conn, schema: str):
    from psycopg import sql

    yield schema
    conn.execute(
        sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
    )


@pytest.fixture(scope="module")
def schema_sidra_vazio(pg_conn):
    """Esquema do SIDRA criado vazio pelo ``quantilica-sql`` (o contrato das SQL)."""
    from quantilica_sql.sidra.esquema import criar_esquema

    schema = f"qpipe_sidra_{uuid.uuid4().hex[:8]}"

    criar_esquema(pg_conn, schema)
    yield from _com_schema(pg_conn, schema)


@pytest.fixture(scope="module")
def schema_sidra_carregado(pg_conn):
    """Esquema do SIDRA com as fixtures reais de ``tests/data/sidra`` carregadas pelo
    adaptador (o caminho da CLI: ``load sidra -s <raiz> --all``)."""
    from pathlib import Path

    from quantilica_sql.adapters.sidra import SidraAdapter

    schema = f"qpipe_sidra_{uuid.uuid4().hex[:8]}"
    raiz = Path(__file__).parent / "data" / "sidra"
    adaptador = _adaptador(SidraAdapter, schema)
    adaptador.load(pg_conn, raiz, all_partitions=True)
    yield from _com_schema(pg_conn, schema)


@pytest.fixture(scope="module")
def schema_bcb_vazio(pg_conn):
    """Esquema do BCB SGS criado vazio pelo adaptador, mais um ``series_metadata``
    mínimo (nenhum adaptador do ``quantilica-sql`` o cria: ``test_bcb_contrato``)."""
    from quantilica_sql.adapters.bcb import BcbAdapter

    schema = f"qpipe_bcb_{uuid.uuid4().hex[:8]}"
    adaptador = _adaptador(BcbAdapter, schema)
    adaptador._ensure_tables(pg_conn)
    from psycopg import sql

    pg_conn.execute(
        sql.SQL(
            "CREATE TABLE {} (series_id integer PRIMARY KEY, name text, "
            "name_abbreviated text, unit text, frequency text, "
            "theme_hierarchy text[])"
        ).format(sql.Identifier(schema, "series_metadata"))
    )
    yield from _com_schema(pg_conn, schema)
