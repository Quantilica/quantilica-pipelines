"""Validações offline dos pipelines DuckDB do catálogo.

O ``quantilica sql validate`` confere a estrutura dos TOMLs, mas não olha dentro do SQL.
Estes testes fecham a lacuna:

* toda view ``fonte.alias`` lida por um pipeline ativo é um alias conhecido do lake
  (``tests/lake_aliases.toml``);
* nenhum SQL de pipeline ativo usa ``SELECT *``;
* todo pipeline comentado no manifest explicita a dependência upstream (regra 5.4.3 do
  plano de expansão de datasets).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.toml"
ALIASES_FILE = Path(__file__).resolve().parent / "lake_aliases.toml"

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_STRING = re.compile(r"'(?:[^']|'')*'")
_TABLE_REF = re.compile(
    r"\b(?:FROM|JOIN)\s+([A-Za-z_]\w*)\.([A-Za-z_]\w*)", re.IGNORECASE
)
_SELECT_STAR = re.compile(
    r"\bSELECT\s+(?:ALL\s+|DISTINCT\s+)?(?:\w+\.)?\*", re.IGNORECASE
)
_COMMENTED_PIPELINE = re.compile(r"^#\s*\[pipelines\.(\w+)\]", re.MULTILINE)
_COMMENTED_PATH = re.compile(r'^#\s*path\s*=\s*"([^"]+)"', re.MULTILINE)


def strip_sql(text: str) -> str:
    """Remove comentários e literais de texto, que podem conter FROM/SELECT soltos."""
    text = _BLOCK_COMMENT.sub(" ", text)
    text = _LINE_COMMENT.sub(" ", text)
    return _STRING.sub("''", text)


def table_refs(sql: str) -> set[str]:
    """Referências ``schema.nome`` após FROM/JOIN, em minúsculas."""
    return {
        f"{schema}.{name}".lower()
        for schema, name in _TABLE_REF.findall(strip_sql(sql))
    }


def has_select_star(sql: str) -> bool:
    return bool(_SELECT_STAR.search(strip_sql(sql)))


def load_manifest() -> dict:
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))


def pipeline_sql_files(path: str, default_engine: str) -> list[tuple[Path, str]]:
    """SQLs de um pipeline: ``(arquivo, engine)`` de tabelas e prelude."""
    pipeline_dir = ROOT / path
    config_file = pipeline_dir / "transform.toml"
    if not config_file.is_file():
        return []
    config = tomllib.loads(config_file.read_text(encoding="utf-8"))
    files: list[tuple[Path, str]] = []
    if "prelude" in config:
        files.append((pipeline_dir / config["prelude"], default_engine))
    for table in config.get("table", []):
        files.append((pipeline_dir / table["sql"], table.get("engine", default_engine)))
    return files


def active_sql_files() -> list[tuple[str, Path, str]]:
    """``(pipeline, arquivo, engine)`` de todos os pipelines ativos do manifest."""
    found = []
    for name, spec in load_manifest()["pipelines"].items():
        for sql_file, engine in pipeline_sql_files(spec["path"], spec["engine"]):
            found.append((name, sql_file, engine))
    return found


def load_aliases() -> dict[str, dict]:
    return tomllib.loads(ALIASES_FILE.read_text(encoding="utf-8"))["sources"]


def known_views() -> set[str]:
    views = set()
    for source, info in load_aliases().items():
        for alias in info["aliases"] + info.get("legacy_aliases", []):
            views.add(f"{source}.{alias}")
    return views


def workspace_root() -> Path | None:
    """Pasta do workspace Quantilica (a que contém os fetchers), se houver."""
    for parent in ROOT.parents:
        if (parent / "b3-fetcher").is_dir():
            return parent
    return None


def test_manifest_has_active_duckdb_pipelines():
    sqls = [item for item in active_sql_files() if item[2] == "duckdb"]
    assert sqls, "nenhum SQL DuckDB ativo encontrado: o teste ficaria vazio"


def test_active_sql_files_exist():
    missing = [str(f) for _, f, _ in active_sql_files() if not f.is_file()]
    assert not missing, f"SQL declarado e inexistente: {missing}"


def test_active_duckdb_views_are_known_aliases():
    known = known_views()
    unknown: dict[str, set[str]] = {}
    for pipeline, sql_file, engine in active_sql_files():
        if engine != "duckdb":
            continue  # engine postgres lê tabelas do banco, não views do lake
        refs = table_refs(sql_file.read_text(encoding="utf-8"))
        bad = {ref for ref in refs if ref not in known}
        if bad:
            unknown[f"{pipeline}:{sql_file.relative_to(ROOT)}"] = bad
    assert not unknown, (
        "views fora de tests/lake_aliases.toml (confirme o alias no lake.py do "
        f"fetcher): {unknown}"
    )


def test_no_select_star_in_active_sql():
    offenders = [
        str(sql_file.relative_to(ROOT))
        for _, sql_file, _ in active_sql_files()
        if has_select_star(sql_file.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"SELECT * em SQL ativo: {offenders}"


def commented_pipelines() -> list[tuple[str, str, str]]:
    """``(nome, path, texto do bloco)`` dos pipelines comentados no manifest."""
    text = MANIFEST.read_text(encoding="utf-8")
    matches = list(_COMMENTED_PIPELINE.finditer(text))
    blocks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        path = _COMMENTED_PATH.search(block)
        blocks.append((match.group(1), path.group(1) if path else "", block))
    return blocks


def test_commented_pipelines_state_upstream_dependency():
    blocks = commented_pipelines()
    assert blocks, "esperava os marts M1..M5 comentados no manifest"
    for name, _, block in blocks:
        assert "Dependência upstream:" in block, (
            f"pipeline comentado {name!r} sem 'Dependência upstream:'"
        )


def test_commented_pipelines_keep_sql_and_hide_transform_toml():
    """O SQL é preservado; o TOML fica desabilitado para o validador não cobrá-lo."""
    for name, path, _ in commented_pipelines():
        pipeline_dir = ROOT / path
        assert path and pipeline_dir.is_dir(), f"{name}: path ausente ou inexistente"
        assert (pipeline_dir / "transform.toml.disabled").is_file(), name
        assert not (pipeline_dir / "transform.toml").exists(), (
            f"{name}: transform.toml presente, mas o pipeline está fora do manifest"
        )
        assert list(pipeline_dir.glob("*.sql")), f"{name}: SQL removido"


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        (
            "SELECT a FROM b3.cotahist c JOIN cvm.fi_cad USING (x)",
            {"b3.cotahist", "cvm.fi_cad"},
        ),
        ("-- FROM b3.fake\nSELECT 1 /* JOIN x.y */ FROM t", set()),
        ("SELECT 'FROM a.b' AS s FROM t", set()),
        ("SELECT * FROM cte", set()),
    ],
)
def test_table_refs_ignores_comments_and_strings(sql, expected):
    assert table_refs(sql) == expected


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT * FROM t", True),
        ("select distinct * from t", True),
        ("SELECT t.* FROM t", True),
        ("SELECT count(*) FROM t", False),
        ("-- SELECT * FROM t\nSELECT a FROM t", False),
        ("SELECT a, b FROM t UNION ALL SELECT a, b FROM u", False),
    ],
)
def test_select_star_detection(sql, expected):
    assert has_select_star(sql) is expected


def test_literal_aliases_match_fetcher_lake_py():
    """Confere o arquivo de aliases com o ``lake.py`` do fetcher, quando ele existe."""
    root = workspace_root()
    if root is None:
        pytest.skip("workspace Quantilica ausente: sem fetchers ao lado do repositório")
    checked = 0
    for source, info in load_aliases().items():
        literals = info.get("literal_aliases", [])
        lake_py = root / info["lake_py"]
        if not literals or not lake_py.is_file():
            continue
        text = lake_py.read_text(encoding="utf-8")
        missing = [a for a in literals if f'"{a}"' not in text]
        assert not missing, (
            f"{source}: aliases {missing} não aparecem em {info['lake_py']}"
        )
        checked += 1
    assert checked, "nenhum lake.py conferido"
