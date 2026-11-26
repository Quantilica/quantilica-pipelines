"""Resultado de duas SQL de ``macro/**`` sobre dado real do BCB SGS carregado do bruto.

``tests/data/bcb`` guarda o que o ``bcb-sgs-fetcher`` gravou para cinco séries (433,
189, 188, 11 e 432): observações em ``data/`` e metadados em
``bcb-sgs_2026-11/metadata/``. O adaptador ``bcb`` do ``quantilica-sql`` carrega as
duas coisas (``load bcb-sgs -s <raiz> --all``), inclusive ``series_metadata``, e as SQL
rodam sobre o resultado, sem nenhuma tabela declarada pelo teste. O esperado vem de um
cálculo independente em Python, direto do JSON cru.

Exige ``QUANTILICA_TEST_DATABASE_URL`` (banco descartável); no CI a ausência reprova.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from _catalogo import ROOT, usar_schema

DADOS = Path(__file__).parent / "data" / "bcb"
METADADOS = DADOS / "bcb-sgs_2026-11" / "metadata"


def _pontos(serie: int) -> list[dict]:
    [arq] = (DADOS / "data").glob(f"series_{serie}@*.json")
    return json.loads(arq.read_text(encoding="utf-8"))


def _basic(serie: int) -> dict:
    return json.loads((METADADOS / f"{serie:06d}.json").read_text("utf-8"))["basic"]


def _rodar(conn, schema: str, caminho: str) -> list[dict]:
    usar_schema(conn, schema)
    cur = conn.execute((ROOT / caminho).read_text(encoding="utf-8"))
    nomes = [c.name for c in cur.description]
    return [dict(zip(nomes, linha, strict=True)) for linha in cur.fetchall()]


def test_load_criou_e_preencheu_series_metadata(pg_conn, schema_bcb_carregado):
    linhas = pg_conn.execute(
        f'SELECT series_id, name, theme_hierarchy FROM "{schema_bcb_carregado}"'
        ".series_metadata ORDER BY series_id"
    ).fetchall()
    assert [r[0] for r in linhas] == [11, 188, 189, 432, 433]
    assert [(r[1], r[2]) for r in linhas] == [
        (_basic(s)["name"], _basic(s)["theme_hierarchy"])
        for s in (11, 188, 189, 432, 433)
    ]
    assert pg_conn.execute(
        f'SELECT count(*) FROM "{schema_bcb_carregado}".series_data'
    ).fetchone() == (100,)


def test_bcb_precos(pg_conn, schema_bcb_carregado):
    """433 (IPCA), 188 (INPC) e 189 (IGP-M) têm o tema 'Atividade econômica e preços >
    Preços'; a Selic (11 e 432) não entra."""
    res = _rodar(pg_conn, schema_bcb_carregado, "macro/bcb_precos/precos.sql")

    esperado = {}
    for indice, serie in (("IPCA", 433), ("INPC", 188), ("IGP-M", 189)):
        b = _basic(serie)
        for p in _pontos(serie):
            esperado[(dt.date.fromisoformat(p["date"]), indice)] = (
                b["name"],
                b["unit"],
                b["frequency"],
                float(p["value"]),
            )
    obtido = {
        (r["date"], r["indice"]): (
            r["nome_serie"],
            r["unidade"],
            r["frequencia"],
            r["valor"],
        )
        for r in res
    }
    assert len(res) == len(obtido) == len(esperado) == 60
    assert obtido == esperado

    # três valores escritos à mão a partir do JSON (a última observação de cada índice)
    ultimo = {i: max(d for d, ind in esperado if ind == i) for i in ("IPCA", "INPC")}
    assert (ultimo["IPCA"], obtido[(ultimo["IPCA"], "IPCA")][1:3]) == (
        dt.date(2026, 10, 1),
        ("Var. % mensal", "Mensal"),
    )
    assert obtido[(dt.date(2026, 10, 1), "IPCA")][3] == 0.14
    assert obtido[(dt.date(2026, 10, 1), "INPC")][3] == 0.22
    assert obtido[(dt.date(2026, 10, 1), "IGP-M")][3] == 1.47


def test_juros(pg_conn, schema_bcb_carregado):
    """Só a Selic diária (11) tem o tema 'Taxas de juros'; a meta (432) é de outro
    tema ('Política monetária') e não entra."""
    res = _rodar(pg_conn, schema_bcb_carregado, "macro/juros/juros.sql")
    b = _basic(11)
    pontos = _pontos(11)

    assert len(res) == len(pontos) == 20
    assert {
        (r["taxa"], r["nome_serie"], r["unidade"], r["frequencia"]) for r in res
    } == {("SELIC-OVER", b["name"], b["unit"], b["frequency"])}
    assert [(r["date"], r["valor"]) for r in res] == [
        (dt.date.fromisoformat(p["date"]), float(p["value"])) for p in pontos
    ]
    assert (b["unit"], b["frequency"], res[-1]["valor"]) == (
        "% a.d.",
        "Diária",
        0.050788,
    )
