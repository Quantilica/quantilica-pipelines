"""Contrato das SQL de ``macro/**`` e ``setorial/**`` com o BCB SGS (quantilica-sql).

As 13 SQL que leem ``series_data`` (``series_id``, ``date``, ``date_end``, ``value``,
``ativo``) passam por ``EXPLAIN`` contra as tabelas que o ``quantilica load bcb``
cria (vazias). Dez delas também juntam ``series_metadata`` (``series_id``, ``name``,
``name_abbreviated``, ``unit``, ``frequency``, ``theme_hierarchy``), que o mesmo
adaptador cria e preenche a partir dos metadados do bruto (``quantilica-sql`` 0.4.1):
nenhuma tabela é declarada por este teste. Um segundo teste confere, por varredura,
que cada coluna lida de ``series_metadata`` existe na tabela criada.

Exige ``QUANTILICA_TEST_DATABASE_URL`` (banco descartável); no CI a ausência reprova.
"""

from __future__ import annotations

import pytest
from _catalogo import colunas_de_series_metadata, rel, sql_bcb_do_contrato, usar_schema

SQLS = sql_bcb_do_contrato()


@pytest.mark.parametrize("sql_path", SQLS, ids=rel)
def test_sql_le_series_data_e_series_metadata_do_quantilica_sql(
    sql_path, pg_conn, schema_bcb_vazio
):
    usar_schema(pg_conn, schema_bcb_vazio)
    pg_conn.execute("EXPLAIN " + sql_path.read_text(encoding="utf-8"))


def test_colunas_lidas_de_series_metadata_existem_na_tabela_criada(
    pg_conn, schema_bcb_vazio
):
    esperado = {sql: colunas_de_series_metadata(sql) for sql in SQLS}
    # 10 das 13 juntam series_metadata; credito, monetario e pib_mensal leem só
    # series_data (os ids das séries estão escritos na própria SQL).
    juntam = {rel(sql) for sql, colunas in esperado.items() if colunas}
    assert len(juntam) == 10, sorted(juntam)
    existentes = {
        r[0]: r[1]
        for r in pg_conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'series_metadata'",
            (schema_bcb_vazio,),
        ).fetchall()
    }
    lidas = set().union(*esperado.values())
    assert lidas <= set(existentes), sorted(lidas - set(existentes))
    # os tipos de que as SQL dependem: o id junta com series_data, o tema é array
    assert existentes["series_id"] == "integer"
    assert existentes["theme_hierarchy"] == "ARRAY"
