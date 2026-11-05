"""Executa os marts DuckDB em memória, com dados sintéticos no lugar do lake.

Cada view ``fonte.alias`` lida por um mart vira uma tabela de texto (como as views
do lake, cujas colunas vêm como VARCHAR) com as colunas de ``SOURCES``. Os testes
conferem que:

* todo mart compila e entrega exatamente as colunas e tipos do contrato
  (``docs/marts_contract.toml``, documentado em ``docs/marts.md``);
* o contrato e o ``transform.toml`` (ou ``transform.toml.disabled``) concordam
  sobre o destino ``schema.tabela``;
* nos marts ativos a chave é única e o resultado é idêntico qualquer que seja a
  ordem das linhas de entrada (chaves e ordenação determinísticas).
"""

from __future__ import annotations

import random
import tomllib
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "docs" / "marts_contract.toml"

# Colunas (todas VARCHAR) de cada view do lake lida pelos marts. Os nomes vêm dos
# conversores dos fetchers (b3, comex, pdet, rfb-cnpj, anac, tesouro-direto).
SOURCES: dict[str, list[str]] = {
    "tesouro_direto.taxas": ["data_base", "tipo_titulo", "taxa_compra_manha"],
    "comex.trade_exp_ncm": [
        "ano",
        "co_mes",
        "co_ncm",
        "sg_uf_ncm",
        "vl_fob",
        "kg_liquido",
    ],
    "comex.trade_imp_ncm": [
        "ano",
        "co_mes",
        "co_ncm",
        "sg_uf_ncm",
        "vl_fob",
        "kg_liquido",
    ],
    "pdet.caged_2020_mov": [
        "ano",
        "mes",
        "id_uf",
        "cnae_2_secao",
        "tipo_movimentacao",
        "saldo_movimento",
        "salario_mensal",
    ],
    "rfb_cnpj.estabelecimentos": ["cnpj_basico", "situacao_cadastral", "uf"],
    "rfb_cnpj.empresas": ["cnpj_basico", "porte_empresa", "capital_social"],
    "anac.vra": ["icao_aerodromo_origem", "ano", "mes", "situacao_voo"],
    # marts ainda desativados (dependência upstream no manifest.toml)
    "b3.cotahist": [
        "data",
        "simbolo",
        "quantidade_titulos_negociados",
        "volume_negociado",
    ],
    "b3.btc_posicoes_abertas": [
        "data_referencia",
        "simbolo",
        "codigo_isin",
        "quantidade",
        "valor",
        "taxa_media",
    ],
    "b3.indices_carteiras": ["codigo_isin"],
    "cvm.ofertas_distribuicao": [
        "data_abertura_processo",
        "cnpj_emissor",
        "codigo_isin",
        "nome_emissor",
        "valor_total_oferta",
    ],
    "cvm.securitizacao_cri": [
        "ano",
        "cnpj_securitizadora",
        "nome_securitizadora",
        "codigo_isin",
        "valor_emissao",
    ],
    "cvm.securitizacao_cra": [
        "ano",
        "cnpj_securitizadora",
        "nome_securitizadora",
        "codigo_isin",
        "valor_emissao",
    ],
    "bcb_microdados.scr_carteira_cnae_rating": [
        "data_base",
        "cnae_divisao",
        "modalidade",
        "valor_carteira",
    ],
    "bcb_microdados.fluxo_cambial_diario": ["ano", "mes", "natureza", "valor_usd"],
    "antaq.cargas": [
        "ano",
        "mes",
        "codigo_instalacao_portuaria",
        "sh4",
        "peso_liquido_kg",
    ],
}

