"""Versão e dependências declaradas num lugar só, sem divergência."""
import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_requirements_igual_ao_pyproject():
    tomllib = pytest.importorskip("tomllib")
    with open(os.path.join(RAIZ, "pyproject.toml"), "rb") as f:
        deps = tomllib.load(f)["project"]["dependencies"]
    with open(os.path.join(RAIZ, "requirements.txt"), encoding="utf-8") as f:
        req = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    assert sorted(deps) == sorted(req)


def test_versao_no_changelog():
    from motor import __version__
    with open(os.path.join(RAIZ, "CHANGELOG.md"), encoding="utf-8") as f:
        assert f"## [{__version__}]" in f.read(), "Registre a versão no CHANGELOG.md"


def test_versao_semver():
    from motor import __version__
    assert re.fullmatch(r"0\.\d+\.\d+", __version__), "Versões 0.x até o lançamento"
