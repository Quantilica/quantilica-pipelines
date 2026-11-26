# ruff: noqa: E501
"""DDL das tabelas de dados de um conjunto publicado, gerada da declaração espelhada.

ADR de 25/11/2026 (D2): cada visão de um conjunto tem **uma tabela física**
``publicacao.c_<fonte>_<conjunto>_<nivel>``, fora do Alembic. A forma da tabela vem só da
declaração (``publicacao.conjunto.declaracao``, o espelho de ``Declaracao.espelho()``):

    entidade text, periodo date,
    d_<dimensão> text (uma por dimensão), a_<atributo> <tipo> (uma por atributo),
    m_<medida> <bigint | double precision | numeric> (uma por medida);
    PRIMARY KEY (entidade, periodo, d_...);  índice (periodo, entidade).

O DDL sai dos construtores do SQLAlchemy (``Table``, ``Column``, ``CreateTable``,
``CreateIndex``): nenhum nome é colado em texto. Os nomes ainda passam, aqui, pelo padrão
do validador da declaração, de modo que um JSONB adulterado não vira DDL.

**Quem chama.** Nunca o portal em tempo de requisição. O portal só *lê* estas tabelas (e só
importa deste módulo os padrões de nome, ``RE_NOME`` e ``RE_TABELA``). Quem as cria é o
carregador da estação de coleta: cria a tabela nova com
``sql_criar_tabela(espelho, nivel, nome=<nome temporário>)``, copia os dados com ``COPY`` nas
colunas de ``colunas_da_tabela`` e troca por ``RENAME``.

**De quem é este arquivo.** Deste repositório (``quantilica-pipelines``), ao lado das
declarações e do validador. O portal guarda uma cópia idêntica byte a byte em
``quantilica_portal/core/publicacao_ddl.py`` (ele só pode importar o que está no próprio
pacote) e um teste dele falha se as duas divergirem: edite aqui e copie para lá. O mesmo vale
para ``publicacao_registro.sql`` (o DDL do registro, da migração ``p137`` do portal).

**Por que este arquivo é autocontido.** O carregador roda fora do app do portal e o portal
não importa nada daqui além da cópia. Este módulo só importa a biblioteca padrão e o
SQLAlchemy e não importa nada de ``quantilica_portal`` nem do validador: é carregado pelo
caminho do arquivo (``importlib.util.spec_from_file_location``). A regra de forma da tabela
mora só aqui.

Nomes de índice e de restrição derivam do nome da tabela **usado na criação**. Como o
carregador cria a tabela com um nome temporário e a renomeia, ele deve usar um nome
temporário diferente a cada carga (um sufixo com a hora, por exemplo): os índices
guardam o nome da criação e uma segunda carga com o mesmo nome temporário esbarraria no
índice da tabela já publicada.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Double,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    Table,
    Text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.types import TypeEngine

#: Schema das tabelas de dados e do registro.
SCHEMA = "publicacao"

#: Nome de coluna, medida, dimensão e atributo (o padrão do validador da declaração).
RE_NOME = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
#: Nome de tabela gerada (ou temporária da carga): ``c_...``, no máximo 63 caracteres.
RE_TABELA = re.compile(r"^c_[a-z][a-z0-9_]{0,60}$")
#: Nível da visão (``UF``, ``MUN``, ``CIA``...).
RE_NIVEL = re.compile(r"^[A-Z][A-Z0-9]{0,11}$")

#: Limite de um identificador do Postgres.
MAX_IDENTIFICADOR = 63

_TIPO_DA_MEDIDA: dict[str, TypeEngine[Any]] = {
    "bigint": BigInteger(),
    "double": Double(),
    "numeric": Numeric(),
}
_TIPO_DO_ATRIBUTO: dict[str, TypeEngine[Any]] = {
    "text": Text(),
    "date": Date(),
    "boolean": Boolean(),
    "integer": Integer(),
}


def nome_indice_periodo(tabela: str) -> str:
    """Nome do índice ``(periodo, entidade)``, dentro do limite do Postgres."""
    nome = f"ix_{tabela}_pe"
    if len(nome) <= MAX_IDENTIFICADOR:
        return nome
    resumo = hashlib.sha1(tabela.encode()).hexdigest()[:8]
    return f"{tabela[:44]}_{resumo}_pe"


def _nomes(blocos: Any, onde: str) -> list[str]:
    ids: list[str] = []
    for bloco in blocos or []:
        valor = bloco.get("id") if isinstance(bloco, Mapping) else None
        if not isinstance(valor, str) or not RE_NOME.fullmatch(valor):
            raise ValueError(f"{onde}: id inválido {valor!r}")
        ids.append(valor)
    if len(set(ids)) != len(ids):
        raise ValueError(f"{onde}: ids repetidos")
    return ids


def _visao(espelho: Mapping[str, Any], nivel: str) -> Mapping[str, Any]:
    if not isinstance(nivel, str) or not RE_NIVEL.fullmatch(nivel):
        raise ValueError(f"nível inválido: {nivel!r}")
    for v in espelho.get("visoes") or []:
        if isinstance(v, Mapping) and v.get("nivel") == nivel:
            return v
    raise ValueError(f"visão {nivel!r} não existe em {espelho.get('id')!r}")


def _nome_da_tabela(visao: Mapping[str, Any], nome: str | None) -> str:
    tabela = nome if nome is not None else visao.get("tabela")
    if not isinstance(tabela, str) or not RE_TABELA.fullmatch(tabela):
        raise ValueError(f"nome de tabela inválido: {tabela!r}")
    return tabela


def colunas_da_tabela(espelho: Mapping[str, Any], nivel: str) -> list[str]:
    """Nomes das colunas, na ordem do DDL (a do ``COPY`` do carregador)."""
    _visao(espelho, nivel)
    return [
        "entidade",
        "periodo",
        *(f"d_{i}" for i in _nomes(espelho.get("dimensoes"), "dimensoes")),
        *(f"a_{i}" for i in _nomes(espelho.get("atributos"), "atributos")),
        *(f"m_{i}" for i in _nomes(espelho.get("medidas"), "medidas")),
    ]


def tabela_de_dados(
    espelho: Mapping[str, Any],
    nivel: str,
    *,
    nome: str | None = None,
    metadata: MetaData | None = None,
) -> Table:
    """A ``Table`` do SQLAlchemy da visão ``nivel`` (nome da declaração ou ``nome``).

    Chave primária ``(entidade, periodo, dimensões...)`` e índice ``(periodo, entidade)``.
    Uma declaração sem medida é inválida (a tabela serviria para nada).
    """
    visao = _visao(espelho, nivel)
    tabela = _nome_da_tabela(visao, nome)
    dimensoes = _nomes(espelho.get("dimensoes"), "dimensoes")
    atributos = espelho.get("atributos") or []
    medidas = espelho.get("medidas") or []
    _nomes(atributos, "atributos")
    _nomes(medidas, "medidas")
    if not medidas:
        raise ValueError(f"{espelho.get('id')!r} não declara medida")

    colunas: list[Column[Any]] = [
        Column("entidade", Text(), nullable=False),
        Column("periodo", Date(), nullable=False),
    ]
    colunas += [Column(f"d_{i}", Text(), nullable=False) for i in dimensoes]
    for a in atributos:
        tipo = _TIPO_DO_ATRIBUTO.get(a.get("tipo", "text"))
        if tipo is None:
            raise ValueError(
                f"atributo {a['id']!r}: tipo {a.get('tipo')!r} desconhecido"
            )
        colunas.append(Column(f"a_{a['id']}", tipo, nullable=True))
    for m in medidas:
        tipo = _TIPO_DA_MEDIDA.get(m.get("tipo"))
        if tipo is None:
            raise ValueError(f"medida {m['id']!r}: tipo {m.get('tipo')!r} desconhecido")
        colunas.append(Column(f"m_{m['id']}", tipo, nullable=True))

    t = Table(
        tabela,
        metadata or MetaData(),
        *colunas,
        PrimaryKeyConstraint("entidade", "periodo", *(f"d_{i}" for i in dimensoes)),
        schema=SCHEMA,
    )
    Index(nome_indice_periodo(tabela), t.c.periodo, t.c.entidade)
    return t


def sql_criar_tabela(
    espelho: Mapping[str, Any], nivel: str, *, nome: str | None = None
) -> list[str]:
    """Instruções (``CREATE TABLE`` e ``CREATE INDEX``) para o Postgres, sem ``;``."""
    t = tabela_de_dados(espelho, nivel, nome=nome)
    dialeto = postgresql.dialect()
    instrucoes = [str(CreateTable(t).compile(dialect=dialeto))]
    instrucoes += [
        str(CreateIndex(ix).compile(dialect=dialeto))
        for ix in sorted(t.indexes, key=lambda i: i.name or "")
    ]
    return [" ".join(i.split()) for i in instrucoes]


def sql_criar_tabelas(
    espelho: Mapping[str, Any], *, niveis: Sequence[str] | None = None
) -> dict[str, list[str]]:
    """``sql_criar_tabela`` de cada visão (ou só das de ``niveis``), por nível."""
    todos = [v["nivel"] for v in espelho.get("visoes") or []]
    return {n: sql_criar_tabela(espelho, n) for n in (niveis or todos)}