# Linhas sintéticas dos marts ativos (dict coluna -> valor); o resto fica NULL.
ROWS: dict[str, list[dict[str, str]]] = {
    "tesouro_direto.taxas": [
        {
            "data_base": "02/01/2024",
            "tipo_titulo": "Tesouro Selic 2027",
            "taxa_compra_manha": "0,05",
        },
        {
            "data_base": "15/01/2024",
            "tipo_titulo": "Tesouro Selic 2029",
            "taxa_compra_manha": "0,07",
        },
        {
            "data_base": "2024-01-20",
            "tipo_titulo": "Tesouro IPCA+ 2035",
            "taxa_compra_manha": "5,90",
        },
        {
            "data_base": "2024-02-05",
            "tipo_titulo": "Tesouro Prefixado 2027",
            "taxa_compra_manha": "10,80",
        },
        {
            "data_base": "05/02/2024",
            "tipo_titulo": "Tesouro IPCA+ 2035",
            "taxa_compra_manha": "6,10",
        },
    ],
    "comex.trade_exp_ncm": [
        {
            "ano": "2024",
            "co_mes": "1",
            "sg_uf_ncm": "SP",
            "vl_fob": "100",
            "kg_liquido": "10",
        },
        {
            "ano": "2024",
            "co_mes": "1",
            "sg_uf_ncm": "SP",
            "vl_fob": "50",
            "kg_liquido": "5",
        },
        {
            "ano": "2024",
            "co_mes": "1",
            "sg_uf_ncm": "RJ",
            "vl_fob": "70",
            "kg_liquido": "7",
        },
        {
            "ano": "2024",
            "co_mes": "2",
            "sg_uf_ncm": "SP",
            "vl_fob": "10",
            "kg_liquido": "1",
        },
    ],
    "comex.trade_imp_ncm": [
        {
            "ano": "2024",
            "co_mes": "1",
            "sg_uf_ncm": "SP",
            "vl_fob": "30",
            "kg_liquido": "3",
        },
        {
            "ano": "2024",
            "co_mes": "1",
            "sg_uf_ncm": "RJ",
            "vl_fob": "20",
            "kg_liquido": "2",
        },
        {
            "ano": "2024",
            "co_mes": "2",
            "sg_uf_ncm": "SP",
            "vl_fob": "40",
            "kg_liquido": "4",
        },
    ],
    "pdet.caged_2020_mov": [
        {
            "ano": "2024",
            "mes": "01",
            "id_uf": "35",
            "cnae_2_secao": "C",
            "tipo_movimentacao": "10",
            "saldo_movimento": "1",
            "salario_mensal": "1.500,00",
        },
        {
            "ano": "2024",
            "mes": "01",
            "id_uf": "35",
            "cnae_2_secao": "C",
            "tipo_movimentacao": "31",
            "saldo_movimento": "-1",
            "salario_mensal": "2000",
        },
        {
            "ano": "2024",
            "mes": "01",
            "id_uf": "35",
            "cnae_2_secao": "G",
            "tipo_movimentacao": "10",
            "saldo_movimento": "1",
            "salario_mensal": "1800",
        },
        {
            "ano": "2024",
            "mes": "01",
            "id_uf": "33",
            "cnae_2_secao": "C",
            "tipo_movimentacao": "20",
            "saldo_movimento": "1",
            "salario_mensal": "1700",
        },
        {
            "ano": "2024",
            "mes": "02",
            "id_uf": "35",
            "cnae_2_secao": "C",
            "tipo_movimentacao": "40",
            "saldo_movimento": "-1",
            "salario_mensal": "2100",
        },
    ],
    "rfb_cnpj.estabelecimentos": [
        {"cnpj_basico": "00000001", "situacao_cadastral": "02", "uf": "SP"},
        {"cnpj_basico": "00000002", "situacao_cadastral": "08", "uf": "SP"},
        {"cnpj_basico": "00000003", "situacao_cadastral": "02", "uf": "RJ"},
        {"cnpj_basico": "00000003", "situacao_cadastral": "02", "uf": "RJ"},
    ],
    "rfb_cnpj.empresas": [
        {"cnpj_basico": "00000001", "porte_empresa": "01", "capital_social": "1000.00"},
        {"cnpj_basico": "00000002", "porte_empresa": "01", "capital_social": "2000.50"},
        {"cnpj_basico": "00000003", "porte_empresa": "03", "capital_social": "500.00"},
    ],
    "anac.vra": [
        {
            "icao_aerodromo_origem": "SBGR",
            "ano": "2024",
            "mes": "1",
            "situacao_voo": "REALIZADO",
        },
        {
            "icao_aerodromo_origem": "SBGR",
            "ano": "2024",
            "mes": "1",
            "situacao_voo": "CANCELADO",
        },
        {
            "icao_aerodromo_origem": "SBGR",
            "ano": "2024",
            "mes": "2",
            "situacao_voo": "REALIZADO",
        },
        {
            "icao_aerodromo_origem": "SBSP",
            "ano": "2024",
            "mes": "1",
            "situacao_voo": "REALIZADO",
        },
        {
            "icao_aerodromo_origem": None,
            "ano": "2024",
            "mes": "1",
            "situacao_voo": "REALIZADO",
        },
    ],
}


def load_contract() -> list[dict]:
    return tomllib.loads(CONTRACT.read_text(encoding="utf-8"))["mart"]


def mart_id(mart: dict) -> str:
    return mart["table"]


