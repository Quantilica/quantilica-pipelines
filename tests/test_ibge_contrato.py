"""Contrato das SQL de ``ibge/**`` com o esquema do SIDRA do ``quantilica-sql``.

Cada SQL que lê a superfície do ``sidra-sql`` legado (``dados``, ``dimensao``,
``localidade``, ``periodo``) passa por ``EXPLAIN`` contra o esquema que o
``quantilica load sidra`` cria (vazio): coluna que sumiu, tipo que mudou ou tabela
que deixou de existir reprova aqui, antes de chegar a uma carga real.

As SQL que leem ``analytics.*`` (marts que o próprio catálogo materializa) ficam fora,
com o motivo em ``_catalogo.FORA_DO_CONTRATO_SIDRA``; ``test_catalogo_descoberta``
garante que a lista é exatamente a das que leem ``analytics``.

Exige ``QUANTILICA_TEST_DATABASE_URL`` (banco descartável); no CI a ausência reprova.
"""

from __future__ import annotations

import pytest
from _catalogo import rel, sql_ibge_do_contrato, usar_schema

SQLS = sql_ibge_do_contrato()


@pytest.mark.parametrize("sql_path", SQLS, ids=rel)
def test_sql_le_o_esquema_do_quantilica_sql(sql_path, pg_conn, schema_sidra_vazio):
    usar_schema(pg_conn, schema_sidra_vazio)
    pg_conn.execute("EXPLAIN " + sql_path.read_text(encoding="utf-8"))
