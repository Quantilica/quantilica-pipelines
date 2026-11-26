# ruff: noqa: E501
"""consulta.py: executa as consultas de uma declaração sobre o lake (DuckDB).

Pedaço de execução que o validador (`declaracao.py`, só biblioteca padrão) não tem: monta os
parâmetros das entradas, materializa o `preparo` como a tabela temporária `base` e roda a
consulta de cada visão. Usado pelos testes das declarações e, depois, pelo carregador.

Os caminhos do lake entram só como parâmetro nomeado (`$entrada`), nunca no texto da SQL.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .declaracao import (
    TIPOS_AUDITORIA,
    Declaracao,
    Visao,
    ler_correcoes,
    parametros_sql,
)

#: Nome fixo da tabela temporária criada pelo `preparo`.
TABELA_BASE = "base"
#: Nome fixo da tabela temporária das correções (do CSV declarado em `correcoes`).
TABELA_CORRECOES = "correcoes"

_RE_MEMORIA = re.compile(
    r"^\d+(\.\d+)?\s?(KB|MB|GB|TB|KiB|MiB|GiB|TiB|%)$", re.IGNORECASE
)


def _lit(texto: str) -> str:
    return "'" + str(texto).replace("'", "''") + "'"


@contextmanager
def conexao_do_lake(
    lake: Path,
    *,
    threads: int = 4,
    memoria: str = "4GB",
    temp: Path | None = None,
) -> Iterator[Any]:
    """Conexão DuckDB que só enxerga o lake e a pasta temporária (defesa em profundidade).

    O validador da declaração é um filtro de sanidade, não um sandbox; esta é a barreira de
    verdade: depois de abrir, o DuckDB não lê nem escreve fora de `allowed_directories`
    (`FROM ('/fora/x.csv')`, `read_text('/proc/self/environ')`, `COPY ... TO`, `ATTACH` e
    URLs dão `Permission Error`), não baixa nem carrega extensões e a configuração fica
    travada (`SET enable_external_access = true` falha). `threads` e `memory_limit` são
    explícitos. A pasta temporária (derrame em disco) entra nos diretórios permitidos; sem
    `temp`, cria uma e a remove ao sair.
    """
    import duckdb

    if not _RE_MEMORIA.fullmatch(str(memoria).strip()):
        raise ValueError(f"memory_limit inválido: {memoria!r}")
    criada: Path | None = None
    if temp is None:
        criada = Path(tempfile.mkdtemp(prefix="quantilica-duckdb-"))
        temp = criada
    else:
        temp = Path(temp)
        temp.mkdir(parents=True, exist_ok=True)
    lake = Path(lake)
    permitidos: list[str] = []
    for p in (lake, lake.resolve(), temp, temp.resolve()):
        if str(p) not in permitidos:
            permitidos.append(str(p))
    con = duckdb.connect()
    try:
        con.execute(f"SET threads = {int(threads)}")
        con.execute(f"SET memory_limit = {_lit(str(memoria).strip())}")
        con.execute(f"SET temp_directory = {_lit(str(temp))}")
        # ordem: a lista de diretórios antes de fechar o acesso externo; o travamento por último
        con.execute(
            f"SET allowed_directories = [{', '.join(_lit(p) for p in permitidos)}]"
        )
        con.execute("SET enable_external_access = false")
        con.execute("SET autoinstall_known_extensions = false")
        con.execute("SET autoload_known_extensions = false")
        con.execute("SET lock_configuration = true")
        yield con
    finally:
        con.close()
        if criada is not None:
            shutil.rmtree(criada, ignore_errors=True)


def parametros(
    decl: Declaracao, lake: Path, usados: set[str] | None = None
) -> dict[str, str]:
    """`{nome: caminho absoluto}` das entradas (só as `usados`, se dadas)."""
    return {
        e.nome: f"{lake}/{e.glob}"
        for e in decl.entradas
        if usados is None or e.nome in usados
    }


def ler_sqls(pasta: Path, decl: Declaracao) -> dict[str, str]:
    """Texto de cada `.sql` que a declaração cita, lido da pasta do `conjunto.toml`."""
    nomes = {v.consulta for v in decl.visoes} | {
        v.descartes for v in decl.visoes if v.descartes
    }
    if decl.preparo:
        nomes.add(decl.preparo)
    if decl.auditoria:
        nomes.add(decl.auditoria)
    if decl.correcoes:
        nomes.add(decl.correcoes)
    return {n: (pasta / n).read_text(encoding="utf-8") for n in sorted(nomes)}


def _executar(con: Any, sql: str, decl: Declaracao, lake: Path) -> Any:
    usados = parametros_sql(sql)
    return con.execute(sql, parametros(decl, lake, usados))


def carregar_correcoes(con: Any, decl: Declaracao, sqls: dict[str, str]) -> int:
    """Cria a tabela temporária `correcoes` com as linhas do CSV declarado (0 se não há).

    O CSV é validado (`ler_correcoes`) e as linhas entram por parâmetro: o DuckDB nunca lê o
    arquivo, então o sandbox (`allowed_directories`) e o validador de SQL ficam como estão.
    Colunas de chave são texto; `valor` é DOUBLE; `data` é DATE.
    """
    if not decl.correcoes:
        return 0
    tabela, erros = ler_correcoes(sqls[decl.correcoes])
    if tabela is None:
        raise ValueError(f"{decl.correcoes}: " + "; ".join(erros))
    tipos = {"valor": "DOUBLE", "data": "DATE"}
    colunas = ", ".join(f'"{c}" {tipos.get(c, "VARCHAR")}' for c in tabela.colunas)
    con.execute(f"CREATE OR REPLACE TEMP TABLE {TABELA_CORRECOES} ({colunas})")
    if tabela.linhas:
        marcas = ", ".join("?" * len(tabela.colunas))
        con.executemany(
            f"INSERT INTO {TABELA_CORRECOES} VALUES ({marcas})",
            [list(linha) for linha in tabela.linhas],
        )
    return len(tabela.linhas)


def auditar(
    con: Any, decl: Declaracao, sqls: dict[str, str], lake: Path
) -> list[tuple[str, str, str]]:
    """Roda a consulta `auditoria` (depois de `preparar`): `[(tipo, chave, detalhe)]`.

    O contrato são três colunas de texto, `tipo` (um de `TIPOS_AUDITORIA`), `chave` e
    `detalhe`; é auditoria do desempate e das correções, nunca dado servido.
    """
    if not decl.auditoria:
        return []
    cur = _executar(con, sqls[decl.auditoria], decl, lake)
    nomes = [d[0] for d in cur.description]
    if nomes != ["tipo", "chave", "detalhe"]:
        raise ValueError(
            f"{decl.id} ({decl.auditoria}): a auditoria deve devolver as colunas "
            f"tipo, chave, detalhe (veio {', '.join(nomes)})"
        )
    saida = [(str(t), str(c), str(d)) for t, c, d in cur.fetchall()]
    ruins = sorted({t for t, _, _ in saida} - set(TIPOS_AUDITORIA))
    if ruins:
        raise ValueError(
            f"{decl.id} ({decl.auditoria}): tipo de achado desconhecido: "
            f"{', '.join(ruins)} (aceitos: {', '.join(TIPOS_AUDITORIA)})"
        )
    return saida


def preparar(con: Any, decl: Declaracao, sqls: dict[str, str], lake: Path) -> None:
    """Cria a tabela temporária `correcoes` (do CSV) e `base` (do `preparo`), se houver."""
    carregar_correcoes(con, decl, sqls)
    if not decl.preparo:
        return
    _executar(
        con,
        f"CREATE OR REPLACE TEMP TABLE {TABELA_BASE} AS\n{sqls[decl.preparo]}",
        decl,
        lake,
    )


def executar_visao(
    con: Any,
    decl: Declaracao,
    visao: Visao,
    sqls: dict[str, str],
    lake: Path,
    *,
    descartes: bool = False,
) -> tuple[list[tuple[str, str]], list[tuple[Any, ...]]]:
    """Roda a consulta (ou os descartes) da visão: `([(coluna, tipo)], linhas)`.

    Chame `preparar` antes quando a declaração tem `preparo`.
    """
    arquivo = visao.descartes if descartes else visao.consulta
    cur = _executar(con, sqls[arquivo], decl, lake)
    colunas = [(d[0], str(d[1])) for d in cur.description]
    return colunas, cur.fetchall()
