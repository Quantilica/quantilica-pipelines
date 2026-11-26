#!/usr/bin/env python3
# ruff: noqa: E501
"""declaracao.py: validador da declaração de um conjunto tabular publicado.

Cumpre o ADR de 25/11/2026 ("Publicação genérica de dados tabulares no portal", D1).
Lê `conjunto.toml` (e as consultas `.sql` ao lado) do catálogo `publicacao/<fonte>/<conjunto>/`
do `quantilica-pipelines` e devolve uma `Declaracao` imutável, ou levanta `DeclaracaoInvalida`
com **todos** os erros de uma vez (um por linha, com o caminho do campo). A validação é
estrita: campo desconhecido é erro (com sugestão), tipo errado é erro, e nomes de tabela e
coluna só passam pelo padrão `^[a-z][a-z0-9_]{0,40}$`, de modo que o DDL gerado nunca recebe
texto de requisição.

Só biblioteca padrão (`tomllib`, `dataclasses`, `re`, `difflib`); o formato está documentado
em `quantilica-pipelines/publicacao/README.md`.

    python ferramentas/quantilica_publicacao/declaracao.py <pasta-ou-conjunto.toml>...

Pontos de entrada:

- `carregar(caminho)`: lê o `.toml` e os `.sql` e valida (levanta `DeclaracaoInvalida`);
- `validar(dados, sqls=...)`: o mesmo, a partir de dicionários (usado nos testes);
- `Declaracao.espelho()`: o JSON que vai para `publicacao.conjunto.declaracao` no portal
  (sem o layout do lake nem o texto das consultas);
- `colunas_esperadas(...)` e `conferir_colunas(...)`: o contrato de colunas da consulta;
- `tabelas_duplicadas(...)`: ids e nomes de tabela únicos num conjunto de declarações.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Versão do formato que este validador entende.
SCHEMA_VERSAO = 1

#: Nome de tabela, coluna, medida, dimensão e atributo (nunca vem de requisição).
RE_NOME = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
#: Segmento do id (`<fonte>/<slug>`): o que o QSID aceita como fonte e conjunto.
RE_SEGMENTO = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RE_NIVEL = re.compile(r"^[A-Z][A-Z0-9]{0,11}$")
RE_ARQUIVO_SQL = re.compile(r"^[a-z][a-z0-9_]{0,60}\.sql$")
RE_ARQUIVO_CSV = re.compile(r"^[a-z][a-z0-9_]{0,60}\.csv$")
RE_PARAMETRO = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
RE_VALOR_DIMENSAO = re.compile(r"^[A-Za-z0-9_.\-]{1,40}$")
RE_GLOB = re.compile(r"^[A-Za-z0-9_.=*?\[\]/\-]+$")
RE_CATALOGO = re.compile(r"^[a-z][a-z0-9-]*/[a-z0-9][a-z0-9._-]*$")

ESTADOS = ("rascunho", "publicado", "aposentado")
REDISTRIBUICOES = ("livre", "restrita")
TIPOS_ENTIDADE = ("territorio", "identificador")
TIPOS_TEMPO = ("dia", "mes", "trimestre", "ano")
FREQUENCIA_DO_TEMPO = {
    "dia": "daily",
    "mes": "monthly",
    "trimestre": "quarterly",
    "ano": "yearly",
}
ALINHAMENTOS = ("inicio", "fim")
PADROES_TEMPO = ("ultimo", "ultimo_com_cobertura")
TIPOS_MEDIDA = ("bigint", "double", "numeric")
TIPOS_ATRIBUTO = ("text", "date", "boolean", "integer")

#: Nota condicional (emenda de 26/11/2026 ao ADR): conjunto pequeno e fechado de operadores
#: e de marcadores. Acrescentar um item exige emenda ao ADR, não um campo avulso.
OPERADORES_NOTA = ("igual_a", "diferente_de")
MARCADORES_NOTA = ("n", "valores")
_RE_MARCADOR = re.compile(r"\{([^{}]*)\}")
_RE_MES_DIA = re.compile(r"^(\d{2})-(\d{2})$")

#: Níveis e chaves que o portal sabe ligar ao mapa (`dim.geo_*`).
CHAVES_DO_NIVEL = {
    "UF": ("sigla",),
    "MUN": ("ibge6", "ibge7"),
    "REGIAO": ("ibge1",),
}

#: Qualifiers que a gramática do QSID já usa; uma dimensão não pode ter esses nomes.
QUALIFIERS_RESERVADOS = frozenset(
    {"tempo", "periodo", "entidade", "snapshot", "geo", "limit", "format"}
)

#: Limites padrão e teto duro de cada limite (ADR D2 e D4). O teto não se negocia na
#: declaração: acima dele o ADR precisa ser emendado.
LIMITES_PADRAO = {
    "max_linhas_cs": 10_000,
    "max_entidades_painel": 50,
    "max_linhas_painel": 100_000,
    "max_linhas_tabela": 1_000_000,
}
LIMITES_TETO = {
    "max_linhas_cs": 10_000,
    "max_entidades_painel": 50,
    "max_linhas_painel": 100_000,
    "max_linhas_tabela": 5_000_000,
}

#: Tamanho máximo de um identificador de tabela do Postgres.
MAX_NOME_TABELA = 63

_RE_PERIODO = {
    "dia": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "mes": re.compile(r"^\d{4}-\d{2}$"),
    "trimestre": re.compile(r"^\d{4}-T[1-4]$"),
    "ano": re.compile(r"^\d{4}$"),
}
_FORMATO_PERIODO = {
    "dia": "AAAA-MM-DD",
    "mes": "AAAA-MM",
    "trimestre": "AAAA-T1 a AAAA-T4",
    "ano": "AAAA",
}

#: Licença que restringe obra derivada (por exemplo CC BY-ND): exige `parecer_licenca`.
_RE_LICENCA_SEM_DERIVACAO = re.compile(
    r"(?i)(\bND\b|sem[\s-]+deriva|no[\s-]?deriv|noderiv)"
)


class DeclaracaoInvalida(ValueError):
    """A declaração não passa na validação; `erros` traz cada problema, um por item."""

    def __init__(self, erros: Sequence[str], origem: str = "") -> None:
        self.erros = list(erros)
        self.origem = origem
        cabeca = f"declaração inválida{f' ({origem})' if origem else ''}:"
        super().__init__("\n".join([cabeca, *(f"  - {e}" for e in self.erros)]))


# --- modelo ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Parecer:
    data: str
    por: str
    nota: str = ""


@dataclass(frozen=True, slots=True)
class Fonte:
    orgao: str
    licenca: str
    atribuicao: str
    redistribuicao: str
    url: str = ""
    parecer_licenca: Parecer | None = None


@dataclass(frozen=True, slots=True)
class Entidade:
    tipo: str
    rotulo: str
    qualifier: str
    chaves_alternativas: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Entrada:
    """Parquet do lake que a consulta lê: `$nome` na SQL, `glob` relativo à raiz do lake."""

    nome: str
    glob: str


@dataclass(frozen=True, slots=True)
class Visao:
    nivel: str
    consulta: str
    cabecalhos: tuple[str, str]
    chave: str = ""
    descartes: str = ""


@dataclass(frozen=True, slots=True)
class Tempo:
    tipo: str
    frequencia: str
    alinhamento_painel: str
    padrao: str
    fracao: float | None = None


@dataclass(frozen=True, slots=True)
class Medida:
    id: str
    rotulo: str
    unidade: str
    tipo: str
    aditiva: bool = False
    descricao: str = ""
    nota: str = ""


@dataclass(frozen=True, slots=True)
class Dimensao:
    id: str
    rotulo: str
    valores: tuple[str, ...] = ()
    padrao: str = ""


@dataclass(frozen=True, slots=True)
class Atributo:
    id: str
    rotulo: str
    tipo: str


@dataclass(frozen=True, slots=True)
class Preliminar:
    ultimos_periodos: int
    nota: str


#: Colunas obrigatórias do CSV de correções (as demais são a chave da célula corrigida).
COLUNAS_FIXAS_CORRECOES = ("valor", "referencia", "motivo", "data")
MAX_CORRECOES = 500
#: Tipos do achado que a consulta `auditoria` devolve.
TIPOS_AUDITORIA = ("ambigua", "correcao_aplicada", "correcao_sem_efeito")


@dataclass(frozen=True, slots=True)
class Correcoes:
    """Tabela de correções lida do CSV: `chaves` (texto), `valor`, `referencia`, `motivo`, `data`."""

    chaves: tuple[str, ...]
    linhas: tuple[tuple[Any, ...], ...]  # na ordem `colunas`

    @property
    def colunas(self) -> tuple[str, ...]:
        return (*self.chaves, *COLUNAS_FIXAS_CORRECOES)


@dataclass(frozen=True, slots=True)
class Condicao:
    """`quando` de uma nota condicional: um atributo ou dimensão, um operador, um valor.

    `valor` tem o formato do tipo do alvo: `MM-DD` (dia e mês, sem ano) para atributo
    `date`, booleano, inteiro ou texto; para dimensão, um dos `valores` declarados.
    """

    tipo: str  # "atributo" ou "dimensao"
    id: str
    operador: str
    valor: str | bool | int


@dataclass(frozen=True, slots=True)
class NotaCondicional:
    """Texto que o leitor só inclui se alguma linha do corte satisfaz `quando`."""

    texto: str
    quando: Condicao
    #: `(singular, plural)` do que `{n}` e `{valores}` contam (opcional)
    substantivo: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class Limites:
    max_linhas_cs: int = LIMITES_PADRAO["max_linhas_cs"]
    max_entidades_painel: int = LIMITES_PADRAO["max_entidades_painel"]
    max_linhas_painel: int = LIMITES_PADRAO["max_linhas_painel"]
    max_linhas_tabela: int = LIMITES_PADRAO["max_linhas_tabela"]


@dataclass(frozen=True, slots=True)
class Guardas:
    queda_maxima_linhas: float = 0.10
    periodos_nao_somem: bool = True
    periodos_continuos: bool = False
    periodo_inicial: str = ""
    cobertura_minima_entidades: int | None = None
    queda_maxima_entidades_por_periodo: float | None = None
    revisao_maxima_total: float | None = None
    revisao_medidas: tuple[str, ...] = ()
    #: queda máxima dos valores NÃO NULOS de cada medida por período já carregado (uma
    #: medida que esvazia passa pela soma e pela revisão do total; a contagem pega). Não vai
    #: no espelho: é regra do carregador, o portal não a lê.
    queda_maxima_valores: float = 0.10


@dataclass(frozen=True, slots=True)
class Conferencia:
    nivel: str
    medida: str
    periodo: str
    valor: float | int
    tolerancia_relativa: float
    referencia: str
    entidade: str = ""
    #: fixa o valor de cada dimensão citada (`{tipo = "fatal"}`); sem ela, soma todos
    dimensoes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Declaracao:
    schema_versao: int
    id: str
    titulo: str
    descricao: str
    estado: str
    fonte: Fonte
    entidade: Entidade
    tempo: Tempo
    entradas: tuple[Entrada, ...]
    visoes: tuple[Visao, ...]
    medidas: tuple[Medida, ...]
    titulo_curto: str = ""
    catalogo: str = ""
    preparo: str = ""
    #: CSV de correções (vira a tabela temporária `correcoes`) e a consulta que audita o
    #: desempate e as correções (`tipo`, `chave`, `detalhe`); ver o README do formato
    correcoes: str = ""
    auditoria: str = ""
    dimensoes: tuple[Dimensao, ...] = ()
    atributos: tuple[Atributo, ...] = ()
    notas: tuple[str, ...] = ()
    notas_condicionais: tuple[NotaCondicional, ...] = ()
    preliminar: Preliminar | None = None
    limites: Limites = field(default_factory=Limites)
    guardas: Guardas = field(default_factory=Guardas)
    conferencias: tuple[Conferencia, ...] = ()

    @property
    def fonte_id(self) -> str:
        return self.id.partition("/")[0]

    @property
    def slug(self) -> str:
        return self.id.partition("/")[2]

    def visao(self, nivel: str) -> Visao:
        for v in self.visoes:
            if v.nivel == nivel:
                return v
        raise KeyError(f"visão {nivel!r} não existe em {self.id}")

    def tabela(self, visao: Visao | str) -> str:
        """Nome da tabela gerada (`c_<fonte>_<slug>_<nivel>`), no schema `publicacao`."""
        nivel = visao.nivel if isinstance(visao, Visao) else visao
        return nome_tabela(self.id, nivel)

    def espelho(self) -> dict[str, Any]:
        """O JSON de `publicacao.conjunto.declaracao`: tudo menos o layout do lake e as SQL."""
        f = self.fonte
        fonte: dict[str, Any] = {
            "orgao": f.orgao,
            "licenca": f.licenca,
            "atribuicao": f.atribuicao,
            "redistribuicao": f.redistribuicao,
            "url": f.url or None,
            "parecer_licenca": None
            if f.parecer_licenca is None
            else {
                "data": f.parecer_licenca.data,
                "por": f.parecer_licenca.por,
                "nota": f.parecer_licenca.nota or None,
            },
        }
        t = self.tempo
        g = self.guardas
        return {
            "schema_versao": self.schema_versao,
            "id": self.id,
            "fonte_id": self.fonte_id,
            "slug": self.slug,
            "titulo": self.titulo,
            "titulo_curto": self.titulo_curto or self.titulo,
            "descricao": self.descricao,
            "estado": self.estado,
            "catalogo": self.catalogo or None,
            "fonte": fonte,
            "entidade": {
                "tipo": self.entidade.tipo,
                "rotulo": self.entidade.rotulo,
                "qualifier": self.entidade.qualifier,
                "chaves_alternativas": list(self.entidade.chaves_alternativas),
            },
            "visoes": [
                {
                    "nivel": v.nivel,
                    "tabela": self.tabela(v),
                    "chave": v.chave or None,
                    "cabecalhos": list(v.cabecalhos),
                }
                for v in self.visoes
            ],
            "tempo": {
                "tipo": t.tipo,
                "frequencia": t.frequencia,
                "alinhamento_painel": t.alinhamento_painel,
                "padrao": t.padrao,
                "fracao": t.fracao,
            },
            "medidas": [
                {
                    "id": m.id,
                    "rotulo": m.rotulo,
                    "descricao": m.descricao or None,
                    "unidade": m.unidade,
                    "tipo": m.tipo,
                    "aditiva": m.aditiva,
                    "nota": m.nota or None,
                }
                for m in self.medidas
            ],
            "dimensoes": [
                {
                    "id": d.id,
                    "rotulo": d.rotulo,
                    "valores": list(d.valores) or None,
                    "padrao": d.padrao or None,
                }
                for d in self.dimensoes
            ],
            "atributos": [
                {"id": a.id, "rotulo": a.rotulo, "tipo": a.tipo} for a in self.atributos
            ],
            "notas": list(self.notas),
            # sempre presente (lista vazia sem nota condicional): a forma do espelho não
            # depende de a declaração usar o campo
            "notas_condicionais": [
                {
                    "texto": n.texto,
                    "quando": {
                        "tipo": n.quando.tipo,
                        "id": n.quando.id,
                        "operador": n.quando.operador,
                        "valor": n.quando.valor,
                    },
                    "substantivo": list(n.substantivo) if n.substantivo else None,
                }
                for n in self.notas_condicionais
            ],
            "preliminar": None
            if self.preliminar is None
            else {
                "ultimos_periodos": self.preliminar.ultimos_periodos,
                "nota": self.preliminar.nota,
            },
            "limites": {
                "max_linhas_cs": self.limites.max_linhas_cs,
                "max_entidades_painel": self.limites.max_entidades_painel,
                "max_linhas_painel": self.limites.max_linhas_painel,
                "max_linhas_tabela": self.limites.max_linhas_tabela,
            },
            "guardas": {
                "queda_maxima_linhas": g.queda_maxima_linhas,
                "periodos_nao_somem": g.periodos_nao_somem,
                "periodos_continuos": g.periodos_continuos,
                "periodo_inicial": g.periodo_inicial or None,
                "cobertura_minima_entidades": g.cobertura_minima_entidades,
                "queda_maxima_entidades_por_periodo": g.queda_maxima_entidades_por_periodo,
                "revisao_maxima_total": g.revisao_maxima_total,
                "revisao_medidas": list(g.revisao_medidas),
            },
            "conferencias": [
                {
                    "nivel": c.nivel,
                    "medida": c.medida,
                    "periodo": c.periodo,
                    "entidade": c.entidade or None,
                    "valor": c.valor,
                    "tolerancia_relativa": c.tolerancia_relativa,
                    "referencia": c.referencia,
                    # a chave só existe quando a conferência fixa dimensões (o exemplo
                    # dourado do contrato com o portal não muda)
                    **({"dimensoes": dict(c.dimensoes)} if c.dimensoes else {}),
                }
                for c in self.conferencias
            ],
        }


def nome_tabela(conjunto_id: str, nivel: str) -> str:
    """`pdet/caged` + `UF` -> `c_pdet_caged_uf` (hífen do id vira sublinhado)."""
    fonte, _, slug = conjunto_id.partition("/")
    return f"c_{fonte}_{slug}_{nivel.lower()}".replace("-", "_")


# --- ajudantes de validação -------------------------------------------------------


class _Erros:
    def __init__(self) -> None:
        self.itens: list[str] = []

    def add(self, caminho: str, mensagem: str) -> None:
        self.itens.append(f"{caminho}: {mensagem}" if caminho else mensagem)


def _sugestao(nome: str, validos: Iterable[str]) -> str:
    perto = difflib.get_close_matches(nome, list(validos), n=1, cutoff=0.6)
    return f" (você quis dizer {perto[0]!r}?)" if perto else ""


def _tabela(
    e: _Erros,
    dados: Any,
    caminho: str,
    permitidas: Sequence[str],
    obrigatorias: Sequence[str] = (),
) -> dict[str, Any] | None:
    if not isinstance(dados, dict):
        e.add(caminho, f"esperava uma tabela, veio {_tipo(dados)}")
        return None
    for chave in dados:
        if chave not in permitidas:
            e.add(
                f"{caminho}.{chave}" if caminho else chave,
                f"campo desconhecido{_sugestao(str(chave), permitidas)}; "
                f"aceitos: {', '.join(permitidas)}",
            )
    for chave in obrigatorias:
        if chave not in dados:
            e.add(
                f"{caminho}.{chave}" if caminho else chave, "campo obrigatório ausente"
            )
    return dados


def _tipo(valor: Any) -> str:
    return {
        str: "texto",
        int: "inteiro",
        float: "número",
        bool: "booleano",
        list: "lista",
        dict: "tabela",
        dt.date: "data",
        dt.datetime: "data e hora",
    }.get(type(valor), type(valor).__name__)


def _texto(
    e: _Erros,
    d: dict[str, Any],
    chave: str,
    caminho: str,
    *,
    obrigatorio: bool = True,
    maximo: int = 1000,
    regex: re.Pattern[str] | None = None,
    dentre: Sequence[str] | None = None,
    padrao: str = "",
    formato: str = "",
) -> str:
    if chave not in d:
        return padrao
    caminho_campo = f"{caminho}.{chave}" if caminho else chave
    v = d[chave]
    if not isinstance(v, str):
        e.add(caminho_campo, f"esperava texto, veio {_tipo(v)}")
        return padrao
    v = v.strip()
    if not v and obrigatorio:
        e.add(caminho_campo, "texto vazio")
    elif len(v) > maximo:
        e.add(caminho_campo, f"texto com {len(v)} caracteres (máximo {maximo})")
    elif dentre is not None and v not in dentre:
        e.add(
            caminho_campo,
            f"valor {v!r} inválido{_sugestao(v, dentre)}; aceitos: {', '.join(dentre)}",
        )
    elif regex is not None and not regex.fullmatch(v):
        e.add(
            caminho_campo,
            f"{v!r} fora do padrão {formato or regex.pattern}",
        )
    return v


def _inteiro(
    e: _Erros,
    d: dict[str, Any],
    chave: str,
    caminho: str,
    *,
    minimo: int,
    maximo: int,
    padrao: int | None = None,
) -> int | None:
    if chave not in d:
        return padrao
    v = d[chave]
    caminho_campo = f"{caminho}.{chave}" if caminho else chave
    if isinstance(v, bool) or not isinstance(v, int):
        e.add(caminho_campo, f"esperava inteiro, veio {_tipo(v)}")
        return padrao
    if not minimo <= v <= maximo:
        e.add(caminho_campo, f"{v} fora do intervalo {minimo} a {maximo}")
        return padrao
    return v


def _numero(
    e: _Erros,
    d: dict[str, Any],
    chave: str,
    caminho: str,
    *,
    minimo: float | None = None,
    maximo: float | None = None,
    minimo_aberto: bool = False,
    maximo_aberto: bool = False,
    padrao: float | None = None,
) -> float | None:
    if chave not in d:
        return padrao
    v = d[chave]
    caminho_campo = f"{caminho}.{chave}" if caminho else chave
    if isinstance(v, bool) or not isinstance(v, int | float):
        e.add(caminho_campo, f"esperava número, veio {_tipo(v)}")
        return padrao
    abaixo = minimo is not None and (v <= minimo if minimo_aberto else v < minimo)
    acima = maximo is not None and (v >= maximo if maximo_aberto else v > maximo)
    if abaixo or acima:
        lo = "" if minimo is None else f"{'>' if minimo_aberto else '>='} {minimo}"
        hi = "" if maximo is None else f"{'<' if maximo_aberto else '<='} {maximo}"
        e.add(
            caminho_campo,
            f"{v} fora do intervalo ({' e '.join(x for x in (lo, hi) if x)})",
        )
        return padrao
    return float(v)


def _booleano(
    e: _Erros, d: dict[str, Any], chave: str, caminho: str, *, padrao: bool = False
) -> bool:
    if chave not in d:
        return padrao
    v = d[chave]
    if not isinstance(v, bool):
        e.add(
            f"{caminho}.{chave}" if caminho else chave,
            f"esperava true/false, veio {_tipo(v)}",
        )
        return padrao
    return v


def _lista_texto(
    e: _Erros,
    d: dict[str, Any],
    chave: str,
    caminho: str,
    *,
    regex: re.Pattern[str] | None = None,
    maximo_itens: int = 50,
    maximo_texto: int = 1000,
) -> tuple[str, ...]:
    if chave not in d:
        return ()
    v = d[chave]
    caminho_campo = f"{caminho}.{chave}" if caminho else chave
    if not isinstance(v, list):
        e.add(caminho_campo, f"esperava lista de textos, veio {_tipo(v)}")
        return ()
    if len(v) > maximo_itens:
        e.add(caminho_campo, f"{len(v)} itens (máximo {maximo_itens})")
    saida: list[str] = []
    for i, item in enumerate(v):
        if not isinstance(item, str) or not item.strip():
            e.add(f"{caminho_campo}[{i}]", "esperava texto não vazio")
        elif len(item) > maximo_texto:
            e.add(f"{caminho_campo}[{i}]", f"texto com {len(item)} caracteres")
        elif regex is not None and not regex.fullmatch(item.strip()):
            e.add(f"{caminho_campo}[{i}]", f"{item!r} fora do padrão {regex.pattern}")
        else:
            saida.append(item.strip())
    if len(set(saida)) != len(saida):
        e.add(caminho_campo, "valores repetidos")
    return tuple(saida)


def _lista_tabelas(
    e: _Erros, d: dict[str, Any], chave: str, *, obrigatoria: bool = False
) -> list[Any]:
    if chave not in d:
        if obrigatoria:
            e.add(chave, f"pelo menos um bloco [[{chave}]] é obrigatório")
        return []
    v = d[chave]
    if not isinstance(v, list) or not all(isinstance(x, dict) for x in v):
        e.add(chave, f"esperava uma lista de blocos [[{chave}]], veio {_tipo(v)}")
        return []
    if obrigatoria and not v:
        e.add(chave, f"pelo menos um bloco [[{chave}]] é obrigatório")
    return v


def _periodo(e: _Erros, valor: str, tipo: str, caminho: str) -> str:
    """Confere `AAAA-MM`/`AAAA`/... conforme o `tempo.tipo`; devolve o texto."""
    if not _RE_PERIODO[tipo].fullmatch(valor):
        e.add(caminho, f"{valor!r} não é um período {tipo} ({_FORMATO_PERIODO[tipo]})")
        return valor
    try:
        if tipo == "dia":
            dt.date.fromisoformat(valor)
        elif tipo == "mes":
            dt.date.fromisoformat(valor + "-01")
    except ValueError:
        e.add(caminho, f"{valor!r} não é uma data válida")
    return valor


# --- SQL -------------------------------------------------------------------------

_PALAVRAS_PROIBIDAS = (
    "insert update delete drop create alter attach detach copy export import install "
    "load pragma call set reset truncate begin commit rollback vacuum checkpoint use "
    "grant revoke execute prepare summarize describe show explain"
).split()
_RE_PROIBIDAS = re.compile(
    r"\b(" + "|".join(_PALAVRAS_PROIBIDAS) + r")\b", re.IGNORECASE
)
_RE_FUNCAO_DE_ARQUIVO = re.compile(
    r"\b(read_\w+|\w+_scan|glob|sniff_csv|parquet_\w+|read|query_table|query)\s*\(\s*(\$?)([A-Za-z_]*)",
    re.IGNORECASE,
)
#: Funções que executam texto ou leem arquivo: proibidas também DENTRO de literais
#: (`query('SELECT ... read_text(''/proc/self/environ'')')` passaria pelo filtro dos literais vazios).
_RE_FUNCAO_EM_LITERAL = re.compile(
    r"\b(read_\w+|\w+_scan|glob|sniff_csv|parquet_\w+|query_table|query)\s*\(",
    re.IGNORECASE,
)
#: `FROM '...'`, `FROM ('...')` e variantes: a leitura de arquivo por replacement scan.
_RE_FROM_LITERAL = re.compile(r"(?i)\b(from|join)\s*\(*\s*''")
_RE_PARAMETRO_SQL = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def limpar_sql(sql: str, *, manter_literais: bool = False) -> str:
    """Tira comentários e esvazia os literais de texto (`'...'` vira `''`).

    Com `manter_literais`, só os comentários saem (para olhar dentro dos literais, onde uma
    função como `query('...')` esconderia uma instrução inteira).
    """
    saida: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
            saida.append(" ")
        elif c == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            saida.append(sql[i : j + 1] if manter_literais else "''")
            i = j + 1
        else:
            saida.append(c)
            i += 1
    return "".join(saida)


def parametros_sql(sql: str) -> set[str]:
    """Nomes `$nome` que a consulta usa (fora de comentários e literais)."""
    return set(_RE_PARAMETRO_SQL.findall(limpar_sql(sql)))


def _dentro_de_literal(sql: str, posicao: int) -> bool:
    """A posição cai dentro de um literal `'...'` (aspas duplicadas escapam)."""
    dentro = False
    i = 0
    while i < posicao:
        if sql[i] == "'":
            if dentro and sql[i + 1 : i + 2] == "'":
                i += 2
                continue
            dentro = not dentro
        i += 1
    return dentro


def _analisar_sql(e: _Erros, caminho: str, sql: str, entradas: set[str]) -> set[str]:
    """Filtro de sanidade da consulta (não é um sandbox: a revisão em git é a barreira)."""
    limpo = limpar_sql(sql).strip()
    if not limpo:
        e.add(caminho, "consulta vazia")
        return set()
    corpo = limpo.rstrip(";").rstrip()
    if ";" in corpo:
        e.add(caminho, "mais de uma instrução (`;` no meio); uma consulta, um SELECT")
    if not re.match(r"(?is)^\(*\s*(select|with)\b", corpo):
        e.add(caminho, "a consulta deve começar com SELECT ou WITH")
    proibida = _RE_PROIBIDAS.search(corpo)
    if proibida:
        e.add(
            caminho,
            f"palavra {proibida.group(1).upper()!r} não é permitida: a consulta só lê",
        )
    if _RE_FROM_LITERAL.search(corpo) or re.search(
        r'(?i)\b(from|join)\s*\(*\s*"[^"]*[./][^"]*"', corpo
    ):
        e.add(caminho, "caminho de arquivo literal; leia o lake por `$entrada`")
    for m in _RE_FUNCAO_DE_ARQUIVO.finditer(corpo):
        funcao, cifrao, nome = m.group(1).lower(), m.group(2), m.group(3)
        if funcao == "read_parquet" and cifrao == "$" and nome:
            continue
        e.add(
            caminho,
            f"função {funcao}() fora do padrão: só `read_parquet($entrada, ...)` lê o lake",
        )
    com_literais = limpar_sql(sql, manter_literais=True)
    for m in _RE_FUNCAO_EM_LITERAL.finditer(com_literais):
        # fora de literais já foi dito acima; aqui só o que está dentro de aspas simples
        if _dentro_de_literal(com_literais, m.start()):
            e.add(
                caminho,
                f"função {m.group(1).lower()}() dentro de um literal de texto: "
                "texto que executa SQL ou lê arquivo não é permitido",
            )
    usados = set(_RE_PARAMETRO_SQL.findall(corpo))
    for nome in sorted(usados - entradas):
        e.add(
            caminho,
            f"parâmetro ${nome} não declarado em [[entrada]]{_sugestao(nome, entradas)}",
        )
    return usados & entradas


# --- validação -------------------------------------------------------------------

_RAIZ = (
    "schema_versao id titulo titulo_curto descricao estado catalogo preparo correcoes auditoria "
    "notas "
    "fonte entidade tempo preliminar limites guardas entrada visao medida dimensao "
    "atributo nota_condicional conferencia"
).split()
_RAIZ_OBRIGATORIOS = (
    "schema_versao id titulo descricao estado fonte entidade tempo entrada visao medida"
).split()


def validar(
    dados: Mapping[str, Any],
    sqls: Mapping[str, str] | None = None,
    *,
    origem: str = "",
    fontes: Mapping[str, Mapping[str, Any]] | None = None,
) -> Declaracao:
    """Valida o conteúdo de um `conjunto.toml` e devolve a `Declaracao`.

    `sqls` mapeia o nome de cada arquivo `.sql` (como escrito na declaração) ao seu texto;
    sem ele, só a declaração é validada (os arquivos não são conferidos). `fontes` é o
    registro de fetchers por id (`{"pdet": {...}}`): quando dado, a fonte do id precisa
    existir nele, `redistribuicao = "restrita"` nele recusa a declaração e a pasta do lake
    é o `lake_source_id` da fonte. Levanta `DeclaracaoInvalida` com todos os erros.
    """
    e = _Erros()
    d = _tabela(e, dict(dados), "", _RAIZ, _RAIZ_OBRIGATORIOS)
    if d is None:
        raise DeclaracaoInvalida(e.itens, origem)

    versao = d.get("schema_versao")
    if isinstance(versao, bool) or not isinstance(versao, int):
        e.add("schema_versao", f"esperava inteiro, veio {_tipo(versao)}")
        versao = 0
    elif versao != SCHEMA_VERSAO:
        e.add(
            "schema_versao",
            f"versão {versao} não suportada por este validador (aceita {SCHEMA_VERSAO})",
        )

    # identidade -----------------------------------------------------------------
    conj_id = _texto(e, d, "id", "", maximo=83)
    fonte_id = slug = ""
    if conj_id:
        partes = conj_id.split("/")
        if len(partes) != 2 or not all(
            RE_SEGMENTO.fullmatch(p) and len(p) <= 40 for p in partes
        ):
            e.add(
                "id",
                f"{conj_id!r} deve ser <fonte>/<conjunto> com segmentos em minúsculas, "
                "dígitos e hífen (ex.: pdet/caged)",
            )
        else:
            fonte_id, slug = partes
            if fontes is not None and fonte_id not in fontes:
                e.add(
                    "id",
                    f"a fonte {fonte_id!r} não está no registro de fetchers"
                    f"{_sugestao(fonte_id, fontes)}",
                )
    titulo = _texto(e, d, "titulo", "", maximo=160)
    titulo_curto = _texto(e, d, "titulo_curto", "", maximo=60, obrigatorio=False)
    descricao = _texto(e, d, "descricao", "", maximo=1500)
    estado = _texto(e, d, "estado", "", dentre=ESTADOS)
    catalogo = _texto(e, d, "catalogo", "", obrigatorio=False, regex=RE_CATALOGO,
                      formato="<fonte>/<dataset> do catálogo")  # fmt: skip
    notas = _lista_texto(e, d, "notas", "", maximo_itens=10, maximo_texto=600)

    # fonte e licença ------------------------------------------------------------
    fonte = _validar_fonte(e, d.get("fonte"), fonte_id, fontes, estado)

    # entidade -------------------------------------------------------------------
    entidade = _validar_entidade(e, d.get("entidade"))

    # tempo ----------------------------------------------------------------------
    tempo = _validar_tempo(e, d.get("tempo"))

    # entradas, visões, medidas, dimensões, atributos ---------------------------
    entradas = _validar_entradas(e, _lista_tabelas(e, d, "entrada", obrigatoria=True),
                                 fonte_id, fontes)  # fmt: skip
    visoes = _validar_visoes(e, _lista_tabelas(e, d, "visao", obrigatoria=True),
                             entidade, conj_id)  # fmt: skip
    medidas = _validar_medidas(e, _lista_tabelas(e, d, "medida", obrigatoria=True))
    dimensoes = _validar_dimensoes(
        e, _lista_tabelas(e, d, "dimensao"), entidade.qualifier if entidade else ""
    )
    atributos = _validar_atributos(e, _lista_tabelas(e, d, "atributo"))
    notas_condicionais = _validar_notas_condicionais(
        e, _lista_tabelas(e, d, "nota_condicional"), atributos, dimensoes
    )

    # preliminar, limites, guardas, conferências ---------------------------------
    preliminar = None
    if "preliminar" in d:
        t = _tabela(e, d["preliminar"], "preliminar", ("ultimos_periodos", "nota"),
                    ("ultimos_periodos", "nota"))  # fmt: skip
        if t is not None:
            n = _inteiro(e, t, "ultimos_periodos", "preliminar", minimo=1, maximo=24)
            nota = _texto(e, t, "nota", "preliminar", maximo=600)
            preliminar = Preliminar(n or 1, nota)
    limites = _validar_limites(e, d.get("limites"))
    guardas = _validar_guardas(e, d.get("guardas"), tempo, medidas)
    conferencias = _validar_conferencias(
        e, _lista_tabelas(e, d, "conferencia"), tempo, visoes, medidas, dimensoes
    )
    if estado == "publicado" and not conferencias:
        e.add(
            "conferencia",
            "estado 'publicado' exige pelo menos uma [[conferencia]] com valor da fonte",
        )

    # consultas ------------------------------------------------------------------
    preparo = _texto(e, d, "preparo", "", obrigatorio=False, regex=RE_ARQUIVO_SQL,
                     formato="nome.sql")  # fmt: skip
    correcoes = _texto(e, d, "correcoes", "", obrigatorio=False, regex=RE_ARQUIVO_CSV,
                       formato="nome.csv")  # fmt: skip
    auditoria = _texto(e, d, "auditoria", "", obrigatorio=False, regex=RE_ARQUIVO_SQL,
                       formato="nome.sql")  # fmt: skip
    if correcoes and not auditoria:
        e.add(
            "auditoria",
            "`correcoes` exige `auditoria`: é ela que diz se a correção valeu ou ficou inerte",
        )
    arquivos = [(f"visao[{i}].consulta", v.consulta) for i, v in enumerate(visoes)]
    arquivos += [
        (f"visao[{i}].descartes", v.descartes)
        for i, v in enumerate(visoes)
        if v.descartes
    ]
    if preparo:
        arquivos.insert(0, ("preparo", preparo))
    if auditoria:
        arquivos.append(("auditoria", auditoria))
    if len({nome for _, nome in [*arquivos, ("correcoes", correcoes)] if nome}) != len(
        arquivos
    ) + bool(correcoes):
        e.add("visao", "o mesmo arquivo .sql aparece em mais de um campo")
    if sqls is not None:
        nomes_entrada = {x.nome for x in entradas}
        usados: set[str] = set()
        for campo, nome in arquivos:
            if nome not in sqls:
                e.add(campo, f"arquivo {nome} não existe ao lado do conjunto.toml")
                continue
            usados |= _analisar_sql(e, f"{campo} ({nome})", sqls[nome], nomes_entrada)
            if not correcoes and re.search(
                r"(?i)\bcorrecoes\b", limpar_sql(sqls[nome])
            ):
                e.add(
                    f"{campo} ({nome})",
                    'lê a tabela `correcoes`, mas a declaração não tem `correcoes = "arquivo.csv"`',
                )
        if correcoes:
            if correcoes not in sqls:
                e.add(
                    "correcoes",
                    f"arquivo {correcoes} não existe ao lado do conjunto.toml",
                )
            else:
                _, erros_csv = ler_correcoes(sqls[correcoes])
                for msg in erros_csv:
                    e.add(f"correcoes ({correcoes})", msg)
        if all(nome in sqls for _, nome in arquivos):
            for nome in sorted(nomes_entrada - usados):
                e.add(
                    "entrada",
                    f"a entrada {nome!r} não é usada por nenhuma consulta (${nome})",
                )

    # nomes de tabela ------------------------------------------------------------
    if conj_id and fonte_id:
        for v in visoes:
            tabela = nome_tabela(conj_id, v.nivel)
            if len(tabela) > MAX_NOME_TABELA:
                e.add(
                    f"visao {v.nivel}",
                    f"a tabela gerada {tabela!r} tem {len(tabela)} caracteres "
                    f"(máximo {MAX_NOME_TABELA}); encurte o id ou o nível",
                )

    if e.itens or entidade is None or tempo is None or fonte is None:
        raise DeclaracaoInvalida(e.itens or ["declaração incompleta"], origem)
    return Declaracao(
        schema_versao=versao,
        id=conj_id,
        titulo=titulo,
        titulo_curto=titulo_curto,
        descricao=descricao,
        estado=estado,
        catalogo=catalogo,
        fonte=fonte,
        entidade=entidade,
        tempo=tempo,
        entradas=tuple(entradas),
        preparo=preparo,
        correcoes=correcoes,
        auditoria=auditoria,
        visoes=tuple(visoes),
        medidas=tuple(medidas),
        dimensoes=tuple(dimensoes),
        atributos=tuple(atributos),
        notas=notas,
        notas_condicionais=notas_condicionais,
        preliminar=preliminar,
        limites=limites,
        guardas=guardas,
        conferencias=tuple(conferencias),
    )


def _validar_fonte(
    e: _Erros,
    bruto: Any,
    fonte_id: str,
    fontes: Mapping[str, Mapping[str, Any]] | None,
    estado: str,
) -> Fonte | None:
    chaves = "orgao licenca atribuicao redistribuicao url parecer_licenca".split()
    t = _tabela(
        e, bruto, "fonte", chaves, ("orgao", "licenca", "atribuicao", "redistribuicao")
    )
    if t is None:
        return None
    orgao = _texto(e, t, "orgao", "fonte", maximo=200)
    licenca = _texto(e, t, "licenca", "fonte", maximo=300)
    atribuicao = _texto(e, t, "atribuicao", "fonte", maximo=1000)
    redistribuicao = _texto(e, t, "redistribuicao", "fonte", dentre=REDISTRIBUICOES)
    url = _texto(e, t, "url", "fonte", obrigatorio=False, maximo=300,
                 regex=re.compile(r"^https?://\S+$"), formato="URL http(s) sem espaços")  # fmt: skip
    parecer = None
    if "parecer_licenca" in t:
        p = _tabela(e, t["parecer_licenca"], "fonte.parecer_licenca",
                    ("data", "por", "nota"), ("data", "por"))  # fmt: skip
        if p is not None:
            data = p.get("data")
            if isinstance(data, dt.date) and not isinstance(data, dt.datetime):
                data_txt = data.isoformat()
            elif isinstance(data, str):
                data_txt = data
                try:
                    dt.date.fromisoformat(data)
                except ValueError:
                    e.add("fonte.parecer_licenca.data", f"{data!r} não é AAAA-MM-DD")
            else:
                e.add("fonte.parecer_licenca.data", "esperava a data AAAA-MM-DD")
                data_txt = ""
            parecer = Parecer(
                data_txt,
                _texto(e, p, "por", "fonte.parecer_licenca", maximo=200),
                _texto(
                    e, p, "nota", "fonte.parecer_licenca", obrigatorio=False, maximo=600
                ),
            )
    if licenca and _RE_LICENCA_SEM_DERIVACAO.search(licenca) and parecer is None:
        e.add(
            "fonte.parecer_licenca",
            f"a licença {licenca!r} restringe obra derivada: informe "
            "[fonte.parecer_licenca] (data e quem decidiu)",
        )
    if redistribuicao == "restrita" and estado == "publicado":
        e.add(
            "fonte.redistribuicao",
            "fonte 'restrita' não pode estar no estado 'publicado'",
        )
    if fontes is not None and fonte_id in fontes:
        registro = fontes[fonte_id].get("redistribuicao")
        if registro == "restrita" and redistribuicao != "restrita":
            e.add(
                "fonte.redistribuicao",
                f"o registro de fetchers marca a fonte {fonte_id!r} como restrita",
            )
    return Fonte(orgao, licenca, atribuicao, redistribuicao, url, parecer)


def _validar_entidade(e: _Erros, bruto: Any) -> Entidade | None:
    t = _tabela(e, bruto, "entidade", ("tipo", "rotulo", "qualifier", "chaves_alternativas"),
                ("tipo", "rotulo", "qualifier"))  # fmt: skip
    if t is None:
        return None
    tipo = _texto(e, t, "tipo", "entidade", dentre=TIPOS_ENTIDADE)
    rotulo = _texto(e, t, "rotulo", "entidade", maximo=60)
    qualifier = _texto(e, t, "qualifier", "entidade", regex=RE_NOME)
    chaves = _lista_texto(
        e, t, "chaves_alternativas", "entidade", regex=RE_NOME, maximo_itens=3
    )
    if tipo == "territorio" and qualifier and qualifier != "geo":
        e.add("entidade.qualifier", "entidade territorial usa o qualifier 'geo'")
    if tipo == "identificador" and qualifier in QUALIFIERS_RESERVADOS:
        e.add(
            "entidade.qualifier",
            f"{qualifier!r} é nome reservado; use p. ex. 'cia' ou 'estacao'",
        )
    if tipo == "territorio" and chaves:
        e.add(
            "entidade.chaves_alternativas",
            "só entidade 'identificador' tem chave alternativa",
        )
    return Entidade(tipo, rotulo, qualifier, chaves)


def _validar_tempo(e: _Erros, bruto: Any) -> Tempo | None:
    t = _tabela(
        e, bruto, "tempo",
        ("tipo", "frequencia", "alinhamento_painel", "padrao", "fracao"),
        ("tipo", "frequencia", "alinhamento_painel", "padrao"),
    )  # fmt: skip
    if t is None:
        return None
    tipo = _texto(e, t, "tipo", "tempo", dentre=TIPOS_TEMPO)
    freq = _texto(e, t, "frequencia", "tempo", maximo=20)
    if tipo in FREQUENCIA_DO_TEMPO and freq and freq != FREQUENCIA_DO_TEMPO[tipo]:
        e.add("tempo.frequencia",
              f"para tempo.tipo = {tipo!r} a frequência é {FREQUENCIA_DO_TEMPO[tipo]!r}, não {freq!r}")  # fmt: skip
    alinhamento = _texto(e, t, "alinhamento_painel", "tempo", dentre=ALINHAMENTOS)
    padrao = _texto(e, t, "padrao", "tempo", dentre=PADROES_TEMPO)
    fracao = _numero(e, t, "fracao", "tempo", minimo=0, maximo=1, minimo_aberto=True)
    if padrao == "ultimo_com_cobertura" and "fracao" not in t:
        e.add("tempo.fracao", "o padrão 'ultimo_com_cobertura' exige fracao (0 a 1)")
    if padrao == "ultimo" and "fracao" in t:
        e.add("tempo.fracao", "fracao só vale com o padrão 'ultimo_com_cobertura'")
    return Tempo(tipo, freq, alinhamento, padrao, fracao)


def _validar_entradas(
    e: _Erros,
    blocos: list[Any],
    fonte_id: str,
    fontes: Mapping[str, Mapping[str, Any]] | None,
) -> list[Entrada]:
    saida: list[Entrada] = []
    pasta_lake = fonte_id
    if fontes is not None and fonte_id in fontes:
        pasta_lake = str(fontes[fonte_id].get("lake_source_id") or fonte_id)
    vistos: set[str] = set()
    for i, b in enumerate(blocos):
        c = f"entrada[{i}]"
        t = _tabela(e, b, c, ("nome", "glob"), ("nome", "glob"))
        if t is None:
            continue
        nome = _texto(e, t, "nome", c, regex=RE_PARAMETRO, maximo=31)
        glob = _texto(e, t, "glob", c, maximo=300)
        if nome in vistos:
            e.add(f"{c}.nome", f"entrada {nome!r} repetida")
        vistos.add(nome)
        if glob:
            segmentos = glob.split("/")
            if glob.startswith("/") or ".." in segmentos or "\\" in glob:
                e.add(
                    f"{c}.glob", f"{glob!r} deve ser relativo à raiz do lake, sem '..'"
                )
            elif not RE_GLOB.fullmatch(glob):
                e.add(
                    f"{c}.glob", f"{glob!r} tem caracteres fora de [A-Za-z0-9_.=*?[]/-]"
                )
            elif not glob.endswith(".parquet"):
                e.add(f"{c}.glob", f"{glob!r} deve terminar em .parquet")
            elif fonte_id and segmentos[0] != pasta_lake:
                e.add(
                    f"{c}.glob",
                    f"{glob!r} deve começar por {pasta_lake}/ (a fonte do conjunto)",
                )
        saida.append(Entrada(nome, glob))
    return saida


def _validar_visoes(
    e: _Erros, blocos: list[Any], entidade: Entidade | None, conj_id: str
) -> list[Visao]:
    saida: list[Visao] = []
    vistos: set[str] = set()
    for i, b in enumerate(blocos):
        c = f"visao[{i}]"
        t = _tabela(e, b, c, ("nivel", "chave", "consulta", "descartes", "cabecalhos"),
                    ("nivel", "consulta", "cabecalhos"))  # fmt: skip
        if t is None:
            continue
        nivel = _texto(e, t, "nivel", c, regex=RE_NIVEL, maximo=12,
                       formato="MAIÚSCULAS, até 12 caracteres")  # fmt: skip
        consulta = _texto(e, t, "consulta", c, regex=RE_ARQUIVO_SQL, formato="nome.sql")
        descartes = _texto(e, t, "descartes", c, obrigatorio=False, regex=RE_ARQUIVO_SQL,
                           formato="nome.sql")  # fmt: skip
        chave = _texto(e, t, "chave", c, obrigatorio=False, maximo=20)
        cab = _lista_texto(e, t, "cabecalhos", c, maximo_itens=2, maximo_texto=40)
        if "cabecalhos" in t and len(cab) != 2:
            e.add(
                f"{c}.cabecalhos",
                "esperava dois textos: [cabeçalho da chave, cabeçalho do nome]",
            )
        if nivel in vistos:
            e.add(f"{c}.nivel", f"nível {nivel!r} repetido")
        vistos.add(nivel)
        if entidade is not None and nivel:
            if entidade.tipo == "territorio":
                if nivel not in CHAVES_DO_NIVEL:
                    e.add(f"{c}.nivel",
                          f"nível territorial {nivel!r} desconhecido; aceitos: {', '.join(CHAVES_DO_NIVEL)}")  # fmt: skip
                elif chave not in CHAVES_DO_NIVEL[nivel]:
                    e.add(f"{c}.chave",
                          f"o nível {nivel} exige chave dentre: {', '.join(CHAVES_DO_NIVEL[nivel])}")  # fmt: skip
            elif chave:
                e.add(f"{c}.chave", "só entidade territorial declara chave por nível")
        cabecalhos = (cab[0], cab[1]) if len(cab) == 2 else ("", "")
        saida.append(Visao(nivel, consulta, cabecalhos, chave, descartes))
    return saida


def _validar_medidas(e: _Erros, blocos: list[Any]) -> list[Medida]:
    saida: list[Medida] = []
    vistos: set[str] = set()
    for i, b in enumerate(blocos):
        c = f"medida[{i}]"
        t = _tabela(e, b, c, ("id", "rotulo", "descricao", "unidade", "tipo", "aditiva", "nota"),
                    ("id", "rotulo", "unidade", "tipo"))  # fmt: skip
        if t is None:
            continue
        mid = _texto(e, t, "id", c, regex=RE_NOME)
        if mid in vistos:
            e.add(f"{c}.id", f"medida {mid!r} repetida")
        vistos.add(mid)
        saida.append(
            Medida(
                id=mid,
                rotulo=_texto(e, t, "rotulo", c, maximo=160),
                unidade=_texto(e, t, "unidade", c, maximo=40),
                tipo=_texto(e, t, "tipo", c, dentre=TIPOS_MEDIDA),
                aditiva=_booleano(e, t, "aditiva", c),
                descricao=_texto(e, t, "descricao", c, obrigatorio=False, maximo=600),
                nota=_texto(e, t, "nota", c, obrigatorio=False, maximo=600),
            )
        )
    return saida


def _validar_dimensoes(e: _Erros, blocos: list[Any], qualifier: str) -> list[Dimensao]:
    saida: list[Dimensao] = []
    vistos: set[str] = set()
    for i, b in enumerate(blocos):
        c = f"dimensao[{i}]"
        t = _tabela(e, b, c, ("id", "rotulo", "valores", "padrao"), ("id", "rotulo"))
        if t is None:
            continue
        did = _texto(e, t, "id", c, regex=RE_NOME)
        if did in QUALIFIERS_RESERVADOS or (qualifier and did == qualifier):
            e.add(
                f"{c}.id", f"{did!r} já é um qualifier da consulta; escolha outro nome"
            )
        if did in vistos:
            e.add(f"{c}.id", f"dimensão {did!r} repetida")
        vistos.add(did)
        valores = _lista_texto(
            e, t, "valores", c, regex=RE_VALOR_DIMENSAO, maximo_itens=50
        )
        if "valores" in t and not valores:
            e.add(f"{c}.valores", "lista vazia (omita para dimensão aberta)")
        padrao = _texto(e, t, "padrao", c, obrigatorio=False, maximo=40)
        if padrao and valores and padrao not in valores:
            e.add(
                f"{c}.padrao", f"{padrao!r} não está em valores ({', '.join(valores)})"
            )
        saida.append(
            Dimensao(did, _texto(e, t, "rotulo", c, maximo=60), valores, padrao)
        )
    return saida


def _validar_atributos(e: _Erros, blocos: list[Any]) -> list[Atributo]:
    saida: list[Atributo] = []
    vistos: set[str] = set()
    for i, b in enumerate(blocos):
        c = f"atributo[{i}]"
        t = _tabela(e, b, c, ("id", "rotulo", "tipo"), ("id", "rotulo", "tipo"))
        if t is None:
            continue
        aid = _texto(e, t, "id", c, regex=RE_NOME)
        if aid in vistos:
            e.add(f"{c}.id", f"atributo {aid!r} repetido")
        vistos.add(aid)
        saida.append(
            Atributo(
                aid,
                _texto(e, t, "rotulo", c, maximo=60),
                _texto(e, t, "tipo", c, dentre=TIPOS_ATRIBUTO),
            )
        )
    return saida


def _valor_da_condicao(
    e: _Erros,
    t: dict[str, Any],
    operador: str,
    caminho: str,
    tipo_alvo: str,
    valores: tuple[str, ...],
) -> str | bool | int:
    """Confere o valor da condição no formato do tipo do alvo (`tipo_alvo`: tipo do
    atributo, ou `dimensao`)."""
    campo = f"{caminho}.{operador}"
    v = t[operador]
    if tipo_alvo == "boolean":
        if not isinstance(v, bool):
            e.add(campo, f"atributo boolean pede true/false, veio {_tipo(v)}")
            return False
        return v
    if tipo_alvo == "integer":
        if isinstance(v, bool) or not isinstance(v, int):
            e.add(campo, f"atributo integer pede um inteiro, veio {_tipo(v)}")
            return 0
        return v
    if not isinstance(v, str) or not v.strip():
        e.add(campo, f"esperava texto não vazio, veio {_tipo(v)}")
        return ""
    v = v.strip()
    if tipo_alvo == "date":
        m = _RE_MES_DIA.fullmatch(v)
        try:
            if m is None:
                raise ValueError
            dt.date(
                2000, int(m.group(1)), int(m.group(2))
            )  # 2000 é bissexto: 02-29 vale
        except ValueError:
            e.add(
                campo,
                f"{v!r} não é MM-DD (dia e mês, sem ano; atributo date só compara dia e mês)",
            )
        return v
    if tipo_alvo == "dimensao":
        if valores and v not in valores:
            e.add(
                campo,
                f"{v!r} não está nos valores da dimensão ({', '.join(valores)})"
                f"{_sugestao(v, valores)}",
            )
        elif not valores and not RE_VALOR_DIMENSAO.fullmatch(v):
            e.add(campo, f"{v!r} fora do padrão {RE_VALOR_DIMENSAO.pattern}")
        return v
    if len(v) > 80:  # text
        e.add(campo, f"texto com {len(v)} caracteres (máximo 80)")
    return v


def _validar_condicao(
    e: _Erros,
    bruto: Any,
    caminho: str,
    atributos: Sequence[Atributo],
    dimensoes: Sequence[Dimensao],
) -> Condicao | None:
    t = _tabela(e, bruto, caminho, ("atributo", "dimensao", *OPERADORES_NOTA))
    if t is None:
        return None
    alvos = [k for k in ("atributo", "dimensao") if k in t]
    if len(alvos) != 1:
        e.add(caminho, "informe exatamente um entre 'atributo' e 'dimensao'")
        return None
    operadores = [k for k in OPERADORES_NOTA if k in t]
    if len(operadores) != 1:
        e.add(
            caminho,
            f"informe exatamente um operador entre {', '.join(OPERADORES_NOTA)}",
        )
        return None
    tipo, operador = alvos[0], operadores[0]
    alvo_id = _texto(e, t, tipo, caminho, regex=RE_NOME)
    if tipo == "atributo":
        existentes = {a.id: a for a in atributos}
        tipo_alvo = existentes[alvo_id].tipo if alvo_id in existentes else ""
        valores: tuple[str, ...] = ()
    else:
        existentes_d = {d.id: d for d in dimensoes}
        tipo_alvo = "dimensao" if alvo_id in existentes_d else ""
        valores = existentes_d[alvo_id].valores if alvo_id in existentes_d else ()
    if not tipo_alvo:
        if alvo_id:
            declarados = (
                [a.id for a in atributos]
                if tipo == "atributo"
                else [d.id for d in dimensoes]
            )
            e.add(
                f"{caminho}.{tipo}",
                f"{tipo} {alvo_id!r} não está declarado"
                f"{_sugestao(alvo_id, declarados)}; declarados: "
                f"{', '.join(declarados) or 'nenhum'}",
            )
        return None
    valor = _valor_da_condicao(e, t, operador, caminho, tipo_alvo, valores)
    return Condicao(tipo, alvo_id, operador, valor)


def _validar_notas_condicionais(
    e: _Erros,
    blocos: list[Any],
    atributos: Sequence[Atributo],
    dimensoes: Sequence[Dimensao],
) -> tuple[NotaCondicional, ...]:
    if len(blocos) > 10:
        e.add("nota_condicional", f"{len(blocos)} blocos (máximo 10)")
    saida: list[NotaCondicional] = []
    for i, b in enumerate(blocos):
        c = f"nota_condicional[{i}]"
        t = _tabela(e, b, c, ("texto", "quando", "substantivo"), ("texto", "quando"))
        if t is None:
            continue
        texto = _texto(e, t, "texto", c, maximo=600)
        marcadores = set()
        for m in _RE_MARCADOR.finditer(texto):
            if m.group(1) in MARCADORES_NOTA:
                marcadores.add(m.group(1))
            else:
                e.add(
                    f"{c}.texto",
                    f"marcador {{{m.group(1)}}} desconhecido{_sugestao(m.group(1), MARCADORES_NOTA)}; "
                    f"aceitos: {', '.join('{' + x + '}' for x in MARCADORES_NOTA)}",
                )
        resto = _RE_MARCADOR.sub("", texto)
        if "{" in resto or "}" in resto:
            e.add(f"{c}.texto", "chave solta: use só os marcadores do vocabulário")
        condicao = (
            _validar_condicao(e, t["quando"], f"{c}.quando", atributos, dimensoes)
            if "quando" in t
            else None
        )
        substantivo: tuple[str, str] | None = None
        if "substantivo" in t:
            s = t["substantivo"]
            if (
                not isinstance(s, list)
                or len(s) != 2
                or not all(isinstance(x, str) and x.strip() for x in s)
            ):
                e.add(
                    f"{c}.substantivo",
                    'esperava ["singular", "plural"] (dois textos não vazios)',
                )
            elif any(len(x) > 40 or "{" in x or "}" in x for x in s):
                e.add(
                    f"{c}.substantivo", "texto com mais de 40 caracteres ou com chave"
                )
            elif not marcadores:
                e.add(
                    f"{c}.substantivo",
                    "só tem efeito com {n} ou {valores} no texto; remova-o",
                )
            else:
                substantivo = (s[0].strip(), s[1].strip())
        if condicao is not None:
            saida.append(NotaCondicional(texto, condicao, substantivo))
    return tuple(saida)


# --- tabela de correções (CSV) ----------------------------------------------------


def ler_correcoes(texto: str) -> tuple[Correcoes | None, list[str]]:
    """Valida o CSV de correções (UTF-8, vírgula, aspas duplas) e devolve `(tabela, erros)`.

    Cabeçalho: uma ou mais colunas de chave (nomes `^[a-z][a-z0-9_]{0,40}$`, texto, as que a
    consulta usa para achar a célula) mais `valor` (número), `referencia` (de onde vem o valor
    oficial), `motivo` e `data` (AAAA-MM-DD, quando foi decidido). Nada de célula vazia, chave
    repetida, linha com colunas a mais ou a menos; no máximo `MAX_CORRECOES` linhas. O arquivo
    só vira dado: nunca é executado, e o DuckDB não o lê (o carregador insere as linhas).
    """
    import csv
    import io
    import math

    erros: list[str] = []
    try:
        leitor = list(csv.reader(io.StringIO(texto, newline=""), strict=True))
    except csv.Error as exc:
        return None, [f"CSV inválido: {exc}"]
    if not leitor:
        return None, ["CSV vazio: falta o cabeçalho"]
    cab = [c.strip() for c in leitor[0]]
    if len(set(cab)) != len(cab):
        erros.append("cabeçalho com colunas repetidas")
    for c in cab:
        if not RE_NOME.fullmatch(c):
            erros.append(f"coluna {c!r} fora do padrão {RE_NOME.pattern}")
    faltam = [c for c in COLUNAS_FIXAS_CORRECOES if c not in cab]
    if faltam:
        erros.append(f"faltam as colunas {', '.join(faltam)}")
    chaves = tuple(c for c in cab if c not in COLUNAS_FIXAS_CORRECOES)
    if not chaves:
        erros.append(
            "falta pelo menos uma coluna de chave (além de valor, referencia, motivo e data)"
        )
    if erros:
        return None, erros
    linhas_brutas = [r for r in leitor[1:] if r]  # linha em branco não conta
    if len(linhas_brutas) > MAX_CORRECOES:
        erros.append(f"{len(linhas_brutas)} correções (máximo {MAX_CORRECOES})")
    ordem = (*chaves, *COLUNAS_FIXAS_CORRECOES)
    saida: list[tuple[Any, ...]] = []
    vistas: set[tuple[str, ...]] = set()
    for n, r in enumerate(linhas_brutas, start=2):
        onde = f"linha {n}"
        if len(r) != len(cab):
            erros.append(f"{onde}: {len(r)} colunas, o cabeçalho tem {len(cab)}")
            continue
        cel = {c: v.strip() for c, v in zip(cab, r, strict=True)}
        vazias = [c for c in cab if not cel[c]]
        if vazias:
            erros.append(f"{onde}: célula vazia em {', '.join(vazias)}")
            continue
        for c in (*chaves, "referencia", "motivo"):
            limite = 80 if c in chaves else 600
            if len(cel[c]) > limite:
                erros.append(
                    f"{onde}: {c} com {len(cel[c])} caracteres (máximo {limite})"
                )
        try:
            valor = float(cel["valor"])
            if not math.isfinite(valor):
                raise ValueError
        except ValueError:
            erros.append(f"{onde}: valor {cel['valor']!r} não é um número")
            continue
        try:
            data = dt.date.fromisoformat(cel["data"])
        except ValueError:
            erros.append(f"{onde}: data {cel['data']!r} não é AAAA-MM-DD")
            continue
        chave = tuple(cel[c] for c in chaves)
        if chave in vistas:
            erros.append(f"{onde}: chave repetida ({', '.join(chave)})")
        vistas.add(chave)
        todas = {**cel, "valor": valor, "data": data}
        saida.append(tuple(todas[c] for c in ordem))
    if erros:
        return None, erros
    return Correcoes(chaves, tuple(saida)), []


def _validar_limites(e: _Erros, bruto: Any) -> Limites:
    if bruto is None:
        return Limites()
    t = _tabela(e, bruto, "limites", tuple(LIMITES_PADRAO))
    if t is None:
        return Limites()
    valores: dict[str, int] = {}
    for nome, padrao in LIMITES_PADRAO.items():
        v = _inteiro(
            e, t, nome, "limites", minimo=1, maximo=LIMITES_TETO[nome], padrao=padrao
        )
        valores[nome] = padrao if v is None else v
    return Limites(**valores)


def _validar_guardas(
    e: _Erros, bruto: Any, tempo: Tempo | None, medidas: list[Medida]
) -> Guardas:
    permitidas = (
        "queda_maxima_linhas periodos_nao_somem periodos_continuos periodo_inicial "
        "cobertura_minima_entidades queda_maxima_entidades_por_periodo "
        "revisao_maxima_total revisao_medidas queda_maxima_valores"
    ).split()
    if bruto is None:
        return Guardas()
    t = _tabela(e, bruto, "guardas", permitidas)
    if t is None:
        return Guardas()
    queda = _numero(e, t, "queda_maxima_linhas", "guardas", minimo=0, maximo=1,
                    minimo_aberto=True, maximo_aberto=True, padrao=0.10)  # fmt: skip
    nao_somem = _booleano(e, t, "periodos_nao_somem", "guardas", padrao=True)
    continuos = _booleano(e, t, "periodos_continuos", "guardas")
    inicial = _texto(e, t, "periodo_inicial", "guardas", obrigatorio=False, maximo=10)
    if inicial and tempo is not None and tempo.tipo in _RE_PERIODO:
        _periodo(e, inicial, tempo.tipo, "guardas.periodo_inicial")
    if inicial and not continuos:
        e.add("guardas.periodo_inicial", "só vale com periodos_continuos = true")
    cobertura = _inteiro(
        e, t, "cobertura_minima_entidades", "guardas", minimo=1, maximo=10_000_000
    )
    queda_ent = _numero(e, t, "queda_maxima_entidades_por_periodo", "guardas", minimo=0,
                        maximo=1, minimo_aberto=True, maximo_aberto=True)  # fmt: skip
    revisao = _numero(e, t, "revisao_maxima_total", "guardas", minimo=0, maximo=1,
                      minimo_aberto=True, maximo_aberto=True)  # fmt: skip
    queda_valores = _numero(e, t, "queda_maxima_valores", "guardas", minimo=0, maximo=1,
                            minimo_aberto=True, maximo_aberto=True, padrao=0.10)  # fmt: skip
    ids_aditivas = [m.id for m in medidas if m.aditiva]
    rev_medidas = _lista_texto(e, t, "revisao_medidas", "guardas", regex=RE_NOME)
    for m in rev_medidas:
        if m not in ids_aditivas:
            e.add("guardas.revisao_medidas",
                  f"{m!r} não é uma medida aditiva do conjunto (aditivas: {', '.join(ids_aditivas) or 'nenhuma'})")  # fmt: skip
    if revisao is not None and not ids_aditivas:
        e.add(
            "guardas.revisao_maxima_total",
            "exige pelo menos uma medida com aditiva = true",
        )
    if rev_medidas and revisao is None:
        e.add(
            "guardas.revisao_medidas", "sem revisao_maxima_total a lista não tem efeito"
        )
    if revisao is not None and not rev_medidas:
        rev_medidas = tuple(ids_aditivas)
    return Guardas(
        queda_maxima_linhas=0.10 if queda is None else queda,
        periodos_nao_somem=nao_somem,
        periodos_continuos=continuos,
        periodo_inicial=inicial,
        cobertura_minima_entidades=cobertura,
        queda_maxima_entidades_por_periodo=queda_ent,
        revisao_maxima_total=revisao,
        revisao_medidas=tuple(rev_medidas),
        queda_maxima_valores=0.10 if queda_valores is None else queda_valores,
    )


def _validar_conferencias(
    e: _Erros,
    blocos: list[Any],
    tempo: Tempo | None,
    visoes: list[Visao],
    medidas: list[Medida],
    dimensoes: list[Dimensao] | None = None,
) -> list[Conferencia]:
    saida: list[Conferencia] = []
    dims = {d.id: d for d in dimensoes or []}
    niveis = {v.nivel for v in visoes}
    ids = {m.id for m in medidas}
    for i, b in enumerate(blocos):
        c = f"conferencia[{i}]"
        t = _tabela(
            e, b, c,
            ("nivel", "medida", "periodo", "entidade", "dimensoes", "valor", "tolerancia_relativa", "referencia"),
            ("nivel", "medida", "periodo", "valor", "tolerancia_relativa", "referencia"),
        )  # fmt: skip
        if t is None:
            continue
        nivel = _texto(e, t, "nivel", c, maximo=12)
        if nivel and nivel not in niveis:
            e.add(f"{c}.nivel", f"visão {nivel!r} não existe{_sugestao(nivel, niveis)}")
        medida = _texto(e, t, "medida", c, maximo=41)
        if medida and medida not in ids:
            e.add(
                f"{c}.medida", f"medida {medida!r} não existe{_sugestao(medida, ids)}"
            )
        periodo = _texto(e, t, "periodo", c, maximo=10)
        if periodo and tempo is not None and tempo.tipo in _RE_PERIODO:
            _periodo(e, periodo, tempo.tipo, f"{c}.periodo")
        valor: float | None = _numero(e, t, "valor", c)
        if valor is not None and isinstance(t["valor"], int):
            valor = t["valor"]  # inteiro continua inteiro no espelho
        tol = _numero(
            e, t, "tolerancia_relativa", c, minimo=0, maximo=1, maximo_aberto=True
        )
        fixadas: list[tuple[str, str]] = []
        if "dimensoes" in t:
            bruto_d = t["dimensoes"]
            if not isinstance(bruto_d, dict) or not bruto_d:
                e.add(
                    f"{c}.dimensoes",
                    'esperava uma tabela {dimensao = "valor"} não vazia',
                )
            else:
                for did, val in sorted(bruto_d.items()):
                    if did not in dims:
                        e.add(f"{c}.dimensoes.{did}",
                              f"dimensão {did!r} não existe{_sugestao(str(did), dims)}")  # fmt: skip
                    elif not isinstance(val, str) or not val:
                        e.add(
                            f"{c}.dimensoes.{did}",
                            "esperava o valor da dimensão em texto",
                        )
                    elif dims[did].valores and val not in dims[did].valores:
                        e.add(f"{c}.dimensoes.{did}",
                              f"{val!r} não está em valores ({', '.join(dims[did].valores)})")  # fmt: skip
                    else:
                        fixadas.append((did, val))
        saida.append(
            Conferencia(
                nivel, medida, periodo,
                0.0 if valor is None else valor,
                0.0 if tol is None else tol,
                _texto(e, t, "referencia", c, maximo=400),
                _texto(e, t, "entidade", c, obrigatorio=False, maximo=60),
                tuple(fixadas),
            )
        )  # fmt: skip
    return saida


# --- contrato de colunas da consulta -----------------------------------------------


@dataclass(frozen=True, slots=True)
class ColunaEsperada:
    nome: str
    familia: str  # texto | data | booleano | inteiro | double | decimal
    obrigatoria: bool = True


_FAMILIA_DA_MEDIDA = {"bigint": "inteiro", "double": "double", "numeric": "decimal"}
_FAMILIA_DO_ATRIBUTO = {
    "text": "texto",
    "date": "data",
    "boolean": "booleano",
    "integer": "inteiro",
}


def colunas_esperadas(decl: Declaracao, visao: Visao) -> list[ColunaEsperada]:
    """Colunas, em ordem, que a consulta da visão devolve (ADR D3).

    `entidade`, `entidade_rotulo` (obrigatória só para entidade 'identificador'),
    `entidade_<chave>` por chave alternativa, `periodo` (data do primeiro dia do período),
    `d_<dimensão>`, `a_<atributo>` e `m_<medida>`.
    """
    cols = [
        ColunaEsperada("entidade", "texto"),
        ColunaEsperada(
            "entidade_rotulo", "texto", decl.entidade.tipo == "identificador"
        ),
    ]
    cols += [
        ColunaEsperada(f"entidade_{c}", "texto")
        for c in decl.entidade.chaves_alternativas
    ]
    cols.append(ColunaEsperada("periodo", "data"))
    cols += [ColunaEsperada(f"d_{d.id}", "texto") for d in decl.dimensoes]
    cols += [
        ColunaEsperada(f"a_{a.id}", _FAMILIA_DO_ATRIBUTO[a.tipo])
        for a in decl.atributos
    ]
    cols += [
        ColunaEsperada(f"m_{m.id}", _FAMILIA_DA_MEDIDA[m.tipo]) for m in decl.medidas
    ]
    return cols


def familia_duckdb(tipo: str) -> str:
    """Família de um tipo de coluna do DuckDB (`DECIMAL(18,3)` -> `decimal`)."""
    t = tipo.upper().split("(")[0].strip()
    if t in ("VARCHAR", "TEXT", "STRING", "CHAR", "BPCHAR"):
        return "texto"
    if t in ("DATE",):
        return "data"
    if t in ("BOOLEAN", "BOOL"):
        return "booleano"
    if t in ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT",
             "USMALLINT", "UINTEGER", "UBIGINT", "UHUGEINT", "INT"):  # fmt: skip
        return "inteiro"
    if t in ("DOUBLE", "FLOAT", "REAL"):
        return "double"
    if t == "DECIMAL":
        return "decimal"
    return t.lower()


def conferir_colunas(
    decl: Declaracao,
    visao: Visao,
    colunas: Sequence[tuple[str, str]],
    *,
    descartes: bool = False,
) -> list[str]:
    """Compara `(nome, tipo DuckDB)` do resultado com o contrato; devolve os problemas.

    Para `descartes = True` o contrato é `periodo` (texto) mais colunas `m_<medida>` (ao
    menos uma). Colunas a mais, a menos ou de tipo errado são erros; a ordem não importa (o
    carregador lê por nome). Nomes repetidos também são erro.
    """
    problemas: list[str] = []
    onde = f"{decl.id} visão {visao.nivel}{' (descartes)' if descartes else ''}"
    reais = [(n, familia_duckdb(t), t) for n, t in colunas]
    if descartes:
        esperadas = [ColunaEsperada("periodo", "texto")]
        medidas = {f"m_{m.id}": _FAMILIA_DA_MEDIDA[m.tipo] for m in decl.medidas}
        for nome, _, _ in reais[1:]:
            if nome not in medidas:
                problemas.append(f"{onde}: coluna {nome!r} não é m_<medida> declarada")
        esperadas += [
            ColunaEsperada(n, medidas[n]) for n, _, _ in reais[1:] if n in medidas
        ]
        if len(reais) < 2:
            problemas.append(f"{onde}: faltam colunas m_<medida>")
    else:
        esperadas = [c for c in colunas_esperadas(decl, visao) if c.obrigatoria or
                     any(n == c.nome for n, _, _ in reais)]  # fmt: skip
    nomes_reais = [n for n, _, _ in reais]
    for n in sorted({n for n in nomes_reais if nomes_reais.count(n) > 1}):
        problemas.append(f"{onde}: coluna {n!r} repetida")
    nomes_esperados = [c.nome for c in esperadas]
    for c in esperadas:
        if c.nome not in nomes_reais:
            problemas.append(f"{onde}: falta a coluna {c.nome!r} ({c.familia})")
    conhecidos = set(nomes_esperados)
    for n, _, _ in reais:
        if n not in conhecidos and not (descartes and n.startswith("m_")):
            problemas.append(
                f"{onde}: coluna {n!r} não faz parte do contrato{_sugestao(n, conhecidos)}"
            )
    for c in esperadas:
        for n, fam, bruto in reais:
            if n == c.nome and fam != c.familia:
                problemas.append(
                    f"{onde}: coluna {n!r} é {bruto}, o contrato pede {c.familia}"
                )
    return problemas


# --- conjunto de declarações ----------------------------------------------------------


def tabelas_duplicadas(decls: Iterable[Declaracao]) -> list[str]:
    """Ids repetidos e nomes de tabela gerada que colidem entre declarações."""
    problemas: list[str] = []
    ids: dict[str, int] = {}
    tabelas: dict[str, str] = {}
    for d in decls:
        ids[d.id] = ids.get(d.id, 0) + 1
        for v in d.visoes:
            t = d.tabela(v)
            if t in tabelas and tabelas[t] != d.id:
                problemas.append(f"tabela {t!r} gerada por {tabelas[t]} e por {d.id}")
            tabelas[t] = d.id
    problemas += [f"id {i!r} declarado {n} vezes" for i, n in ids.items() if n > 1]
    return problemas


# --- leitura de arquivos ----------------------------------------------------------


def ler_registro(caminho: Path) -> dict[str, dict[str, Any]]:
    """Registro de fetchers (`registry.json`, público ou interno) -> `{id da fonte: entrada}`."""
    doc = json.loads(caminho.read_text(encoding="utf-8"))
    return {f["id"]: f for f in doc.get("fetchers", [])}


def carregar(
    caminho: Path | str,
    *,
    fontes: Mapping[str, Mapping[str, Any]] | None = None,
) -> Declaracao:
    """Lê `conjunto.toml` (ou a pasta que o contém) e as `.sql` da mesma pasta e valida."""
    p = Path(caminho)
    if p.is_dir():
        p = p / "conjunto.toml"
    try:
        dados = tomllib.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DeclaracaoInvalida([f"arquivo {p} não existe"], str(p)) from None
    except tomllib.TOMLDecodeError as exc:
        raise DeclaracaoInvalida([f"TOML inválido: {exc}"], str(p)) from exc
    sqls = {
        f.name: f.read_text(encoding="utf-8")
        for f in sorted([*p.parent.glob("*.sql"), *p.parent.glob("*.csv")])
    }
    return validar(dados, sqls, origem=str(p), fontes=fontes)


def declaracoes_do_catalogo(raiz: Path) -> list[Path]:
    """Os `conjunto.toml` de `publicacao/<fonte>/<conjunto>/` (pastas `_*` ficam de fora)."""
    return sorted(
        p
        for p in raiz.glob("*/*/conjunto.toml")
        if not p.parent.parent.name.startswith("_")
        and not p.parent.name.startswith("_")
    )


def _alvos(caminhos: Sequence[str]) -> list[Path]:
    achados: list[Path] = []
    for c in caminhos:
        p = Path(c)
        if p.is_dir() and not (p / "conjunto.toml").exists():
            # pastas `_*` (o `_exemplo` fictício) ficam de fora da varredura, como no catálogo;
            # o exemplo se valida por caminho, sem o registro (a fonte dele não existe)
            achados.extend(
                a
                for a in sorted(p.glob("**/conjunto.toml"))
                if not any(parte.startswith("_") for parte in a.relative_to(p).parts[:-1])
            )
        else:
            achados.append(p)
    return achados


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("caminhos", nargs="+", help="conjunto.toml ou pasta (recursiva)")
    ap.add_argument(
        "--registro", help="registry.json do índice: confere fonte e redistribuição"
    )
    ap.add_argument(
        "--espelho",
        action="store_true",
        help="imprime o JSON espelhado (publicacao.conjunto.declaracao) de um só conjunto",
    )
    args = ap.parse_args(argv)
    if args.espelho:
        if len(args.caminhos) != 1:
            print("--espelho aceita um só conjunto.toml", file=sys.stderr)
            return 2
        try:
            decl = carregar(args.caminhos[0])
        except DeclaracaoInvalida as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(decl.espelho(), ensure_ascii=False, indent=2))
        return 0
    fontes = ler_registro(Path(args.registro)) if args.registro else None
    ok = True
    validas: list[Declaracao] = []
    for alvo in _alvos(args.caminhos):
        try:
            decl = carregar(alvo, fontes=fontes)
        except DeclaracaoInvalida as exc:
            ok = False
            print(exc, file=sys.stderr)
            continue
        validas.append(decl)
        tabelas = ", ".join(decl.tabela(v) for v in decl.visoes)
        print(f"ok  {decl.id} ({decl.estado}): {tabelas}")
    for problema in tabelas_duplicadas(validas):
        ok = False
        print(f"duplicidade: {problema}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
