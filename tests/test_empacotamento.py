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
    assert re.fullmatch(r"[1-9]\d*\.\d+\.\d+", __version__), "Desde a 1.0 (16/11/2026): 1.x.y"


def test_citation_na_versao_atual():
    from motor import __version__
    with open(os.path.join(RAIZ, "CITATION.cff"), encoding="utf-8") as f:
        texto = f.read()
    assert f'version: "{__version__}"' in texto, "Atualize a versão no CITATION.cff"
    assert "license: AGPL-3.0-only" in texto


def test_pasta_dos_projetos_escolhida_no_instalador():
    from ponte import base
    r = base.resolver_pasta_dados
    docs, app = r"C:\Users\x\Documents", r"C:\clone\SIAPP"
    assert r("", False, "", docs, app) == app                                       # pelo código: a pasta do clone
    assert r("", True, "", docs, app).endswith("SIAPP") and r("", True, "", docs, app).startswith(docs)
    assert r("", True, r"D:\Meus projetos\SIAPP", docs, app) == r"D:\Meus projetos\SIAPP"   # escolhida no instalador
    assert r("", True, "relativa", docs, app).startswith(docs)                     # caminho incompleto: ignora
    assert r(r"E:\teste", True, r"D:\x", docs, app) == r"E:\teste"                  # SIAPP_DADOS ganha de tudo
    with open(os.path.join(RAIZ, "instalador", "siapp.iss"), encoding="utf-8") as f:
        iss = f.read()
    assert "pasta_dados.txt" in iss and base.ARQUIVO_PASTA_DADOS == "pasta_dados.txt" and "/PASTADADOS=" in iss


def test_assinatura_signpath_preparada():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ler = lambda *p: open(os.path.join(raiz, *p), encoding="utf-8").read()
    politica = ler("CODE_SIGNING_POLICY.md")
    # exigências da SignPath Foundation: o termo, o crédito, papéis e privacidade
    assert "Code signing policy" in politica
    assert "Free code signing provided by [SignPath.io]" in politica and "SignPath Foundation" in politica
    assert "Aprovadores" in politica and "Privacy policy" in politica
    readme = ler("README.md")
    assert "CODE_SIGNING_POLICY.md" in readme and "Free code signing provided by" in readme
    fluxo = ler(".github", "workflows", "instalador.yml")
    for slug in ("programa", "instalador"):
        assert f"artifact-configuration-slug: {slug}" in fluxo
        xml = ler("instalador", "signpath", f"{slug}.xml")
        assert "http://signpath.io/artifact-configuration/v1" in xml and "<authenticode-sign/>" in xml
    assert 'pe-file path="SIAPP.exe"' in ler("instalador", "signpath", "programa.xml")
    assert "para-assinar/instalador.exe" in fluxo and 'pe-file path="instalador.exe"' in ler("instalador", "signpath", "instalador.xml")
    # sem o segredo, nada de assinatura (e só com etiqueta)
    assert "secrets.SIGNPATH_API_TOKEN != ''" in fluxo and "startsWith(github.ref, 'refs/tags/v')" in fluxo
    assert "VersionInfoProductName=SIAPP" in ler("instalador", "siapp.iss")
    assert "StringStruct('ProductName', 'SIAPP')" in ler("instalador", "versao.modelo.txt")
