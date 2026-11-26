"""A varredura que alimenta os testes de contrato continua coerente com o catálogo.

Sem banco. Se uma SQL nova de ``ibge/`` ou de ``macro/``/``setorial/`` não cair em
nenhuma categoria, este teste reprova e obriga a decidir: entra no contrato (lê a
superfície do ``quantilica-sql``) ou fica fora com motivo (``FORA_DO_CONTRATO_SIDRA``).
"""

from __future__ import annotations

from _catalogo import (
    FORA_DO_CONTRATO_SIDRA,
    SUPERFICIE_SIDRA,
    le_analytics,
    le_superficie,
    rel,
    sql_bcb_do_contrato,
    sql_de,
    sql_ibge_do_contrato,
)


def test_ibge_toda_sql_esta_no_contrato_ou_fora_com_motivo():
    sem_categoria = []
    for p in sql_de("ibge"):
        r = rel(p)
        if r in FORA_DO_CONTRATO_SIDRA:
            continue
        if not le_superficie(p, SUPERFICIE_SIDRA):
            sem_categoria.append(r)
    assert not sem_categoria, (
        f"SQL de ibge/ que não leem o SIDRA nem têm motivo: {sem_categoria}"
    )


def test_ibge_as_excluidas_sao_exatamente_as_que_leem_analytics():
    leem = {rel(p) for p in sql_de("ibge") if le_analytics(p)}
    assert leem == set(FORA_DO_CONTRATO_SIDRA)
    assert all(FORA_DO_CONTRATO_SIDRA.values()), "toda exclusão tem motivo"


def test_ibge_as_do_contrato_nao_leem_analytics():
    assert not [rel(p) for p in sql_ibge_do_contrato() if le_analytics(p)]


def test_ibge_o_contrato_tem_51_sql_de_55():
    assert len(sql_de("ibge")) == 55
    assert len(sql_ibge_do_contrato()) == 51


def test_bcb_o_contrato_tem_13_sql():
    achadas = {rel(p) for p in sql_bcb_do_contrato()}
    assert len(achadas) == 13
    # nenhuma SQL de ibge/ lê series_data (e vice-versa: os catálogos não se misturam)
    assert not achadas & {rel(p) for p in sql_de("ibge")}
