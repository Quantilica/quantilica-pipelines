"""Contrato das SQL de ``macro/**`` e ``setorial/**`` com ``series_data`` do BCB SGS.

As 13 SQL que leem ``series_data`` (``series_id``, ``date``, ``date_end``, ``value``,
``ativo``) passam por ``EXPLAIN`` contra a tabela que o ``quantilica load bcb`` cria
(vazia). Elas também juntam ``series_metadata`` (``series_id``, ``name``,
``name_abbreviated``, ``unit``, ``frequency``, ``theme_hierarchy``), que nenhum
adaptador do ``quantilica-sql`` cria: o teste a declara com o mínimo que as SQL leem
(``conftest.schema_bcb_vazio``); quem fornece essa tabela na prática é assunto à parte.

Exige ``QUANTILICA_TEST_DATABASE_URL`` (banco descartável); no CI a ausência reprova.
"""

from __future__ import annotations

import pytest
from _catalogo import rel, sql_bcb_do_contrato, usar_schema

SQLS = sql_bcb_do_contrato()


@pytest.mark.parametrize("sql_path", SQLS, ids=rel)
def test_sql_le_series_data_do_quantilica_sql(sql_path, pg_conn, schema_bcb_vazio):
    usar_schema(pg_conn, schema_bcb_vazio)
    pg_conn.execute("EXPLAIN " + sql_path.read_text(encoding="utf-8"))
