# ruff: noqa: E501
"""Lake sintético (Parquet em pasta temporária) com os mesmos nomes e colunas do real.

Usado pelos testes das declarações em `publicacao/`. Todas as colunas são texto (como
as views do lake), salvo as que o próprio Parquet real traz com outro tipo.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def parquet(destino: Path, colunas: list[str], linhas: list[tuple]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE TABLE t ({', '.join(c + ' VARCHAR' for c in colunas)})")
    for linha in linhas:
        con.execute(
            f"INSERT INTO t VALUES ({','.join('?' * len(colunas))})", list(linha)
        )
    con.execute("COPY t TO '" + str(destino).replace("'", "''") + "' (FORMAT parquet)")
    con.close()


_CAGED_COLS = ["competenciamov", "uf", "municipio", "saldomovimentacao"]


def _mov(comp: str, uf: str, mun: str, saldo: str, n: int) -> list[tuple]:
    return [(comp, uf, mun, saldo)] * n


def montar_caged(lake: Path) -> None:
    """2026-05/06 em SP e RJ, com fora do prazo, exclusão e registros sem localização."""
    base = lake / "pdet"
    parquet(
        base / "caged-2020-mov/ano=2026/mes=05/m.parquet",
        _CAGED_COLS,
        _mov("202605", "35", "355030", "1", 5)
        + _mov("202605", "35", "355030", "-1", 2)
        + _mov("202605", "35", "350950", "1", 1)
        + _mov("202605", "33", "330455", "1", 2)
        + _mov("202605", "33", "330455", "-1", 3)
        + _mov("202605", "99", "999999", "1", 4),  # UF e município ignorados
    )
    parquet(
        base / "caged-2020-mov/ano=2026/mes=06/m.parquet",
        _CAGED_COLS,
        _mov("202606", "35", "355030", "1", 3)
        + _mov("202606", "35", "355030", "-1", 1)
        + _mov("202606", "33", "330455", "1", 1)
        + _mov("202606", "33", "330455", "-1", 1)
        + _mov("2026", "35", "355030", "1", 2)  # competência inválida
        + _mov("202606", "35", "35", "1", 1),  # município fora do padrão (UF válida)
    )
    # fora do prazo, declarado em 06, do evento de 05: SP/São Paulo +2 adm +1 des
    parquet(
        base / "caged-2020-for/ano=2026/mes=06/f.parquet",
        _CAGED_COLS,
        _mov("202605", "35", "355030", "1", 2)
        + _mov("202605", "35", "355030", "-1", 1),
    )
    # exclusão de 1 admissão de 05 em SP/São Paulo
    parquet(
        base / "caged-2020-exc/ano=2026/mes=06/e.parquet",
        _CAGED_COLS,
        _mov("202605", "35", "355030", "1", 1),
    )


_DFP_COLS = [
    "CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", "CD_CVM", "MOEDA", "ESCALA_MOEDA",
    "ORDEM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA",
]  # fmt: skip

ALFA = ("11.111.111/0001-11", "ALFA SA", "000001")
BETA = ("22.222.222/0001-22", "BETA SA", "000002")
BANCO = ("33.333.333/0001-33", "BANCO SA", "000003")
GAMA = ("44.444.444/0001-44", "GAMA SA", "000004")


def _dfp(
    emp, conta, ds, valor, *, ref="2024-12-31", versao="1", escala="MIL", ordem="ÚLTIMO"
):
    cnpj, nome, cd = emp
    return (cnpj, ref, versao, nome, cd, "REAL", escala, ordem, conta, ds, str(valor))


def montar_dfp(lake: Path) -> None:
    """DFP 2024: consolidada vs individual, versões, escala, contas por setor, exercício em 30/06."""
    pasta = lake / "cvm" / "cia-dfp" / "ano=2024"

    def arq(kind: str) -> Path:
        return pasta / f"dfp_cia_aberta_2024__dfp_cia_aberta_{kind}_2024.parquet"

    parquet(
        arq("bpa_con"),
        _DFP_COLS,
        [
            _dfp(ALFA, "1", "Ativo Total", 1000),
            _dfp(ALFA, "1", "Ativo Total", 900, ordem="PENÚLTIMO"),
            _dfp(BANCO, "1", "Ativo Total", 7, escala="UNIDADE"),
        ],
    )
    parquet(
        arq("bpa_ind"),
        _DFP_COLS,
        [
            _dfp(ALFA, "1", "Ativo Total", 500),  # perde para a consolidada
            _dfp(BETA, "1", "Ativo Total", 50),
            _dfp(BETA, "1", "Ativo Total", 60, versao="2"),
            _dfp(
                BETA, "1", "Ativo Total", 70, ref="2024-06-30"
            ),  # encerramento mais antigo
            _dfp(
                GAMA, "1", "Ativo Total", 5, ref="2024-06-30"
            ),  # exercício que fecha em 30/06
        ],
    )
    parquet(
        arq("bpp_con"),
        _DFP_COLS,
        [
            _dfp(ALFA, "2.03", "Patrimônio Líquido Consolidado", 400),
            _dfp(ALFA, "2.03.01", "Capital Social Realizado", 99),
            _dfp(BANCO, "2.07", "Patrimônio Líquido Consolidado", 3, escala="UNIDADE"),
            _dfp(BANCO, "2.03", "Provisões", 8, escala="UNIDADE"),
        ],
    )
    parquet(
        arq("dre_con"),
        _DFP_COLS,
        [
            _dfp(ALFA, "3.01", "Receita de Venda de Bens e/ou Serviços", 800),
            _dfp(ALFA, "3.11", "Lucro/Prejuízo Consolidado do Período", 90),
            _dfp(ALFA, "3.99", "Lucro por Ação - (Reais / Ação)", 5),
        ],
    )
    parquet(
        arq("dre_ind"), _DFP_COLS, [_dfp(BETA, "3.11", "Lucro/Prejuízo do Período", 12)]
    )
    parquet(
        arq("dfc_mi_con"),
        _DFP_COLS,
        [_dfp(ALFA, "6.01", "Caixa Líquido Atividades Operacionais", 70)],
    )
    parquet(
        arq("dfc_md_ind"),
        _DFP_COLS,
        [_dfp(BETA, "6.01", "Caixa Líquido das Atividades Operacionais", 30)],
    )
    # demonstrações que a declaração não lê: não podem entrar
    parquet(arq("dmpl_con"), _DFP_COLS, [_dfp(ALFA, "1", "Ativo Total", 123456)])


_EXEMPLO_COLS = ["municipio", "uf", "data", "tipo", "vitimas", "preliminar"]


def montar_exemplo(lake: Path) -> None:
    """Dados do conjunto fictício `exemplo/sinistros`."""
    parquet(
        lake / "exemplo/sinistros/ano=2025/s.parquet",
        _EXEMPLO_COLS,
        [
            ("3550308", "SP", "2025-06-03", "fatal", "1", "false"),
            ("3550308", "SP", "2025-06-20", "fatal", "3", "false"),
            ("3550308", "SP", "2025-06-21", "nao_fatal", "0", "true"),
            ("3304557", "RJ", "2025-06-02", "fatal", "2", "false"),
            ("SEM", "RJ", "2025-06-05", "fatal", "1", "false"),  # município inválido
        ],
    )
