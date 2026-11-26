# ruff: noqa: E501
"""Confere as declarações de `publicacao/` (conjuntos tabulares publicados no portal).

Para cada `publicacao/<fonte>/<conjunto>/conjunto.toml` (e para o exemplo `_exemplo`):

* a declaração passa no validador estrito (`infra/publicacao/declaracao.py` do monorepo;
  fora dele, aponte `QUANTILICA_INFRA_DIR` para a pasta `infra/` ou os testes são pulados);
* as consultas rodam em DuckDB sobre Parquet sintético (`tests/lake_sintetico.py`) e devolvem
  exatamente as colunas e tipos do contrato, com chave única;
* a aritmética de cada regra de negócio (CAGED: dentro do prazo + fora do prazo - exclusões;
  DFP: consolidada, escala MIL, versão mais nova) sai nos números esperados;
* o espelho (`Declaracao.espelho()`, o JSON de `publicacao.conjunto.declaracao`) do exemplo é
  igual ao `publicacao/_exemplo.json`, e este ao `tests/fixtures/publicacao_exemplo.json` do
  portal quando o portal está ao lado;
* nenhum arquivo do catálogo cita termos de operação interna (o repositório é público).
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import duckdb
import lake_sintetico as lake_mod
import pytest

ROOT = Path(__file__).resolve().parent.parent
PUBLICACAO = ROOT / "publicacao"
D = dt.date


def _achar_infra() -> Path | None:
    candidatos = []
    if os.environ.get("QUANTILICA_INFRA_DIR"):
        candidatos.append(Path(os.environ["QUANTILICA_INFRA_DIR"]))
    candidatos.append(ROOT.parent / "infra")
    for c in candidatos:
        if (c / "publicacao" / "declaracao.py").is_file():
            return c
    return None


INFRA = _achar_infra()
if INFRA is None:
    pytest.skip(
        "infra/publicacao/declaracao.py não encontrado (defina QUANTILICA_INFRA_DIR)",
        allow_module_level=True,
    )

# Carrega o pacote `publicacao` da infra sob o nome `quantilica_publicacao` (a pasta de
# dados deste repositório também se chama `publicacao`).
_spec = importlib.util.spec_from_file_location(
    "quantilica_publicacao",
    INFRA / "publicacao" / "__init__.py",
    submodule_search_locations=[str(INFRA / "publicacao")],
)
_pacote = importlib.util.module_from_spec(_spec)
sys.modules["quantilica_publicacao"] = _pacote
assert _spec and _spec.loader
_spec.loader.exec_module(_pacote)
from quantilica_publicacao import consulta as cons  # noqa: E402
from quantilica_publicacao import declaracao as dec  # noqa: E402

REGISTRO = INFRA / "registry.json"
FONTES = dec.ler_registro(REGISTRO) if REGISTRO.is_file() else None

REAIS = dec.declaracoes_do_catalogo(PUBLICACAO)
EXEMPLO = PUBLICACAO / "_exemplo" / "conjunto.toml"
TODAS = [*REAIS, EXEMPLO]


def _ids(caminhos: list[Path]) -> list[str]:
    return [f"{c.parent.parent.name}/{c.parent.name}" for c in caminhos]


def carregar(caminho: Path) -> dec.Declaracao:
    real = caminho != EXEMPLO
    return dec.carregar(caminho, fontes=FONTES if real else None)


def test_o_catalogo_tem_caged_e_dfp():
    assert {c.parent.parent.name + "/" + c.parent.name for c in REAIS} >= {
        "pdet/caged",
        "cvm/dfp",
    }


@pytest.mark.parametrize("caminho", TODAS, ids=_ids(TODAS))
def test_declaracao_valida(caminho):
    d = carregar(caminho)
    assert d.schema_versao == dec.SCHEMA_VERSAO
    # a pasta é a identidade: publicacao/<fonte>/<conjunto>
    esperado = "exemplo/sinistros" if caminho == EXEMPLO else _ids([caminho])[0]
    assert d.id == esperado


def test_ids_e_tabelas_unicos():
    assert dec.tabelas_duplicadas(carregar(c) for c in TODAS) == []


@pytest.mark.parametrize("caminho", REAIS, ids=_ids(REAIS))
def test_conjunto_real_cumpre_o_criterio_de_entrada_declarativo(caminho):
    """Licença, atribuição e uma conferência com a fonte: sem isso não vira `publicado`."""
    d = carregar(caminho)
    assert d.fonte.licenca and d.fonte.atribuicao and d.fonte.orgao
    assert d.conferencias, "declare ao menos uma [[conferencia]] com valor da fonte"
    assert d.fonte.redistribuicao == "livre"


def test_atribuicao_do_caged_nao_diz_sem_restricao():
    caged = carregar(PUBLICACAO / "pdet" / "caged" / "conjunto.toml")
    texto = f"{caged.fonte.licenca} {caged.fonte.atribuicao}".lower()
    assert "sem restrição" not in texto and "sem restricao" not in texto
    assert "ministério do trabalho e emprego" in texto
    assert "dado público agregado" in texto


def test_licenca_e_atribuicao_da_dfp():
    dfp = carregar(PUBLICACAO / "cvm" / "dfp" / "conjunto.toml")
    assert dfp.fonte.licenca == "ODbL-1.0"
    assert "opendatacommons.org/licenses/odbl/1-0" in dfp.fonte.atribuicao
    assert "CVM" in dfp.fonte.atribuicao


# --- execução sobre Parquet sintético ----------------------------------------------


@pytest.fixture()
def lake(tmp_path: Path) -> Path:
    raiz = tmp_path / "l'ake"  # aspas no caminho: nada de interpolação frágil no SQL
    lake_mod.montar_caged(raiz)
    lake_mod.montar_dfp(raiz)
    lake_mod.montar_exemplo(raiz)
    return raiz


def rodar(caminho: Path, lake: Path):
    """Executa preparo e visões: `{nivel: (colunas, linhas)}` (e descartes em `nivel#`)."""
    d = carregar(caminho)
    sqls = cons.ler_sqls(caminho.parent, d)
    con = duckdb.connect()
    try:
        cons.preparar(con, d, sqls, lake)
        saida = {}
        for v in d.visoes:
            saida[v.nivel] = cons.executar_visao(con, d, v, sqls, lake)
            if v.descartes:
                saida[v.nivel + "#"] = cons.executar_visao(
                    con, d, v, sqls, lake, descartes=True
                )
    finally:
        con.close()
    return d, saida


@pytest.mark.parametrize("caminho", TODAS, ids=_ids(TODAS))
def test_consultas_cumprem_o_contrato_de_colunas_e_a_chave(caminho, lake):
    d, saida = rodar(caminho, lake)
    for v in d.visoes:
        colunas, linhas = saida[v.nivel]
        assert dec.conferir_colunas(d, v, colunas) == []
        assert linhas, f"visão {v.nivel} sem linhas no lake sintético"
        nomes = [c for c, _ in colunas]
        chave = ["entidade", "periodo", *[n for n in nomes if n.startswith("d_")]]
        pos = [nomes.index(c) for c in chave]
        vistos = {tuple(linha[i] for i in pos) for linha in linhas}
        assert len(vistos) == len(linhas), f"chave duplicada na visão {v.nivel}"
        if v.descartes:
            cols_d, _ = saida[v.nivel + "#"]
            assert dec.conferir_colunas(d, v, cols_d, descartes=True) == []


def test_caged_soma_mov_for_e_subtrai_exc(lake):
    d, saida = rodar(PUBLICACAO / "pdet" / "caged" / "conjunto.toml", lake)
    cols, linhas = saida["UF"]
    i = {c: k for k, (c, _) in enumerate(cols)}
    uf = {
        (r[i["periodo"]], r[i["entidade"]]): (
            r[i["m_admissoes"]],
            r[i["m_desligamentos"]],
            r[i["m_saldo"]],
        )
        for r in linhas
    }
    # SP 05: mov 5+1 adm e 2 des; for +2 adm e +1 des; exc -1 adm
    assert uf[(D(2026, 5, 1), "SP")] == (
        5 + 1 + 2 - 1,
        2 + 1,
        (5 + 1 + 2 - 1) - (2 + 1),
    )
    assert uf[(D(2026, 5, 1), "RJ")] == (2, 3, -1)
    # SP 06: 3 adm + 1 adm de município fora do padrão (a UF vale), 1 des
    assert uf[(D(2026, 6, 1), "SP")] == (3 + 1, 1, 3)
    assert uf[(D(2026, 6, 1), "RJ")] == (1, 1, 0)
    assert len(uf) == 4
    assert all(isinstance(r[i["m_saldo"]], int) for r in linhas)
    _, mun = saida["MUN"]
    im = {c: k for k, (c, _) in enumerate(saida["MUN"][0])}
    por_mun = {
        (r[im["periodo"]], r[im["entidade"]]): (
            r[im["m_admissoes"]],
            r[im["m_desligamentos"]],
        )
        for r in mun
    }
    assert por_mun[(D(2026, 5, 1), "355030")] == (5 + 2 - 1, 2 + 1)
    assert por_mun[(D(2026, 5, 1), "350950")] == (1, 0)
    assert all(
        m != "999999" and len(m) == 6 for _, m in por_mun
    )  # sem localização válida
    assert (D(2026, 6, 1), "35") not in por_mun  # município fora do padrão sai
    # nenhum saldo líquido nulo é gravado (HAVING)
    assert all(a or b for a, b in por_mun.values())


def test_caged_descartes_contam_o_que_ficou_de_fora(lake):
    _, saida = rodar(PUBLICACAO / "pdet" / "caged" / "conjunto.toml", lake)
    uf = {r[0]: (r[1], r[2]) for r in saida["UF#"][1]}
    # UF 99 (4 adm) em 2026-05; competência "2026" inválida (2 adm)
    assert uf == {"2026-05": (4, 0), "invalida": (2, 0)}
    mun = {r[0]: (r[1], r[2]) for r in saida["MUN#"][1]}
    # município 999999 (4 adm) em 05; "35" fora do padrão (1 adm) em 06; inválida (2 adm)
    assert mun == {"2026-05": (4, 0), "2026-06": (1, 0), "invalida": (2, 0)}


def test_dfp_prefere_consolidada_e_resolve_contas_por_setor(lake):
    d, saida = rodar(PUBLICACAO / "cvm" / "dfp" / "conjunto.toml", lake)
    cols, linhas = saida["CIA"]
    i = {c: k for k, (c, _) in enumerate(cols)}
    por = {(r[i["entidade"]], r[i["periodo"]].year): r for r in linhas}
    alfa, beta = "11111111000111", "22222222000122"
    banco, gama = "33333333000133", "44444444000144"

    def v(cnpj, conta):
        return por[(cnpj, 2024)][i["m_" + conta]]

    # consolidada vence a individual; MIL multiplica por 1000; PENÚLTIMO e dmpl ignorados
    assert v(alfa, "ativo_total") == 1_000_000.0
    assert por[(alfa, 2024)][i["a_consolidado"]] is True
    assert v(alfa, "patrimonio_liquido") == 400_000.0
    assert v(alfa, "receita") == 800_000.0
    assert v(alfa, "lucro_liquido") == 90_000.0  # não pega o "Lucro por Ação"
    assert v(alfa, "caixa_operacional") == 70_000.0
    # só individual: flag falsa, versão mais nova, DFC pelo método direto, 31/12
    assert v(beta, "ativo_total") == 60_000.0
    assert por[(beta, 2024)][i["a_consolidado"]] is False
    assert por[(beta, 2024)][i["a_encerramento"]] == D(2024, 12, 31)
    assert v(beta, "lucro_liquido") == 12_000.0
    assert v(beta, "caixa_operacional") == 30_000.0
    # banco: PL no 2.07 (o 2.03 é "Provisões"); UNIDADE não multiplica; sem receita: nulo
    assert v(banco, "patrimonio_liquido") == 3.0
    assert v(banco, "ativo_total") == 7.0
    assert v(banco, "receita") is None
    # exercício que fecha em 30/06: o ano do encerramento
    assert v(gama, "ativo_total") == 5_000.0
    assert por[(gama, 2024)][i["a_encerramento"]] == D(2024, 6, 30)
    assert por[(alfa, 2024)][i["periodo"]] == D(2024, 1, 1)
    assert len(por) == 4
    assert por[(alfa, 2024)][i["entidade_rotulo"]] == "ALFA SA"
    assert por[(alfa, 2024)][i["entidade_cd_cvm"]] == "000001"


def test_exemplo_exercita_dimensao_atributo_e_descartes(lake):
    d, saida = rodar(EXEMPLO, lake)
    cols, linhas = saida["MUN"]
    i = {c: k for k, (c, _) in enumerate(cols)}
    sp = [r for r in linhas if r[i["entidade"]] == "3550308"]
    assert {r[i["d_tipo_registro"]] for r in sp} == {"fatal", "nao_fatal"}
    fatal = next(r for r in sp if r[i["d_tipo_registro"]] == "fatal")
    assert fatal[i["m_sinistros"]] == 2 and fatal[i["m_vitimas_por_sinistro"]] == 2.0
    assert saida["MUN#"][1] == [("sem_municipio", 1)]


# --- cópias divergentes da DFP: moda, tabela de correções e auditoria ----------------

DFP_TOML = PUBLICACAO / "cvm" / "dfp" / "conjunto.toml"
AUTOMOB, ENGELHART = "35654688000108", "14796754000104"
BRASIL_TERRENOS, REVEE, ZETA, ETA = (
    "20961867000110",
    "52810883000107",
    "55555555000155",
    "66666666000166",
)


def rodar_dfp_copias(tmp_path: Path, **valores):
    """Executa a DFP real (com o `correcoes.csv` real) sobre cópias sintéticas.

    Devolve `({(cnpj, exercício): {medida: valor}}, [(tipo, chave, detalhe)])`.
    """
    raiz = tmp_path / "lake"
    lake_mod.montar_dfp_copias(raiz, **valores)
    d = carregar(DFP_TOML)
    sqls = cons.ler_sqls(DFP_TOML.parent, d)
    con = duckdb.connect()
    try:
        cons.preparar(con, d, sqls, raiz)
        cols, linhas = cons.executar_visao(con, d, d.visoes[0], sqls, raiz)
        achados = cons.auditar(con, d, sqls, raiz)
    finally:
        con.close()
    i = {c: k for k, (c, _) in enumerate(cols)}
    por = {
        (r[i["entidade"]], r[i["periodo"]].year): {
            m.id: r[i["m_" + m.id]] for m in d.medidas
        }
        for r in linhas
    }
    return por, achados


def test_dfp_copias_divergentes_as_seis_celulas_saem_com_o_valor_oficial(tmp_path):
    por, _ = rodar_dfp_copias(tmp_path)
    assert por[(AUTOMOB, 2023)]["lucro_liquido"] == 89_403_000.0
    assert por[(ENGELHART, 2023)]["patrimonio_liquido"] == 10_919_081_000.0  # o menor
    assert por[(BRASIL_TERRENOS, 2025)]["patrimonio_liquido"] == 4_471_389_000.0
    assert por[(BRASIL_TERRENOS, 2025)]["caixa_operacional"] == 313_156_000.0
    assert por[(REVEE, 2023)]["receita"] == 0.0
    assert por[(REVEE, 2023)]["lucro_liquido"] == 0.0


def test_dfp_moda_sem_correcao_e_empate_pelo_maior(tmp_path):
    por, _ = rodar_dfp_copias(tmp_path)
    assert por[(ETA, 2023)]["ativo_total"] == 500_000.0  # cópias idênticas: inofensivas
    assert por[(ZETA, 2023)]["ativo_total"] == 200_000.0  # empate sem correção: o maior
    # a moda vale quando a correção não vale: três cópias, duas iguais, e a de fora é a MAIOR
    # (o valor oficial da correção não está entre as cópias: ela fica inerte, a moda decide)
    por, achados = rodar_dfp_copias(
        tmp_path / "b", brasil_pl=(5, 5, 9), revee=(7, 7, 9)
    )
    assert por[(BRASIL_TERRENOS, 2025)]["patrimonio_liquido"] == 5_000.0
    assert por[(REVEE, 2023)]["receita"] == 7.0
    assert any(
        t == "correcao_sem_efeito" and "patrimonio_liquido" in c for t, c, _ in achados
    )


def test_dfp_auditoria_conta_aplicadas_e_avisa_so_o_empate_sem_correcao(tmp_path):
    _, achados = rodar_dfp_copias(tmp_path)
    por_tipo: dict[str, list[tuple[str, str]]] = {}
    for tipo, chave, detalhe in achados:
        por_tipo.setdefault(tipo, []).append((chave, detalhe))
    assert [c for c, _ in por_tipo["ambigua"]] == [
        f"{ZETA} 2023 ativo_total consolidada"
    ]
    assert "100000 / 200000" in por_tipo["ambigua"][0][1]
    assert len(por_tipo["correcao_aplicada"]) == 6
    assert "correcao_sem_efeito" not in por_tipo
    aplicada = dict(por_tipo["correcao_aplicada"])
    assert "ID_DOC 141876" in aplicada[f"{AUTOMOB} 2023 lucro_liquido consolidada"]


def test_dfp_correcao_inerte_quando_a_cvm_limpa_o_arquivo_ou_o_valor_mudou(tmp_path):
    # Automob: a CVM limpou o arquivo (uma só cópia); Engelhart: o valor oficial sumiu
    por, achados = rodar_dfp_copias(
        tmp_path, automob=(89403,), engelhart=(10919083, 10919084)
    )
    assert por[(AUTOMOB, 2023)]["lucro_liquido"] == 89_403_000.0  # o que o lake traz
    assert (
        por[(ENGELHART, 2023)]["patrimonio_liquido"] == 10_919_084_000.0
    )  # empate: o maior
    sem_efeito = {c: d for t, c, d in achados if t == "correcao_sem_efeito"}
    assert (
        "não deixou mais de um valor"
        in sem_efeito[f"{AUTOMOB} 2023 lucro_liquido consolidada"]
    )
    assert (
        "não está entre as cópias"
        in sem_efeito[f"{ENGELHART} 2023 patrimonio_liquido individual"]
    )
    # a correção inerte NUNCA inventa valor; o empate novo (Engelhart) volta como ambíguo
    ambiguas = {c for t, c, _ in achados if t == "ambigua"}
    assert f"{ENGELHART} 2023 patrimonio_liquido individual" in ambiguas
    assert f"{ZETA} 2023 ativo_total consolidada" in ambiguas


def test_dfp_correcao_de_celula_que_saiu_da_selecao_e_avisada(tmp_path):
    # sem nenhuma cópia da Revee no lake: as duas correções dela ficam sem célula
    por, achados = rodar_dfp_copias(tmp_path, revee=())
    assert (REVEE, 2023) not in por
    motivos = [d for t, c, d in achados if t == "correcao_sem_efeito" and REVEE in c]
    assert len(motivos) == 2 and all("não está na seleção" in m for m in motivos)


def test_dfp_correcoes_csv_cumpre_o_formato_e_a_conferencia_da_automob():
    d = carregar(DFP_TOML)
    assert d.correcoes == "correcoes.csv" and d.auditoria == "dfp_auditoria.sql"
    tabela, erros = dec.ler_correcoes(
        (DFP_TOML.parent / "correcoes.csv").read_text("utf-8")
    )
    assert erros == [] and len(tabela.linhas) == 6
    assert tabela.chaves == ("cnpj", "exercicio", "medida", "demonstracao")
    assert any(
        c.entidade == AUTOMOB and c.medida == "lucro_liquido" and c.valor == 89_403_000
        for c in d.conferencias
    )


# --- espelho e exemplo dourado -----------------------------------------------------


def test_espelho_do_exemplo_e_igual_ao_json_dourado():
    esperado = json.loads((PUBLICACAO / "_exemplo.json").read_text(encoding="utf-8"))
    assert carregar(EXEMPLO).espelho() == esperado


def test_todos_os_espelhos_tem_as_mesmas_chaves():
    ouro = json.loads((PUBLICACAO / "_exemplo.json").read_text(encoding="utf-8"))
    for c in TODAS:
        e = carregar(c).espelho()
        assert set(e) == set(ouro), c
        assert set(e["fonte"]) == set(ouro["fonte"])
        assert set(e["tempo"]) == set(ouro["tempo"])
        assert set(e["guardas"]) == set(ouro["guardas"])
        assert set(e["limites"]) == set(ouro["limites"])
        for bloco in ("visoes", "medidas"):
            assert set(e[bloco][0]) == set(ouro[bloco][0]), (c, bloco)


def test_exemplo_dourado_igual_ao_do_portal_quando_ele_esta_ao_lado():
    alvo = os.environ.get("QUANTILICA_PORTAL_DIR")
    portal = Path(alvo) if alvo else ROOT.parent / "quantilica-portal"
    fixture = portal / "tests" / "fixtures" / "publicacao_exemplo.json"
    if not fixture.is_file():
        pytest.skip(
            "quantilica-portal ao lado não tem tests/fixtures/publicacao_exemplo.json"
        )
    assert fixture.read_bytes() == (PUBLICACAO / "_exemplo.json").read_bytes(), (
        "publicacao/_exemplo.json e tests/fixtures/publicacao_exemplo.json do portal "
        "divergiram: regrave os dois do mesmo espelho"
    )


# --- notas condicionais -------------------------------------------------------------


def test_dfp_tem_a_nota_do_exercicio_fora_de_31_12_como_condicional():
    d = carregar(PUBLICACAO / "cvm" / "dfp" / "conjunto.toml")
    assert d.notas == ()  # nada fixo: o aviso só aparece quando o corte o merece
    (nota,) = d.espelho()["notas_condicionais"]
    assert nota["quando"] == {
        "tipo": "atributo",
        "id": "encerramento",
        "operador": "diferente_de",
        "valor": "12-31",
    }
    assert nota["substantivo"] == ["companhia", "companhias"]
    assert nota["texto"].startswith(
        "Exercício social que não fecha em 31/12: encerrado em "
    )
    assert "{valores}" in nota["texto"]


def test_caged_leva_a_nota_de_preliminar_como_oracao_que_completa_a_frase():
    d = carregar(PUBLICACAO / "pdet" / "caged" / "conjunto.toml")
    assert d.notas_condicionais == ()
    assert d.preliminar.nota == "ainda recebem movimentações fora do prazo e exclusões."


def test_exemplo_exercita_a_nota_condicional_com_e_sem_marcador():
    d = carregar(EXEMPLO)
    assert [n.quando.tipo for n in d.notas_condicionais] == ["atributo", "dimensao"]
    assert "{n}" in d.notas_condicionais[0].texto
    assert d.notas_condicionais[0].substantivo == ("território", "territórios")
    assert d.notas_condicionais[1].substantivo is None


# --- repositório público -------------------------------------------------------------

_TERMOS_INTERNOS = re.compile(
    r"(?i)\b(fedora|vps|pendulograph|drive|rclone|cron|crontab|systemd|cloudflare)\b"
)


def test_catalogo_nao_cita_termos_de_operacao_interna():
    for arq in sorted(PUBLICACAO.rglob("*")):
        if arq.is_file() and arq.suffix in {".toml", ".sql", ".md", ".json", ".csv"}:
            achado = _TERMOS_INTERNOS.search(arq.read_text(encoding="utf-8"))
            assert achado is None, (
                f"{arq.relative_to(ROOT)}: termo interno {achado.group(0)!r}"
            )