def make_conn(rows: dict[str, list[dict]] | None = None, shuffle: int | None = None):
    """Conexão em memória com as views de ``SOURCES`` (vazias ou com ``rows``)."""
    conn = duckdb.connect()
    conn.execute("SET TimeZone = 'UTC'")
    for view, columns in SOURCES.items():
        schema, name = view.split(".")
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        cols = ", ".join(f'"{c}" VARCHAR' for c in columns)
        conn.execute(f'CREATE TABLE "{schema}"."{name}" ({cols})')
        data = list((rows or {}).get(view, []))
        if shuffle is not None:
            random.Random(shuffle).shuffle(data)
        for row in data:
            names = ", ".join(f'"{c}"' for c in columns)
            marks = ", ".join("?" for _ in columns)
            conn.execute(
                f'INSERT INTO "{schema}"."{name}" ({names}) VALUES ({marks})',
                [row.get(c) for c in columns],
            )
    return conn


def mart_dir(mart: dict) -> Path:
    return ROOT / mart["path"]


def run_prelude(conn, mart: dict) -> None:
    prelude = mart.get("prelude")
    if prelude:
        conn.execute((mart_dir(mart) / prelude).read_text(encoding="utf-8"))


def mart_sql(mart: dict) -> str:
    text = (mart_dir(mart) / mart["sql"]).read_text(encoding="utf-8")
    return text.strip().rstrip(";")


def described(conn, mart: dict) -> list[tuple[str, str]]:
    run_prelude(conn, mart)
    return [(r[0], r[1]) for r in conn.execute(f"DESCRIBE {mart_sql(mart)}").fetchall()]


CONTRACT_MARTS = load_contract()
ACTIVE = [m for m in CONTRACT_MARTS if m["status"] == "active"]
IDS = [mart_id(m) for m in CONTRACT_MARTS]
ACTIVE_IDS = [mart_id(m) for m in ACTIVE]


@pytest.mark.parametrize("mart", CONTRACT_MARTS, ids=IDS)
def test_mart_compiles_and_matches_contract_schema(mart):
    got = described(make_conn(), mart)
    want = [(c["name"], c["type"]) for c in mart["columns"]]
    assert got == want


@pytest.mark.parametrize("mart", CONTRACT_MARTS, ids=IDS)
def test_contract_target_matches_transform_toml(mart):
    pipeline = mart_dir(mart)
    toml = pipeline / "transform.toml"
    if mart["status"] == "active":
        assert toml.is_file(), f"{mart['table']} ativo sem transform.toml"
    else:
        toml = pipeline / "transform.toml.disabled"
        assert toml.is_file(), f"{mart['table']} desativado sem transform.toml.disabled"
    tables = tomllib.loads(toml.read_text(encoding="utf-8"))["table"]
    targets = {f"{t['schema']}.{t['name']}" for t in tables if t["sql"] == mart["sql"]}
    assert targets == {mart["table"]}


def test_contract_lists_every_active_manifest_table():
    manifest = tomllib.loads((ROOT / "manifest.toml").read_text(encoding="utf-8"))
    declared = set()
    for spec in manifest["pipelines"].values():
        toml = ROOT / spec["path"] / "transform.toml"
        if spec["engine"] != "duckdb" or spec["path"].startswith("tesouro_direto"):
            continue
        for t in tomllib.loads(toml.read_text(encoding="utf-8"))["table"]:
            declared.add(f"{t['schema']}.{t['name']}")
    assert declared == set(ACTIVE_IDS)


@pytest.mark.parametrize("mart", ACTIVE, ids=ACTIVE_IDS)
def test_active_mart_produces_rows_with_unique_key(mart):
    conn = make_conn(ROWS)
    run_prelude(conn, mart)
    result = conn.execute(mart_sql(mart))
    names = [d[0] for d in result.description]
    rows = result.fetchall()
    assert rows, "dados sintéticos não geraram linhas"
    index = [names.index(k) for k in mart["key"]]
    keys = [tuple(row[i] for i in index) for row in rows]
    assert len(keys) == len(set(keys)), f"chave {mart['key']} repetida"


@pytest.mark.parametrize("mart", ACTIVE, ids=ACTIVE_IDS)
def test_active_mart_is_deterministic_for_any_input_order(mart):
    outputs = []
    for seed in (None, 1, 2, 3):
        conn = make_conn(ROWS, shuffle=seed)
        run_prelude(conn, mart)
        outputs.append(conn.execute(mart_sql(mart)).fetchall())
    assert all(out == outputs[0] for out in outputs[1:])
