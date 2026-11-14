"""Fixture do registro de fetchers, para derivar o caminho do ``lake.py``.

Por padrão o registro é a cópia mínima abaixo, sem rede. Com
``QUANTILICA_REGISTRO_PUBLICO=1`` os testes leem o registro público pela função
de cache do ``quantilica-cli`` (``quantilica.cli.sources.registro_publico``).
"""

from __future__ import annotations

import os
from typing import Any

import pytest

_BASE = "https://github.com/Quantilica"

# Recorte do registro v2: só `id`, `repo` e `module` das fontes de lake_aliases.toml.
_FETCHERS = {
    "b3": "b3_fetcher",
    "cvm": "cvm_fetcher",
    "comex": "comex_fetcher",
    "bcb-microdados": "bcb_microdados_fetcher",
    "rfb-cnpj": "rfb_cnpj_fetcher",
    "tesouro-direto": "tesouro_direto_fetcher",
    "pdet": "pdet_fetcher",
    "anac": "anac_fetcher",
}

REGISTRO_FIXTURE: dict[str, Any] = {
    "version": 2,
    "fetchers": [
        {"id": fid, "module": module, "repo": f"{_BASE}/{fid}-fetcher"}
        for fid, module in _FETCHERS.items()
    ],
}


@pytest.fixture(scope="session")
def registro() -> dict[str, Any]:
    if os.environ.get("QUANTILICA_REGISTRO_PUBLICO") == "1":
        from quantilica.cli.sources import registro_publico

        doc = registro_publico()
        if not doc:
            pytest.skip("registro público indisponível (sem cli, rede ou cache)")
        return doc
    return REGISTRO_FIXTURE
