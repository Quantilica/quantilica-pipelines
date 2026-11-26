"""Descoberta, por varredura, das SQL do catálogo e do que cada uma lê.

Os testes de contrato (``test_ibge_contrato``, ``test_bcb_contrato``) nunca listam
arquivos à mão: usam as funções daqui, e ``test_catalogo_descoberta`` confere que a
varredura e as exclusões explícitas continuam coerentes quando o catálogo cresce.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_BLOCO = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINHA = re.compile(r"--[^\n]*")
_TEXTO = re.compile(r"'(?:[^']|'')*'")
_REF = re.compile(r"\b(?:FROM|JOIN)\s+(?:([A-Za-z_]\w*)\.)?([A-Za-z_]\w*)", re.I)

# Nomes, sem schema, que as SQL do IBGE leem: a superfície do ``sidra-sql`` legado,
# que o ``quantilica-sql`` mantém (``ibge_sidra.dados``, ``dimensao``, ``localidade``
# e ``periodo``), resolvida pelo ``search_path`` do runner.
SUPERFICIE_SIDRA = frozenset({"dados", "dimensao", "localidade", "periodo"})
# A tabela de observações do BCB SGS, também sem schema.
SUPERFICIE_BCB = frozenset({"series_data"})

# SQL de ``ibge/**`` que ficam FORA do contrato com o esquema do SIDRA: leem
# ``analytics.*``, os marts que o próprio catálogo materializa (e que não são destino
# de nenhum ``load``). A chave é o caminho relativo à raiz;
# o valor é o motivo, que o teste de descoberta confere contra a varredura.
FORA_DO_CONTRATO_SIDRA: dict[str, str] = {
    "ibge/populacao/populacao.sql": "lê analytics.* (marts removidos)",
    "ibge/precos/snipc/inflacao.sql": "lê analytics.* (marts removidos)",
    "ibge/precos/snipc/inflacao_difusao.sql": "lê analytics.* (marts removidos)",
    "ibge/precos/snipc/inflacao_hierarquia_subitem.sql": (
        "lê analytics.* (marts removidos)"
    ),
}


def sem_comentarios(texto: str) -> str:
    """Remove comentários e literais de texto (podem conter FROM/JOIN soltos)."""
    texto = _BLOCO.sub(" ", texto)
    texto = _LINHA.sub(" ", texto)
    return _TEXTO.sub("''", texto)


def referencias(path: Path) -> set[tuple[str | None, str]]:
    """``{(schema ou None, tabela)}`` lidos por FROM/JOIN, em minúsculas.

    Inclui os nomes das CTEs (``FROM base``): quem usa só filtra pelos conjuntos
    ``SUPERFICIE_*``, que as CTEs do catálogo não usam como nome.
    """
    texto = sem_comentarios(path.read_text(encoding="utf-8"))
    return {((s.lower() if s else None), t.lower()) for s, t in _REF.findall(texto)}


def sql_de(*pastas: str) -> list[Path]:
    """Todos os ``*.sql`` das pastas (relativas à raiz), em ordem estável."""
    achados: list[Path] = []
    for pasta in pastas:
        achados += (ROOT / pasta).rglob("*.sql")
    return sorted(achados)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def le_analytics(path: Path) -> bool:
    return any(s == "analytics" for s, _ in referencias(path))


def le_superficie(path: Path, superficie: frozenset[str]) -> bool:
    return any(s is None and t in superficie for s, t in referencias(path))


def sql_ibge_do_contrato() -> list[Path]:
    """SQL de ``ibge/**`` que leem a superfície do SIDRA e não estão excluídas."""
    return [
        p
        for p in sql_de("ibge")
        if le_superficie(p, SUPERFICIE_SIDRA) and rel(p) not in FORA_DO_CONTRATO_SIDRA
    ]


def sql_bcb_do_contrato() -> list[Path]:
    """SQL de ``macro/**`` e ``setorial/**`` que leem ``series_data``."""
    return [
        p
        for p in sql_de("macro", "setorial", "cross")
        if le_superficie(p, SUPERFICIE_BCB)
    ]


_JOIN_METADATA = re.compile(r"\bJOIN\s+series_metadata\s+(?:AS\s+)?(\w+)", re.I)


def colunas_de_series_metadata(path: Path) -> set[str]:
    """Colunas de ``series_metadata`` que a SQL lê pelo alias do JOIN (``sm.name``).

    Vazio se a SQL não junta ``series_metadata``. Colunas sem alias (de CTEs) não
    entram: só o que vem da tabela que o ``load bcb`` cria.
    """
    texto = sem_comentarios(path.read_text(encoding="utf-8"))
    colunas: set[str] = set()
    for alias in _JOIN_METADATA.findall(texto):
        colunas |= set(re.findall(rf"\b{alias}\.(\w+)", texto))
    return colunas


def usar_schema(conn, schema: str) -> None:
    """``search_path`` como o runner do ``quantilica-sql`` (origem, depois public)."""
    from psycopg import sql

    conn.execute(
        sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema))
    )
