"""Resultado de cinco SQL de ``ibge/**`` sobre dado real carregado pelo SIDRA.

As fixtures de ``tests/data/sidra`` (cortes de respostas públicas do IBGE) são
carregadas pelo adaptador do SIDRA e cada SQL roda sobre elas. O esperado vem de um
cálculo independente em Python, direto do JSON cru (sem passar pelo banco), e de três
valores escritos à mão a partir do mesmo JSON: número de linhas, e célula por célula.

Exige ``QUANTILICA_TEST_DATABASE_URL`` (banco descartável); no CI a ausência reprova.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from _catalogo import ROOT, usar_schema

DADOS = Path(__file__).parent / "data" / "sidra"
_NUM = re.compile(r"^-?[0-9]")  # o mesmo teste que as SQL fazem sobre ``D.V``


def _linhas(tabela: str) -> list[dict]:
    """Linhas de dados do arquivo da tabela (sem o cabeçalho), como vieram da API."""
    [arq] = [
        p
        for p in (DADOS / f"t-{tabela}").glob(f"t-{tabela}_*.json")
        if not p.name.endswith(".manifest.json")
    ]
    return json.loads(arq.read_text(encoding="utf-8"))[1:]


def _valor(v: str) -> Decimal | None:
    """Número do IBGE como ``Decimal`` com a escala do texto; símbolo é ``None``."""
    return Decimal(v) if _NUM.match(v) else None


def _soma(parcelas: list[Decimal | None]) -> Decimal | None:
    """``SUM`` do SQL: ignora nulos; sem nenhuma parcela não nula, nulo."""
    nao_nulas = [p for p in parcelas if p is not None]
    return sum(nao_nulas, Decimal(0)) if nao_nulas else None


def _maximo(parcelas: list[Decimal | None]) -> Decimal | None:
    nao_nulas = [p for p in parcelas if p is not None]
    return max(nao_nulas) if nao_nulas else None


def _rodar(conn, schema: str, caminho: str) -> list[dict]:
    usar_schema(conn, schema)
    cur = conn.execute((ROOT / caminho).read_text(encoding="utf-8"))
    nomes = [c.name for c in cur.description]
    return [dict(zip(nomes, linha, strict=True)) for linha in cur.fetchall()]


def _por(linhas: list[dict], *chaves: str) -> dict[tuple, dict]:
    out = {tuple(r[c] for c in chaves): r for r in linhas}
    assert len(out) == len(linhas), "chave repetida no resultado"
    return out


# ---------------------------------------------------------------------------
# ipca.sql (7060): classificação com itens, mensal, nível Brasil
# ---------------------------------------------------------------------------
def test_ipca_7060(pg_conn, schema_sidra_carregado):
    res = _rodar(pg_conn, schema_sidra_carregado, "ibge/precos/snipc/ipca.sql")

    esperado: dict[str, dict] = defaultdict(lambda: {"peso": [], "var": []})
    for r in _linhas("7060"):
        e = esperado[r["D4C"]]
        if r["D2N"] == "IPCA - Peso mensal":
            e["peso"].append(_valor(r["V"]))
        if r["D2N"] == "IPCA - Variação mensal":
            e["var"].append(_valor(r["V"]))

    assert len(res) == len(esperado) == 40
    por_item = _por(res, "item_id")
    for item, e in esperado.items():
        linha = por_item[(item,)]
        assert linha["periodo"] == dt.date(2026, 10, 1)
        assert linha["nivel_territorial"] == "Brasil"
        assert linha["peso"] == _soma(e["peso"])
        assert linha["variacao"] == _soma(e["var"])

    # três valores, escritos a partir do JSON cru
    assert por_item[("7169",)]["variacao"] == Decimal("0.14")  # Índice geral
    assert por_item[("7169",)]["nivel"] == 0
    assert por_item[("7283",)]["peso"] == Decimal("2.8496")  # 1107.Carnes
    assert por_item[("7283",)]["codigo_item"] == "1107"
    assert por_item[("7677",)]["variacao"] == Decimal("-0.85")  # Antidiabético


# ---------------------------------------------------------------------------
# leite/transform.sql (1086): 5 dimensões, 2 classificações, trimestral
# ---------------------------------------------------------------------------
def test_leite_1086(pg_conn, schema_sidra_carregado):
    res = _rodar(
        pg_conn, schema_sidra_carregado, "ibge/agropecuaria/leite/transform.sql"
    )

    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for r in _linhas("1086"):
        grupos[(r["D4C"], r["D5C"])].append(r)
    assert len(res) == len(grupos) == 4

    def pega(linhas, igual=None, casa=None):
        return [
            (_valor(r["V"]), r["MN"])
            for r in linhas
            if (igual and r["D2N"] == igual) or (casa and re.fullmatch(casa, r["D2N"]))
        ]

    por_ref = _por(res, "referencia_temporal_id", "tipo_inspecao_id")
    for (d4, d5), linhas in grupos.items():
        linha = por_ref[(d4, d5)]
        assert linha["periodo"] == dt.date(2026, 1, 1)
        n = pega(linhas, igual="Número de informantes")
        assert linha["numero_informantes"] == _maximo([v for v, _ in n])
        assert linha["numero_informantes_unidade"] == max(u for _, u in n)
        p = pega(linhas, igual="Preço médio")
        assert linha["preco_medio"] == _maximo([v for v, _ in p])
        assert linha["preco_medio_unidade"] == max(u for _, u in p)
        a = pega(linhas, casa=r"Quantidade de leite cru.*adquirido")
        assert linha["qtde_leite_adquirido"] == _maximo([v for v, _ in a])

    # três valores, escritos a partir do JSON cru
    assert por_ref[("115236", "118225")]["numero_informantes"] == Decimal("2035")
    assert por_ref[("115236", "118225")]["preco_medio"] == Decimal("2.24")
    assert por_ref[("115233", "118225")]["preco_medio"] == Decimal("2.10")
    assert por_ref[("115233", "118225")]["preco_medio_unidade"] == "Reais por litro"


# ---------------------------------------------------------------------------
# estimativa_populacao.sql (6579): município, anual
# ---------------------------------------------------------------------------
def test_estimativa_populacao_6579(pg_conn, schema_sidra_carregado):
    res = _rodar(
        pg_conn, schema_sidra_carregado, "ibge/populacao/estimativa_populacao.sql"
    )

    esperado = {r["D1C"]: _valor(r["V"]) for r in _linhas("6579")}
    assert len(res) == len(esperado) == 30
    por_mun = _por(res, "id_municipio")
    for cod, valor in esperado.items():
        assert por_mun[(cod,)]["n_pessoas"] == valor
        assert por_mun[(cod,)]["ano"] == 2026

    # três valores, escritos a partir do JSON cru
    assert por_mun[("1100015",)]["n_pessoas"] == Decimal("22724")
    assert por_mun[("1100015",)]["nome_municipio"] == "Alta Floresta D'Oeste - RO"
    assert por_mun[("1502301",)]["n_pessoas"] == Decimal("60663")
    assert por_mun[("2203404",)]["n_pessoas"] == Decimal("6366")


# ---------------------------------------------------------------------------
# pib_municipal/transform.sql (5938): município, anual, 7 variáveis
# ---------------------------------------------------------------------------
_PIB_VARIAVEIS = {
    "pib": r"Produto Interno Bruto a preços correntes",
    "impostos_liquidos_subsidios": (
        r"Impostos, líquidos de subsídios, sobre produtos a preços correntes"
    ),
    "vab_total": r"Valor adicionado bruto a preços correntes total",
    "vab_agropecuaria": r"Valor adicionado bruto a preços correntes da agropecuária",
    "vab_industria": r"Valor adicionado bruto a preços correntes da indústria",
    "vab_servicos": r"Valor adicionado bruto a preços correntes dos serviços.*",
    "vab_administracao_saude": (
        r"Valor adicionado bruto a preços correntes da administração.*"
    ),
}


def test_pib_municipal_5938(pg_conn, schema_sidra_carregado):
    res = _rodar(
        pg_conn,
        schema_sidra_carregado,
        "ibge/contas_nacionais/pib_municipal/transform.sql",
    )

    por_mun: dict[str, list[dict]] = defaultdict(list)
    for r in _linhas("5938"):
        por_mun[r["D1C"]].append(r)
    assert len(res) == len(por_mun) == 5

    obtido = _por(res, "id_municipio")
    for cod, linhas in por_mun.items():
        linha = obtido[(cod,)]
        assert linha["ano"] == 2021
        for coluna, padrao in _PIB_VARIAVEIS.items():
            achados = [_valor(r["V"]) for r in linhas if re.fullmatch(padrao, r["D2N"])]
            assert len(achados) == 1, (cod, coluna)
            assert linha[coluna] == achados[0], (cod, coluna)

    # três valores, escritos a partir do JSON cru (São Paulo, 3550308)
    sp = obtido[("3550308",)]
    assert sp["pib"] == Decimal("828980746.586")
    assert sp["vab_agropecuaria"] == Decimal("61624.738")
    assert sp["vab_administracao_saude"] == Decimal("48453704.592")


# ---------------------------------------------------------------------------
# pam/lavouras_temporarias.sql (1612): UF, símbolos `-`, `..` e `...`
# ---------------------------------------------------------------------------
_LAV_COLUNAS = {
    "area_colhida": "Área colhida",
    "quantidade_produzida": "Quantidade produzida",
    "rendimento_medio_producao": "Rendimento médio da produção",
    "valor_producao": "Valor da produção",
}


def test_lavouras_temporarias_1612(pg_conn, schema_sidra_carregado):
    res = _rodar(
        pg_conn,
        schema_sidra_carregado,
        "ibge/agropecuaria/pam/lavouras_temporarias.sql",
    )

    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for r in _linhas("1612"):
        grupos[(r["D1C"], r["D4N"])].append(r)
    assert len(res) == len(grupos)

    obtido = _por(res, "id_municipio", "produto")
    for chave, linhas in grupos.items():
        linha = obtido[chave]
        for coluna, variavel in _LAV_COLUNAS.items():
            # SUM(CASE WHEN variavel = X THEN valor ELSE 0 END): outra variável soma 0;
            # símbolo (valor nulo) da variável X não soma nada.
            parcelas = [
                _valor(r["V"]) if r["D2N"] == variavel else Decimal(0) for r in linhas
            ]
            assert linha[coluna] == _soma(parcelas), (chave, coluna)

    # três valores, escritos a partir do JSON cru
    assert obtido[("29", "Batata-doce")]["valor_producao"] == Decimal("44300")  # Bahia
    # `...` (dado não disponível) não vira zero: a soma de um único símbolo é nula
    assert obtido[("41", "Alfafa fenada")]["area_colhida"] is None  # Paraná
    # `-` em "Área plantada" não é a variável pedida: as outras colunas somam 0
    assert obtido[("11", "Alho")]["area_colhida"] == Decimal("0")  # Rondônia
