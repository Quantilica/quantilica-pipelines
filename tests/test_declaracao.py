# ruff: noqa: E501
"""Testes do validador da declaração de um conjunto tabular (ferramentas/quantilica_publicacao/declaracao.py).

Uma declaração válida mínima, uma completa e uma lista de declarações quebradas (uma por
regra) que precisam falhar com a mensagem certa.

    uv run --with pytest pytest -q tests/test_declaracao.py
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "publicacao_declaracao", RAIZ / "ferramentas" / "quantilica_publicacao" / "declaracao.py"
)
decl = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["publicacao_declaracao"] = decl
_spec.loader.exec_module(decl)

SQL_BASE = "SELECT cnpj, sum(v) AS v FROM read_parquet($ent) GROUP BY 1"
SQL_UF = (
    "SELECT uf AS entidade, CAST(mes AS DATE) AS periodo, CAST(sum(v) AS BIGINT) AS m_total "
    "FROM base GROUP BY 1, 2"
)
SQLS = {"base.sql": SQL_BASE, "uf.sql": SQL_UF}


def minima() -> dict:
    """A menor declaração válida: território, uma visão, uma medida."""
    return {
        "schema_versao": 1,
        "id": "teste/exemplo",
        "titulo": "Exemplo de teste",
        "descricao": "Conjunto de teste.",
        "estado": "rascunho",
        "preparo": "base.sql",
        "fonte": {
            "orgao": "Órgão de teste",
            "licenca": "CC BY 4.0",
            "atribuicao": "Fonte: órgão de teste.",
            "redistribuicao": "livre",
        },
        "entidade": {"tipo": "territorio", "rotulo": "Território", "qualifier": "geo"},
        "tempo": {
            "tipo": "mes",
            "frequencia": "monthly",
            "alinhamento_painel": "inicio",
            "padrao": "ultimo",
        },
        "entrada": [{"nome": "ent", "glob": "teste/exemplo/ano=*/*.parquet"}],
        "visao": [
            {
                "nivel": "UF",
                "chave": "sigla",
                "consulta": "uf.sql",
                "cabecalhos": ["UF", "Nome"],
            }
        ],
        "medida": [
            {
                "id": "total",
                "rotulo": "Total",
                "unidade": "un",
                "tipo": "bigint",
                "aditiva": True,
            }
        ],
    }


def validar(dados: dict, sqls: dict | None = None):
    return decl.validar(dados, SQLS if sqls is None else sqls)


# --- declarações válidas ----------------------------------------------------------


def test_minima_valida_e_defaults():
    d = validar(minima())
    assert d.id == "teste/exemplo" and d.fonte_id == "teste" and d.slug == "exemplo"
    assert d.tabela("UF") == "c_teste_exemplo_uf"
    assert d.limites.max_linhas_tabela == 1_000_000
    assert d.guardas.queda_maxima_linhas == pytest.approx(0.10)
    assert d.guardas.periodos_nao_somem is True
    assert d.espelho()["titulo_curto"] == "Exemplo de teste"


def test_sem_sqls_valida_so_a_declaracao():
    assert decl.validar(minima()).id == "teste/exemplo"


def test_completa_valida_e_espelho_nao_leva_lake_nem_sql():
    d = minima()
    d["tempo"] = {**d["tempo"], "padrao": "ultimo_com_cobertura", "fracao": 0.8}
    d["dimensao"] = [
        {"id": "tipo", "rotulo": "Tipo", "valores": ["a", "b"], "padrao": "a"}
    ]
    d["atributo"] = [{"id": "prelim", "rotulo": "Preliminar", "tipo": "boolean"}]
    d["preliminar"] = {"ultimos_periodos": 2, "nota": "Revisado."}
    d["guardas"] = {
        "periodos_continuos": True,
        "periodo_inicial": "2020-01",
        "cobertura_minima_entidades": 27,
        "revisao_maxima_total": 0.03,
    }
    d["conferencia"] = [
        {
            "nivel": "UF",
            "medida": "total",
            "periodo": "2025-06",
            "valor": 10,
            "tolerancia_relativa": 0.0,
            "referencia": "Fonte oficial",
        }
    ]
    d["estado"] = "publicado"
    obj = validar(d)
    assert obj.guardas.revisao_medidas == ("total",)  # padrão: as medidas aditivas
    espelho = obj.espelho()
    assert espelho["visoes"][0]["tabela"] == "c_teste_exemplo_uf"
    assert "entrada" not in espelho and "entradas" not in espelho
    assert "consulta" not in espelho["visoes"][0]
    assert espelho["dimensoes"][0]["valores"] == ["a", "b"]


def test_espelho_e_serializavel_em_json():
    import json

    json.dumps(validar(minima()).espelho())


def test_parecer_com_data_toml():
    import datetime as dt

    d = minima()
    d["fonte"]["licenca"] = "Creative Commons BY-ND 4.0"
    d["fonte"]["parecer_licenca"] = {"data": dt.date(2026, 11, 25), "por": "dono"}
    assert validar(d).fonte.parecer_licenca.data == "2026-11-25"


# --- declarações quebradas: uma por regra -----------------------------------------


def _set(caminho: str, valor):
    def aplicar(d: dict) -> None:
        *pais, ultimo = caminho.split(".")
        alvo = d
        for p in pais:
            alvo = alvo[int(p)] if p.isdigit() else alvo[p]
        if valor is _APAGAR:
            del alvo[int(ultimo) if ultimo.isdigit() else ultimo]
        else:
            alvo[int(ultimo) if ultimo.isdigit() else ultimo] = valor

    return aplicar


_APAGAR = object()

QUEBRADAS: list[tuple[str, object, str]] = [
    ("schema_versao futura", _set("schema_versao", 2), "versão 2 não suportada"),
    (
        "schema_versao ausente",
        _set("schema_versao", _APAGAR),
        "schema_versao: campo obrigatório",
    ),
    (
        "campo desconhecido com sugestão",
        _set("titulos", "x"),
        "você quis dizer 'titulo'",
    ),
    ("estado inválido", _set("estado", "ativo"), "valor 'ativo' inválido"),
    ("id sem barra", _set("id", "pdet"), "deve ser <fonte>/<conjunto>"),
    ("id com maiúscula", _set("id", "Pdet/caged"), "deve ser <fonte>/<conjunto>"),
    ("tabela longa demais", _set("id", "a" * 40 + "/" + "b" * 40), "tem 86 caracteres"),
    (
        "redistribuicao inválida",
        _set("fonte.redistribuicao", "talvez"),
        "valor 'talvez' inválido",
    ),
    (
        "restrita publicada",
        lambda d: (
            d["fonte"].update(redistribuicao="restrita"),
            d.update(estado="publicado"),
            d.update(
                conferencia=[
                    {
                        "nivel": "UF",
                        "medida": "total",
                        "periodo": "2025-06",
                        "valor": 1,
                        "tolerancia_relativa": 0.1,
                        "referencia": "r",
                    }
                ]
            ),
        ),
        "'restrita' não pode estar no estado 'publicado'",
    ),
    (
        "licença sem derivação exige parecer",
        _set(
            "fonte.licenca",
            "Creative Commons Atribuição-SemDerivações 4.0 (CC BY-ND 4.0)",
        ),
        "restringe obra derivada",
    ),
    ("url sem esquema", _set("fonte.url", "exemplo.com"), "fora do padrão"),
    (
        "tipo de entidade inválido",
        _set("entidade.tipo", "pessoa"),
        "valor 'pessoa' inválido",
    ),
    (
        "território com qualifier errado",
        _set("entidade.qualifier", "uf"),
        "usa o qualifier 'geo'",
    ),
    (
        "identificador com qualifier reservado",
        lambda d: d["entidade"].update(tipo="identificador", qualifier="geo"),
        "'geo' é nome reservado",
    ),
    (
        "nível territorial desconhecido",
        _set("visao.0.nivel", "BAIRRO"),
        "nível territorial 'BAIRRO'",
    ),
    (
        "chave do nível errada",
        _set("visao.0.chave", "ibge6"),
        "exige chave dentre: sigla",
    ),
    (
        "cabecalhos com um só texto",
        _set("visao.0.cabecalhos", ["UF"]),
        "esperava dois textos",
    ),
    (
        "nível repetido",
        lambda d: d["visao"].append(copy.deepcopy(d["visao"][0])),
        "repetido",
    ),
    (
        "arquivo sql com caminho",
        _set("visao.0.consulta", "../uf.sql"),
        "fora do padrão",
    ),
    (
        "frequência incoerente com o tipo",
        _set("tempo.frequencia", "daily"),
        "a frequência é 'monthly'",
    ),
    (
        "cobertura sem fracao",
        _set("tempo.padrao", "ultimo_com_cobertura"),
        "exige fracao",
    ),
    ("fracao sem cobertura", _set("tempo.fracao", 0.8), "só vale com o padrão"),
    ("medida com id inválido", _set("medida.0.id", "Total-Geral"), "fora do padrão"),
    ("medida com tipo inválido", _set("medida.0.tipo", "int"), "valor 'int' inválido"),
    (
        "medida repetida",
        lambda d: d["medida"].append(copy.deepcopy(d["medida"][0])),
        "medida 'total' repetida",
    ),
    ("sem medida", _set("medida", []), "pelo menos um bloco [[medida]]"),
    (
        "dimensão com nome de qualifier reservado",
        lambda d: d.update(dimensao=[{"id": "tempo", "rotulo": "Tempo"}]),
        "já é um qualifier",
    ),
    (
        "dimensão com padrão fora dos valores",
        lambda d: d.update(
            dimensao=[{"id": "tipo", "rotulo": "T", "valores": ["a"], "padrao": "z"}]
        ),
        "não está em valores",
    ),
    (
        "atributo de tipo inválido",
        lambda d: d.update(atributo=[{"id": "x", "rotulo": "X", "tipo": "json"}]),
        "valor 'json' inválido",
    ),
    (
        "limite acima do teto",
        _set("limites", {"max_linhas_tabela": 6_000_000}),
        "fora do intervalo 1 a 5000000",
    ),
    (
        "limite não inteiro",
        _set("limites", {"max_linhas_cs": "muitos"}),
        "esperava inteiro",
    ),
    (
        "guarda fora do intervalo",
        _set("guardas", {"queda_maxima_linhas": 1.5}),
        "fora do intervalo",
    ),
    (
        "periodo_inicial sem continuidade",
        _set("guardas", {"periodo_inicial": "2020-01"}),
        "só vale com periodos_continuos",
    ),
    (
        "periodo_inicial no formato errado",
        _set("guardas", {"periodos_continuos": True, "periodo_inicial": "2020"}),
        "não é um período mes (AAAA-MM)",
    ),
    (
        "revisão sobre medida não aditiva",
        lambda d: (
            d["medida"][0].update(aditiva=False),
            d.update(guardas={"revisao_maxima_total": 0.03}),
        ),
        "exige pelo menos uma medida com aditiva = true",
    ),
    (
        "revisao_medidas desconhecida",
        _set("guardas", {"revisao_maxima_total": 0.03, "revisao_medidas": ["outra"]}),
        "'outra' não é uma medida aditiva",
    ),
    (
        "conferência com visão inexistente",
        lambda d: d.update(
            conferencia=[
                {
                    "nivel": "MUN",
                    "medida": "total",
                    "periodo": "2025-06",
                    "valor": 1,
                    "tolerancia_relativa": 0.1,
                    "referencia": "r",
                }
            ]
        ),
        "visão 'MUN' não existe",
    ),
    (
        "conferência com período de outro tipo",
        lambda d: d.update(
            conferencia=[
                {
                    "nivel": "UF",
                    "medida": "total",
                    "periodo": "2025",
                    "valor": 1,
                    "tolerancia_relativa": 0.1,
                    "referencia": "r",
                }
            ]
        ),
        "não é um período mes",
    ),
    (
        "conferência sem referência",
        lambda d: d.update(
            conferencia=[
                {
                    "nivel": "UF",
                    "medida": "total",
                    "periodo": "2025-06",
                    "valor": 1,
                    "tolerancia_relativa": 0.1,
                }
            ]
        ),
        "referencia: campo obrigatório",
    ),
    (
        "publicado sem conferência",
        _set("estado", "publicado"),
        "exige pelo menos uma [[conferencia]]",
    ),
    (
        "entrada com caminho absoluto",
        _set("entrada.0.glob", "/lake/teste/x.parquet"),
        "relativo à raiz do lake",
    ),
    (
        "entrada com ..",
        _set("entrada.0.glob", "teste/../outra/x.parquet"),
        "relativo à raiz do lake",
    ),
    (
        "entrada de outra fonte",
        _set("entrada.0.glob", "outra/x/*.parquet"),
        "deve começar por teste/",
    ),
    (
        "entrada que não é parquet",
        _set("entrada.0.glob", "teste/x/*.csv"),
        "terminar em .parquet",
    ),
    (
        "entrada com caractere perigoso",
        _set("entrada.0.glob", "teste/x';--.parquet"),
        "caracteres fora de",
    ),
    ("sem entrada", _set("entrada", []), "pelo menos um bloco [[entrada]]"),
    (
        "preliminar fora do intervalo",
        _set("preliminar", {"ultimos_periodos": 0, "nota": "n"}),
        "fora do intervalo 1 a 24",
    ),
    ("bloco com tipo errado", _set("fonte", "texto"), "esperava uma tabela"),
    (
        "queda de valores fora do intervalo",
        _set("guardas", {"queda_maxima_valores": 1.5}),
        "fora do intervalo",
    ),
    (
        "conferência fixa dimensão que não existe",
        lambda d: d.update(
            conferencia=[
                {
                    "nivel": "UF",
                    "medida": "total",
                    "periodo": "2025-06",
                    "valor": 1,
                    "tolerancia_relativa": 0.1,
                    "referencia": "r",
                    "dimensoes": {"tipo": "a"},
                }
            ]
        ),
        "dimensão 'tipo' não existe",
    ),
    (
        "conferência fixa valor fora do enum da dimensão",
        lambda d: d.update(
            dimensao=[{"id": "tipo", "rotulo": "Tipo", "valores": ["a", "b"]}],
            conferencia=[
                {
                    "nivel": "UF",
                    "medida": "total",
                    "periodo": "2025-06",
                    "valor": 1,
                    "tolerancia_relativa": 0.1,
                    "referencia": "r",
                    "dimensoes": {"tipo": "z"},
                }
            ],
        ),
        "'z' não está em valores",
    ),
]


def test_conferencia_com_dimensao_fixa_entra_no_espelho_so_quando_existe():
    d = minima()
    d["dimensao"] = [{"id": "tipo", "rotulo": "Tipo", "valores": ["a", "b"]}]
    base_conf = {
        "nivel": "UF",
        "medida": "total",
        "periodo": "2025-06",
        "valor": 1,
        "tolerancia_relativa": 0.1,
        "referencia": "r",
    }
    d["conferencia"] = [base_conf, {**base_conf, "dimensoes": {"tipo": "a"}}]
    obj = validar(d)
    assert obj.conferencias[1].dimensoes == (("tipo", "a"),)
    confs = obj.espelho()["conferencias"]
    assert "dimensoes" not in confs[0] and confs[1]["dimensoes"] == {"tipo": "a"}


def test_queda_de_valores_padrao_e_fora_do_espelho():
    d = validar(minima())
    assert d.guardas.queda_maxima_valores == pytest.approx(0.10)
    assert (
        "queda_maxima_valores" not in d.espelho()["guardas"]
    )  # contrato com o portal intacto
    dados = minima()
    dados["guardas"] = {"queda_maxima_valores": 0.25}
    assert validar(dados).guardas.queda_maxima_valores == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("nome", "mutacao", "esperado"), QUEBRADAS, ids=[q[0] for q in QUEBRADAS]
)
def test_declaracao_quebrada_falha_com_mensagem_clara(nome, mutacao, esperado):
    d = minima()
    mutacao(d)
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(d)
    assert esperado in str(exc.value), str(exc.value)


def test_pelo_menos_doze_regras_quebradas():
    assert len(QUEBRADAS) >= 12


def test_todos_os_erros_de_uma_vez():
    d = minima()
    d["estado"] = "ativo"
    d["fonte"]["redistribuicao"] = "talvez"
    d["medida"][0]["tipo"] = "int"
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(d)
    assert len(exc.value.erros) == 3


# --- consultas ---------------------------------------------------------------------

SQLS_RUINS = [
    ("arquivo ausente", {"base.sql": SQL_BASE}, "arquivo uf.sql não existe"),
    (
        "parâmetro não declarado",
        {**SQLS, "base.sql": "SELECT * FROM read_parquet($outra)"},
        "parâmetro $outra não declarado",
    ),
    (
        "entrada nunca usada",
        {**SQLS, "base.sql": "SELECT 1 AS cnpj"},
        "a entrada 'ent' não é usada",
    ),
    (
        "duas instruções",
        {**SQLS, "uf.sql": "SELECT 1; SELECT 2"},
        "mais de uma instrução",
    ),
    (
        "não começa por select",
        {**SQLS, "uf.sql": "CREATE TABLE x AS SELECT 1"},
        "deve começar com SELECT ou WITH",
    ),
    (
        "escrita",
        {**SQLS, "uf.sql": "WITH a AS (SELECT 1) INSERT INTO t SELECT * FROM a"},
        "'INSERT' não é permitida",
    ),
    (
        "caminho literal",
        {**SQLS, "uf.sql": "SELECT * FROM read_parquet('/etc/passwd')"},
        "só `read_parquet($entrada",
    ),
    (
        "from com arquivo literal",
        {**SQLS, "uf.sql": "SELECT * FROM 'dados.parquet'"},
        "caminho de arquivo literal",
    ),
    (
        "função de leitura de texto",
        {**SQLS, "uf.sql": "SELECT * FROM read_csv($ent)"},
        "read_csv() fora do padrão",
    ),
    ("consulta vazia", {**SQLS, "uf.sql": "-- só comentário\n"}, "consulta vazia"),
    (
        "query() executa texto (lê o ambiente do processo)",
        {
            **SQLS,
            "uf.sql": "SELECT * FROM query('SELECT content FROM read_text(''/proc/self/environ'')')",
        },
        "função query() fora do padrão",
    ),
    (
        "função de leitura escondida dentro de literal",
        {
            **SQLS,
            "uf.sql": "SELECT * FROM query('SELECT content FROM read_text(''/proc/self/environ'')')",
        },
        "função read_text() dentro de um literal",
    ),
    (
        "query_table() com literal",
        {**SQLS, "uf.sql": "SELECT * FROM query_table('/etc/x.csv')"},
        "função query_table() fora do padrão",
    ),
    (
        "from com literal entre parênteses",
        {**SQLS, "uf.sql": "SELECT * FROM ('/caminho/x.csv')"},
        "caminho de arquivo literal",
    ),
    (
        "join com literal entre parênteses",
        {**SQLS, "uf.sql": "SELECT * FROM base JOIN (('https://x.y/a.csv')) USING (a)"},
        "caminho de arquivo literal",
    ),
    (
        "from com identificador entre aspas e caminho",
        {**SQLS, "uf.sql": 'SELECT * FROM ("/etc/x.csv")'},
        "caminho de arquivo literal",
    ),
]


@pytest.mark.parametrize(
    ("nome", "sqls", "esperado"), SQLS_RUINS, ids=[s[0] for s in SQLS_RUINS]
)
def test_consulta_quebrada(nome, sqls, esperado):
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(minima(), sqls)
    assert esperado in str(exc.value), str(exc.value)


def test_comentario_e_literal_nao_disparam_o_filtro():
    sql = "-- insert, drop e $fantasma em comentário\nSELECT 'insert $x' AS v, uf AS entidade FROM base"
    d = validar(minima(), {**SQLS, "uf.sql": sql + " WHERE 1 = 1"})
    assert d.id == "teste/exemplo"


# --- contrato de colunas ---------------------------------------------------------


def test_colunas_esperadas_territorio_e_identificador():
    d = validar(minima())
    nomes = [c.nome for c in decl.colunas_esperadas(d, d.visoes[0])]
    assert nomes == ["entidade", "entidade_rotulo", "periodo", "m_total"]
    obrig = {c.nome: c.obrigatoria for c in decl.colunas_esperadas(d, d.visoes[0])}
    assert obrig["entidade_rotulo"] is False
    dados = minima()
    dados["entidade"] = {"tipo": "identificador", "rotulo": "Cia", "qualifier": "cia",
                         "chaves_alternativas": ["cd"]}  # fmt: skip
    dados["visao"][0].pop("chave")
    dados["visao"][0]["nivel"] = "CIA"
    ident = validar(dados)
    cols = decl.colunas_esperadas(ident, ident.visoes[0])
    assert [c.nome for c in cols][:3] == ["entidade", "entidade_rotulo", "entidade_cd"]
    assert cols[1].obrigatoria is True


def test_conferir_colunas_aceita_o_contrato_e_aponta_desvios():
    d = validar(minima())
    v = d.visoes[0]
    certo = [("entidade", "VARCHAR"), ("periodo", "DATE"), ("m_total", "HUGEINT")]
    assert decl.conferir_colunas(d, v, certo) == []
    assert decl.conferir_colunas(d, v, certo[:2])  # falta m_total
    extra = [*certo, ("lixo", "VARCHAR")]
    assert "não faz parte do contrato" in decl.conferir_colunas(d, v, extra)[0]
    errado = [("entidade", "VARCHAR"), ("periodo", "VARCHAR"), ("m_total", "DOUBLE")]
    msgs = " ".join(decl.conferir_colunas(d, v, errado))
    assert "'periodo' é VARCHAR" in msgs and "'m_total' é DOUBLE" in msgs
    repetido = [*certo, ("periodo", "DATE")]
    assert "repetida" in " ".join(decl.conferir_colunas(d, v, repetido))


def test_conferir_colunas_dos_descartes():
    d = validar(minima())
    v = d.visoes[0]
    assert decl.conferir_colunas(d, v, [("periodo", "VARCHAR"), ("m_total", "BIGINT")],
                                 descartes=True) == []  # fmt: skip
    assert decl.conferir_colunas(d, v, [("periodo", "VARCHAR"), ("m_nada", "BIGINT")],
                                 descartes=True)  # fmt: skip


def test_familia_duckdb():
    assert decl.familia_duckdb("DECIMAL(18,3)") == "decimal"
    assert decl.familia_duckdb("HUGEINT") == "inteiro"
    assert decl.familia_duckdb("VARCHAR") == "texto"


def test_tabelas_duplicadas():
    a = validar(minima())

    def com_id(novo: str):
        d = minima()
        d["id"] = novo
        d["entrada"][0]["glob"] = f"{novo.partition('/')[0]}/x/*.parquet"
        return decl.validar(d, SQLS)

    b = com_id("teste-x/exemplo")
    c = com_id("teste/x-exemplo")
    assert decl.tabelas_duplicadas([a, b]) == []
    assert decl.tabelas_duplicadas([a, a])  # id repetido
    # `teste-x/exemplo` e `teste/x-exemplo` geram a mesma tabela
    assert "c_teste_x_exemplo_uf" in decl.tabelas_duplicadas([b, c])[0]


# --- registro de fetchers ---------------------------------------------------------


def test_fonte_fora_do_registro_e_restrita_no_registro():
    registro = {
        "teste": {
            "id": "teste",
            "redistribuicao": "restrita",
            "lake_source_id": "teste",
        }
    }
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(minima(), SQLS, fontes=registro)
    assert "marca a fonte 'teste' como restrita" in str(exc.value)
    with pytest.raises(decl.DeclaracaoInvalida) as exc2:
        decl.validar(minima(), SQLS, fontes={"outra": {"id": "outra"}})
    assert "não está no registro de fetchers" in str(exc2.value)


def test_pasta_do_lake_vem_do_lake_source_id():
    registro = {"teste": {"id": "teste", "lake_source_id": "teste-lake"}}
    d = minima()
    d["entrada"][0]["glob"] = "teste-lake/exemplo/*.parquet"
    assert decl.validar(d, SQLS, fontes=registro).id == "teste/exemplo"


# --- arquivos -----------------------------------------------------------------------


def test_carregar_le_toml_e_sqls_e_aponta_toml_quebrado(tmp_path):
    (tmp_path / "base.sql").write_text(SQL_BASE)
    (tmp_path / "uf.sql").write_text(SQL_UF)
    (tmp_path / "conjunto.toml").write_text(
        'schema_versao = 1\nid = "teste/exemplo"\ntitulo = "T"\ndescricao = "D"\n'
        'estado = "rascunho"\npreparo = "base.sql"\n'
        '[fonte]\norgao = "O"\nlicenca = "CC BY"\natribuicao = "A"\nredistribuicao = "livre"\n'
        '[entidade]\ntipo = "territorio"\nrotulo = "T"\nqualifier = "geo"\n'
        '[tempo]\ntipo = "mes"\nfrequencia = "monthly"\nalinhamento_painel = "inicio"\npadrao = "ultimo"\n'
        '[[entrada]]\nnome = "ent"\nglob = "teste/x/*.parquet"\n'
        '[[visao]]\nnivel = "UF"\nchave = "sigla"\nconsulta = "uf.sql"\ncabecalhos = ["UF", "Nome"]\n'
        '[[medida]]\nid = "total"\nrotulo = "T"\nunidade = "u"\ntipo = "bigint"\n'
    )
    assert decl.carregar(tmp_path).id == "teste/exemplo"
    (tmp_path / "conjunto.toml").write_text("isto não é = toml [")
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.carregar(tmp_path)
    assert "TOML inválido" in str(exc.value)
    with pytest.raises(decl.DeclaracaoInvalida):
        decl.carregar(tmp_path / "nao-existe")


def test_main_devolve_codigo_de_saida(tmp_path, capsys):
    (tmp_path / "conjunto.toml").write_text("schema_versao = 7\n")
    assert decl.main([str(tmp_path)]) == 1
    assert "versão 7 não suportada" in capsys.readouterr().err


# --- nota condicional (emenda de 26/11/2026 ao ADR) -----------------------------------


def com_notas(*blocos: dict) -> dict:
    """Declaração mínima com uma dimensão (`tipo`), três atributos e as notas dadas."""
    d = minima()
    d["dimensao"] = [{"id": "tipo", "rotulo": "Tipo", "valores": ["fatal", "outro"]}]
    d["atributo"] = [
        {"id": "encerramento", "rotulo": "Encerramento", "tipo": "date"},
        {"id": "consolidado", "rotulo": "Consolidado", "tipo": "boolean"},
        {"id": "origem", "rotulo": "Origem", "tipo": "text"},
        {"id": "versao", "rotulo": "Versão", "tipo": "integer"},
    ]
    d["nota_condicional"] = list(blocos)
    return d


NOTA_DFP = {
    "texto": "Encerrado em {valores}.",
    "quando": {"atributo": "encerramento", "diferente_de": "12-31"},
    "substantivo": ["companhia", "companhias"],
}


def test_espelho_sempre_traz_notas_condicionais_mesmo_vazio():
    assert validar(minima()).espelho()["notas_condicionais"] == []


def test_nota_condicional_valida_e_entra_no_espelho_de_forma_estavel():
    d = validar(
        com_notas(
            NOTA_DFP,
            {"texto": "Só óbitos.", "quando": {"dimensao": "tipo", "igual_a": "fatal"}},
            {
                "texto": "{n} sem consolidar.",
                "quando": {"atributo": "consolidado", "igual_a": False},
            },
            {"texto": "Versão 2.", "quando": {"atributo": "versao", "igual_a": 2}},
            {
                "texto": "De fora.",
                "quando": {"atributo": "origem", "diferente_de": "mte"},
            },
        )
    )
    assert len(d.notas_condicionais) == 5
    primeira = d.espelho()["notas_condicionais"][0]
    assert primeira == {
        "texto": "Encerrado em {valores}.",
        "quando": {
            "tipo": "atributo",
            "id": "encerramento",
            "operador": "diferente_de",
            "valor": "12-31",
        },
        "substantivo": ["companhia", "companhias"],
    }
    assert d.espelho()["notas_condicionais"][1]["substantivo"] is None
    import json

    assert json.loads(json.dumps(d.espelho())) == d.espelho()


def test_nota_condicional_muda_o_espelho_e_portanto_o_hash():
    sem = validar(com_notas()).espelho()
    com = validar(com_notas(NOTA_DFP)).espelho()
    assert sem != com


def _nc(**campos) -> dict:
    base = {"texto": "Aviso.", "quando": {"atributo": "origem", "igual_a": "x"}}
    base.update(campos)
    return base


NOTAS_QUEBRADAS = [
    ("campo desconhecido", {**_nc(), "senao": "x"}, "campo desconhecido"),
    (
        "sem texto",
        {"quando": {"atributo": "origem", "igual_a": "x"}},
        "texto: campo obrigatório",
    ),
    ("sem quando", {"texto": "x"}, "quando: campo obrigatório"),
    ("texto vazio", _nc(texto=" "), "texto vazio"),
    (
        "marcador desconhecido",
        _nc(texto="Veja {linhas}."),
        "marcador {linhas} desconhecido",
    ),
    ("marcador com sugestão", _nc(texto="Veja {valor}."), "você quis dizer 'valores'"),
    ("chave solta", _nc(texto="Veja } solta."), "chave solta"),
    ("chave aberta", _nc(texto="Veja { solta."), "chave solta"),
    ("chaves vazias", _nc(texto="Veja {}."), "marcador {} desconhecido"),
    (
        "sem alvo",
        _nc(quando={"igual_a": "x"}),
        "exatamente um entre 'atributo' e 'dimensao'",
    ),
    (
        "dois alvos",
        _nc(quando={"atributo": "origem", "dimensao": "tipo", "igual_a": "x"}),
        "exatamente um entre 'atributo' e 'dimensao'",
    ),
    ("sem operador", _nc(quando={"atributo": "origem"}), "exatamente um operador"),
    (
        "dois operadores",
        _nc(quando={"atributo": "origem", "igual_a": "x", "diferente_de": "y"}),
        "exatamente um operador",
    ),
    (
        "operador fora do vocabulário",
        _nc(quando={"atributo": "origem", "maior_que": 1}),
        "campo desconhecido",
    ),
    (
        "atributo não declarado",
        _nc(quando={"atributo": "encerramentos", "igual_a": "x"}),
        "você quis dizer 'encerramento'",
    ),
    (
        "dimensão não declarada",
        _nc(quando={"dimensao": "gravidade", "igual_a": "x"}),
        "dimensao 'gravidade' não está declarado",
    ),
    (
        "quando não é tabela",
        _nc(quando="encerramento"),
        "esperava uma tabela",
    ),
    (
        "data com ano",
        _nc(quando={"atributo": "encerramento", "igual_a": "2024-12-31"}),
        "não é MM-DD",
    ),
    (
        "data com dia impossível",
        _nc(quando={"atributo": "encerramento", "igual_a": "02-30"}),
        "não é MM-DD",
    ),
    (
        "data com mês impossível",
        _nc(quando={"atributo": "encerramento", "igual_a": "13-01"}),
        "não é MM-DD",
    ),
    (
        "boolean com texto",
        _nc(quando={"atributo": "consolidado", "igual_a": "sim"}),
        "pede true/false",
    ),
    (
        "integer com booleano",
        _nc(quando={"atributo": "versao", "igual_a": True}),
        "pede um inteiro",
    ),
    (
        "integer com texto",
        _nc(quando={"atributo": "versao", "igual_a": "2"}),
        "pede um inteiro",
    ),
    (
        "dimensão fora dos valores",
        _nc(quando={"dimensao": "tipo", "igual_a": "fatais"}),
        "não está nos valores da dimensão",
    ),
    (
        "texto longo demais",
        _nc(quando={"atributo": "origem", "igual_a": "x" * 81}),
        "máximo 80",
    ),
    ("substantivo com um item", _nc(texto="{n}", substantivo=["a"]), "dois textos"),
    (
        "substantivo com três itens",
        _nc(texto="{n}", substantivo=["a", "b", "c"]),
        "dois textos",
    ),
    ("substantivo com chave", _nc(texto="{n}", substantivo=["a", "{b}"]), "com chave"),
    (
        "substantivo sem marcador",
        _nc(texto="sem marcador", substantivo=["a", "as"]),
        "só tem efeito com {n} ou {valores}",
    ),
]


@pytest.mark.parametrize(
    ("bloco", "esperado"),
    [(b, m) for _, b, m in NOTAS_QUEBRADAS],
    ids=[n for n, _, _ in NOTAS_QUEBRADAS],
)
def test_nota_condicional_quebrada_falha_com_mensagem_clara(bloco, esperado):
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(com_notas(bloco))
    assert esperado in str(exc.value), str(exc.value)
    assert "nota_condicional[0]" in str(exc.value)


def test_nota_condicional_dimensao_aberta_aceita_valor_no_padrao():
    d = minima()
    d["dimensao"] = [{"id": "tipo", "rotulo": "Tipo"}]
    d["nota_condicional"] = [
        {"texto": "x", "quando": {"dimensao": "tipo", "igual_a": "nao fatal"}}
    ]
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(d)
    assert "fora do padrão" in str(exc.value)
    d["nota_condicional"][0]["quando"]["igual_a"] = "nao_fatal"
    assert validar(d).notas_condicionais[0].quando.valor == "nao_fatal"


def test_nota_condicional_aceita_29_de_fevereiro_e_so_ate_dez_blocos():
    d = com_notas(_nc(quando={"atributo": "encerramento", "igual_a": "02-29"}))
    assert validar(d).notas_condicionais[0].quando.valor == "02-29"
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(com_notas(*[_nc() for _ in range(11)]))
    assert "11 blocos (máximo 10)" in str(exc.value)


def test_nota_condicional_bloco_que_nao_e_lista_de_tabelas():
    d = minima()
    d["nota_condicional"] = "texto"
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        validar(d)
    assert "esperava uma lista de blocos [[nota_condicional]]" in str(exc.value)


# --- tabela de correções (CSV) e auditoria ------------------------------------------------

CSV_OK = (
    "cnpj,exercicio,medida,valor,referencia,motivo,data\n"
    '1,2023,total,10.5,"Fonte, documento 1",duas cópias,2026-11-26\n'
    "2,2023,total,0,Fonte,duas cópias,2026-11-26\n"
)
SQL_AUDITORIA = "SELECT 'ambigua' AS tipo, cnpj AS chave, 'x' AS detalhe FROM correcoes WHERE valor > 0"


def com_correcoes(csv: str = CSV_OK, **extra) -> tuple[dict, dict]:
    d = minima()
    d["correcoes"] = "correcoes.csv"
    d["auditoria"] = "auditoria.sql"
    d.update(extra)
    return d, {**SQLS, "correcoes.csv": csv, "auditoria.sql": SQL_AUDITORIA}


def test_correcoes_validas_viram_campos_da_declaracao_e_ficam_fora_do_espelho():
    d, sqls = com_correcoes()
    obj = decl.validar(d, sqls)
    assert (obj.correcoes, obj.auditoria) == ("correcoes.csv", "auditoria.sql")
    espelho = obj.espelho()
    assert "correcoes" not in espelho and "auditoria" not in espelho  # contrato intacto
    tabela, erros = decl.ler_correcoes(CSV_OK)
    assert erros == [] and tabela.chaves == ("cnpj", "exercicio", "medida")
    assert tabela.colunas == (
        "cnpj", "exercicio", "medida", "valor", "referencia", "motivo", "data",
    )  # fmt: skip
    assert tabela.linhas[0][3:] == (
        10.5,
        "Fonte, documento 1",
        "duas cópias",
        __import__("datetime").date(2026, 11, 26),
    )


def test_csv_so_com_cabecalho_e_valido():
    cab = "cnpj,valor,referencia,motivo,data\n"
    tabela, erros = decl.ler_correcoes(cab)
    assert erros == [] and tabela.linhas == ()


CSVS_RUINS = [
    ("vazio", "", "CSV vazio"),
    ("sem coluna fixa", "cnpj,valor,referencia,data\n", "faltam as colunas motivo"),
    (
        "sem chave",
        "valor,referencia,motivo,data\n",
        "falta pelo menos uma coluna de chave",
    ),
    (
        "coluna repetida",
        "cnpj,cnpj,valor,referencia,motivo,data\n",
        "colunas repetidas",
    ),
    ("nome ruim", "CNPJ,valor,referencia,motivo,data\n", "fora do padrão"),
    (
        "linha curta",
        "cnpj,valor,referencia,motivo,data\n1,2,r,m\n",
        "linha 2: 4 colunas",
    ),
    (
        "célula vazia",
        "cnpj,valor,referencia,motivo,data\n1,2,,m,2026-11-26\n",
        "célula vazia em referencia",
    ),
    (
        "valor texto",
        "cnpj,valor,referencia,motivo,data\n1,dois,r,m,2026-11-26\n",
        "não é um número",
    ),
    (
        "valor infinito",
        "cnpj,valor,referencia,motivo,data\n1,inf,r,m,2026-11-26\n",
        "não é um número",
    ),
    (
        "data ruim",
        "cnpj,valor,referencia,motivo,data\n1,2,r,m,26/11/2026\n",
        "não é AAAA-MM-DD",
    ),
    (
        "chave repetida",
        "cnpj,valor,referencia,motivo,data\n1,2,r,m,2026-11-26\n1,3,r,m,2026-11-26\n",
        "chave repetida",
    ),
    (
        "texto longo",
        "cnpj,valor,referencia,motivo,data\n1,2," + "r" * 601 + ",m,2026-11-26\n",
        "referencia com 601 caracteres",
    ),
]


@pytest.mark.parametrize(
    ("csv", "esperado"),
    [(c, m) for _, c, m in CSVS_RUINS],
    ids=[n for n, _, _ in CSVS_RUINS],
)
def test_csv_de_correcoes_ruim_falha_com_mensagem_clara(csv, esperado):
    tabela, erros = decl.ler_correcoes(csv)
    assert tabela is None and any(esperado in e for e in erros), erros
    d, sqls = com_correcoes(csv)
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert esperado in str(exc.value)


def test_csv_com_mais_de_500_correcoes_e_recusado():
    linhas = "".join(f"{i},1,r,m,2026-11-26\n" for i in range(501))
    _, erros = decl.ler_correcoes("cnpj,valor,referencia,motivo,data\n" + linhas)
    assert any("501 correções (máximo 500)" in e for e in erros)


def test_correcoes_exige_auditoria_arquivo_existente_e_nome_valido():
    d, sqls = com_correcoes()
    del d["auditoria"]
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert "`correcoes` exige `auditoria`" in str(exc.value)
    d, sqls = com_correcoes()
    del sqls["correcoes.csv"]
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert "arquivo correcoes.csv não existe" in str(exc.value)
    d, sqls = com_correcoes(correcoes="../fora.csv")
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert "fora do padrão nome.csv" in str(exc.value)
    d, sqls = com_correcoes(correcoes="Correcoes.txt")
    with pytest.raises(decl.DeclaracaoInvalida):
        decl.validar(d, sqls)


def test_sql_que_le_correcoes_sem_declarar_e_recusada():
    d = minima()
    sqls = {**SQLS, "uf.sql": SQL_UF + " WHERE EXISTS (SELECT 1 FROM correcoes)"}
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert "lê a tabela `correcoes`" in str(exc.value)


def test_auditoria_passa_pelo_mesmo_filtro_de_sql_das_consultas():
    d, sqls = com_correcoes()
    sqls["auditoria.sql"] = "SELECT * FROM read_csv('/etc/passwd')"
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert "auditoria (auditoria.sql)" in str(exc.value) and "read_csv" in str(
        exc.value
    )
    d, sqls = com_correcoes()
    sqls["auditoria.sql"] = "DROP TABLE correcoes"
    with pytest.raises(decl.DeclaracaoInvalida):
        decl.validar(d, sqls)


def test_o_mesmo_arquivo_nao_serve_a_dois_campos():
    d, sqls = com_correcoes()
    d["auditoria"] = "uf.sql"
    with pytest.raises(decl.DeclaracaoInvalida) as exc:
        decl.validar(d, sqls)
    assert "mais de um campo" in str(exc.value)


def test_carregar_le_csv_e_sql_da_pasta(tmp_path):
    (tmp_path / "uf.sql").write_text(SQL_UF)
    (tmp_path / "base.sql").write_text(SQL_BASE)
    (tmp_path / "correcoes.csv").write_text(CSV_OK)
    (tmp_path / "auditoria.sql").write_text(SQL_AUDITORIA)
    (tmp_path / "conjunto.toml").write_text(
        'schema_versao = 1\nid = "teste/exemplo"\ntitulo = "T"\ndescricao = "D"\nestado = "rascunho"\n'
        'preparo = "base.sql"\ncorrecoes = "correcoes.csv"\nauditoria = "auditoria.sql"\n'
        '[fonte]\norgao = "O"\nlicenca = "CC BY"\natribuicao = "A"\nredistribuicao = "livre"\n'
        '[entidade]\ntipo = "territorio"\nrotulo = "T"\nqualifier = "geo"\n'
        '[tempo]\ntipo = "mes"\nfrequencia = "monthly"\nalinhamento_painel = "inicio"\npadrao = "ultimo"\n'
        '[[entrada]]\nnome = "ent"\nglob = "teste/x/*.parquet"\n'
        '[[visao]]\nnivel = "UF"\nchave = "sigla"\nconsulta = "uf.sql"\ncabecalhos = ["UF", "Nome"]\n'
        '[[medida]]\nid = "total"\nrotulo = "T"\nunidade = "u"\ntipo = "bigint"\n'
    )
    assert decl.carregar(tmp_path).correcoes == "correcoes.csv"
