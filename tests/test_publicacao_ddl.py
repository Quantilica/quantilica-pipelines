"""Criador das tabelas de dados (`ferramentas/quantilica_publicacao/publicacao_ddl.py`).

Sem banco: o DDL de cada visão das declarações do catálogo sai do espelho e bate com as
colunas do contrato da consulta; o módulo só importa biblioteca padrão e SQLAlchemy (é
carregado pelo caminho do arquivo, fora de qualquer pacote); e `publicacao_registro.sql`
(o DDL do registro, conferido contra a migração do portal pelo teste de paridade dele)
declara as quatro tabelas. O portal guarda uma cópia idêntica do módulo.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FERRAMENTAS = ROOT / "ferramentas" / "quantilica_publicacao"
ARQUIVO = FERRAMENTAS / "publicacao_ddl.py"
PUBLICACAO = ROOT / "publicacao"


def _carregar():
    spec = importlib.util.spec_from_file_location("publicacao_ddl_pipelines", ARQUIVO)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["publicacao_ddl_pipelines"] = mod
    spec.loader.exec_module(mod)
    return mod


ddl = _carregar()


def test_modulo_so_importa_biblioteca_padrao_e_sqlalchemy():
    arvore = ast.parse(ARQUIVO.read_text(encoding="utf-8"))
    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados |= {a.name.split(".")[0] for a in no.names}
        elif isinstance(no, ast.ImportFrom):
            assert no.level == 0, "import relativo impede carregar pelo caminho"
            importados.add((no.module or "").split(".")[0])
    assert importados <= set(sys.stdlib_module_names) | {"sqlalchemy"}


def test_ddl_de_cada_visao_do_exemplo_tem_as_colunas_do_contrato():
    espelho = json.loads((PUBLICACAO / "_exemplo.json").read_text(encoding="utf-8"))
    assert espelho["visoes"]
    for visao in espelho["visoes"]:
        nivel = visao["nivel"]
        instrucoes = ddl.sql_criar_tabela(espelho, nivel)
        assert instrucoes[0].upper().startswith("CREATE TABLE")
        sql = " ".join(instrucoes)
        for coluna in ddl.colunas_da_tabela(espelho, nivel):
            assert re.search(rf"\b{re.escape(coluna)}\b", sql), coluna
        assert visao["tabela"] in sql


def test_registro_de_referencia_declara_as_quatro_tabelas():
    sql = (FERRAMENTAS / "publicacao_registro.sql").read_text(encoding="utf-8")
    for tabela in ("conjunto", "medida", "entidade", "carga"):
        assert f"CREATE TABLE IF NOT EXISTS publicacao.{tabela} " in sql
