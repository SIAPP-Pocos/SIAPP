"""Lançador silencioso (0.47): escolha do Python, .venv quebrada, erros claros, sinal de abertura.

Tudo com comandos falsos, sem criar .venv de verdade; roda em qualquer sistema.
"""

import os
import subprocess
import types

import pytest

from lancador import passos
from ponte import base, icone


def _res(codigo=0, saida="", erro=""):
    return types.SimpleNamespace(returncode=codigo, stdout=saida, stderr=erro)


@pytest.fixture
def pasta(tmp_path):
    for a in passos.ARQUIVOS_OBRIGATORIOS:
        f = tmp_path / a
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('__version__ = "9.9.9"\n' if a.endswith("__init__.py") else "x", encoding="utf-8")
    return str(tmp_path)


@pytest.fixture
def py_falso(tmp_path_factory):
    """Um executável que existe (o conteúdo não importa: os comandos são simulados)."""
    f = tmp_path_factory.mktemp("py") / "python.exe"
    f.write_text("x")
    return str(f)


def _criar_venv_falsa(pasta):
    py = passos.venv_python(pasta)
    os.makedirs(os.path.dirname(py), exist_ok=True)
    open(py, "w").close()


# ------------------------------------------------------------------------------------------------ achar Python

def test_mysql_e_atalho_da_loja_nao_servem(tmp_path, monkeypatch):
    mysql = tmp_path / "MySQL Shell" / "python.exe"
    mysql.parent.mkdir()
    mysql.write_text("x")
    chamou = []
    assert passos.python_serve(str(mysql), lambda c: chamou.append(c) or _res()) is False and not chamou

    loja = tmp_path / "Microsoft" / "WindowsApps"
    loja.mkdir(parents=True)
    (loja / "python.exe").write_text("x")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert passos.python_serve(str(loja / "python.exe"), lambda c: _res()) is False


def test_python_serve_so_se_o_teste_passa(tmp_path):
    py = tmp_path / "python.exe"
    py.write_text("x")
    assert passos.python_serve(str(py), lambda c: _res(0)) is True
    assert passos.python_serve(str(py), lambda c: _res(1)) is False

    def explode(c):
        raise OSError("não executa")
    assert passos.python_serve(str(py), explode) is False
    assert passos.python_serve(str(tmp_path / "nao_existe.exe"), lambda c: _res()) is False


def test_candidatos_sem_repeticao_e_py_antes_do_where(monkeypatch):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    def executar(cmd):
        if cmd[0] == "py":
            return _res(0, "C:\\Py313\\python.exe\n")
        return _res(0, "C:\\Py313\\python.exe\nC:\\MySQL\\python.exe\n")
    lista = passos.candidatos_python(executar)
    assert lista.index("C:\\Py313\\python.exe") < lista.index("C:\\MySQL\\python.exe")
    assert len(lista) == len({os.path.normcase(c) for c in lista})


def test_achar_python_pega_o_primeiro_que_serve_e_lista_as_tentativas():
    escolhido, tentativas = passos.achar_python(["a", "b", "c"], lambda c: c == "b")
    assert escolhido == "b" and tentativas == ["falhou    a", "ok        b"]
    assert passos.achar_python(["a"], lambda c: False)[0] is None


# ---------------------------------------------------------------------------------------------- .venv e passos

def test_conferir_arquivos_diz_o_que_falta(tmp_path):
    with pytest.raises(passos.ErroLancador) as e:
        passos.conferir_arquivos(str(tmp_path))
    assert "siapp.py" in e.value.detalhe and "Baixe o SIAPP" in e.value.mensagem


def test_versao_vem_do_motor(pasta, tmp_path):
    assert passos.ler_versao(pasta) == "9.9.9"
    assert passos.ler_versao(str(tmp_path / "vazio")) == ""


def test_venv_quebrada_e_recriada_e_dependencias_instaladas(pasta, py_falso):
    _criar_venv_falsa(pasta)
    marcas = []

    def executar(cmd, cwd=None, timeout=None):
        if cmd[-2:] == ["pip", "--version"]:
            return _res(1)                                   # pasta movida: o pip da .venv antiga não roda
        if "venv" in cmd:
            _criar_venv_falsa(pasta)
            return _res(0)
        if "install" in cmd:
            marcas.append(cwd)
            return _res(0)
        return _res(0)
    textos = []
    passos.preparar_ambiente(pasta, lambda t, i: textos.append((t, i)), executar, candidatos=[py_falso])
    assert marcas == [pasta]
    assert passos.requisitos_em_dia(pasta)
    assert textos[0][0].startswith("Refazendo") and textos[0][1] is True


def test_primeira_vez_avisa_que_leva_alguns_minutos(pasta, py_falso):
    def executar(cmd, cwd=None, timeout=None):
        if "venv" in cmd:
            _criar_venv_falsa(pasta)
        return _res(0)
    textos = []
    passos.preparar_ambiente(pasta, lambda t, i: textos.append(t), executar, candidatos=[py_falso])
    assert textos[0] == passos.DICA_PRIMEIRA_VEZ and "alguns minutos" in textos[0]


def test_venv_boa_e_em_dia_nao_reinstala_nada(pasta):
    _criar_venv_falsa(pasta)
    with open(os.path.join(pasta, ".venv", ".requisitos"), "w") as f:
        f.write(passos._marca_requisitos(pasta))
    chamados = []

    def executar(cmd, cwd=None, timeout=None):
        chamados.append(cmd)
        return _res(0)
    passos.preparar_ambiente(pasta, lambda t, i: None, executar)
    assert len(chamados) == 1 and chamados[0][-2:] == ["pip", "--version"]


def test_requirements_mudou_reinstala(pasta):
    _criar_venv_falsa(pasta)
    with open(os.path.join(pasta, ".venv", ".requisitos"), "w") as f:
        f.write("antigo")
    assert passos.requisitos_em_dia(pasta) is False


def test_sem_python_bom_o_erro_lista_os_candidatos(pasta):
    with pytest.raises(passos.ErroLancador) as e:
        passos.preparar_ambiente(pasta, lambda t, i: None, lambda c, **k: _res(1), candidatos=["x.exe", "y.exe"])
    assert "Python" in e.value.mensagem and "x.exe" in e.value.detalhe and "y.exe" in e.value.detalhe


def test_falha_do_pip_mostra_o_fim_da_saida(pasta, py_falso):
    def executar(cmd, cwd=None, timeout=None):
        if "venv" in cmd:
            _criar_venv_falsa(pasta)
            return _res(0)
        if "install" in cmd:
            return _res(1, "linha\n" * 100 + "ERRO final do pip")
        return _res(0)
    with pytest.raises(passos.ErroLancador) as e:
        passos.preparar_ambiente(pasta, lambda t, i: None, executar, candidatos=[py_falso])
    assert "ERRO final do pip" in e.value.detalhe and e.value.detalhe.count("linha") <= 30
    assert not passos.requisitos_em_dia(pasta)               # não marca como pronto


def test_falha_ao_criar_venv(pasta, py_falso):
    with pytest.raises(passos.ErroLancador) as e:
        passos.preparar_ambiente(pasta, lambda t, i: None,
                                 lambda c, **k: _res(1, erro="sem permissão") if "venv" in c else _res(0),
                                 candidatos=[py_falso])
    assert "criar o ambiente" in e.value.mensagem and "sem permissão" in e.value.detalhe


# ----------------------------------------------------------------------------------------- abrir e sinalizar

class _Proc:
    def __init__(self, codigos):
        self.codigos = list(codigos)

    def poll(self):
        return self.codigos.pop(0) if len(self.codigos) > 1 else self.codigos[0]


def _relogio():
    t = [0.0]
    return (lambda s: t.__setitem__(0, t[0] + s)), (lambda: t[0])


def test_esperar_abertura_ve_o_sinal(pasta):
    sinal = passos.caminho_sinal(pasta)
    os.makedirs(os.path.dirname(sinal))
    dormir, agora = _relogio()

    def dorme_e_sinaliza(s):
        dormir(s)
        open(sinal, "w").write("ok")
    assert passos.esperar_abertura(_Proc([None]), sinal, pasta, 10, dorme_e_sinaliza, agora) is True


def test_app_que_morre_com_erro_mostra_a_saida(pasta):
    os.makedirs(os.path.dirname(passos.caminho_saida_app(pasta)))
    open(passos.caminho_saida_app(pasta), "w", encoding="utf-8").write("Traceback...\nImportError: pywebview")
    dormir, agora = _relogio()
    with pytest.raises(passos.ErroLancador) as e:
        passos.esperar_abertura(_Proc([None, 1]), passos.caminho_sinal(pasta), pasta, 10, dormir, agora)
    assert "fechou ao abrir" in e.value.mensagem and "ImportError: pywebview" in e.value.detalhe
    assert "Código de saída: 1" in e.value.detalhe


def test_app_que_fecha_sem_erro_e_sem_sinal_nao_e_falha(pasta):
    dormir, agora = _relogio()
    assert passos.esperar_abertura(_Proc([0]), passos.caminho_sinal(pasta), pasta, 10, dormir, agora) is False


def test_app_que_nunca_avisa_estoura_o_limite(pasta):
    dormir, agora = _relogio()
    with pytest.raises(passos.ErroLancador) as e:
        passos.esperar_abertura(_Proc([None]), passos.caminho_sinal(pasta), pasta, 3, dormir, agora)
    assert "demorando" in e.value.mensagem


def test_siapp_avisa_pelo_arquivo_do_ambiente(tmp_path, monkeypatch):
    monkeypatch.delenv(passos.VARIAVEL_SINAL, raising=False)
    assert passos.avisar_abertura() is False
    alvo = tmp_path / "sinal"
    monkeypatch.setenv(passos.VARIAVEL_SINAL, str(alvo))
    assert passos.avisar_abertura() is True and alvo.exists()
    monkeypatch.setenv(passos.VARIAVEL_SINAL, str(tmp_path / "nao" / "existe" / "sinal"))
    assert passos.avisar_abertura() is False                  # nunca levanta


def test_executar_segue_os_tres_passos_e_nao_abre_se_algo_falha(pasta, monkeypatch):
    eventos = []
    monkeypatch.setattr(passos, "preparar_ambiente", lambda *a, **k: None)
    monkeypatch.setattr(passos, "abrir_app", lambda p, a=(): ("proc", "sinal"))
    monkeypatch.setattr(passos, "esperar_abertura", lambda *a, **k: True)
    assert passos.executar(pasta, lambda i, t, ind: eventos.append((i, t))) is True
    assert [t for _, t in eventos] == [*passos.PASSOS, "Pronto"]

    def falha(*a, **k):
        raise passos.ErroLancador("quebrou")
    monkeypatch.setattr(passos, "preparar_ambiente", falha)
    abriu = []
    monkeypatch.setattr(passos, "abrir_app", lambda p, a=(): abriu.append(1))
    with pytest.raises(passos.ErroLancador):
        passos.executar(pasta, lambda *a: None)
    assert not abriu


def test_detalhe_completo_e_log(pasta):
    txt = passos.detalhe_completo(pasta, passos.ErroLancador("Falhou", "causa X"))
    assert "SIAPP 9.9.9" in txt and "Falhou" in txt and "causa X" in txt and "lancador.log" in txt
    txt2 = passos.detalhe_completo(pasta, RuntimeError("boom"))
    assert "Erro inesperado" in txt2 and "RuntimeError" in txt2
    passos.registrar(pasta, "linha de teste")
    assert "linha de teste" in open(passos.caminho_log(pasta), encoding="utf-8").read()


def test_comandos_ocultos_usam_create_no_window(monkeypatch):
    vistos = {}
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: vistos.update(kw) or _res())
    monkeypatch.setenv("PYTHONHOME", "x")
    passos.rodar(["a"])
    assert vistos["creationflags"] == passos.SEM_JANELA
    assert "PYTHONHOME" not in vistos["env"] and "PYTHONPATH" not in vistos["env"]


# ------------------------------------------------------------------------------------- arquivos e identidade

def test_png_do_ico_escolhe_o_tamanho():
    png = passos.png_do_ico(icone.CAMINHO_ICO, 64)
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert passos.png_do_ico(icone.CAMINHO_ICO, 9999) is not None       # maior disponível
    assert passos.png_do_ico("nao_existe.ico") is None


def test_identidade_da_janelinha_e_a_mesma_da_janela_principal():
    from lancador import janela
    assert janela.APP_ID == icone.APP_ID == "SIAPP.Pocos.SIAPP"


def test_arquivos_do_lancador_existem_e_o_atalho_nao_passa_pelo_bat():
    for nome in ("SIAPP.pyw", "SIAPP.vbs", "iniciar.bat", "SIAPP - diagnóstico.bat"):
        assert os.path.isfile(os.path.join(base.PASTA_APP, nome)), nome
    vbs = open(os.path.join(base.PASTA_APP, "SIAPP.vbs"), encoding="utf-8").read()
    assert "pyw -3" in vbs and "SIAPP.pyw" in vbs
    iniciar = open(os.path.join(base.PASTA_APP, "iniciar.bat"), encoding="utf-8").read()
    assert "wscript" in iniciar and "SIAPP.vbs" in iniciar and "pause" not in iniciar.lower()
    diag = open(os.path.join(base.PASTA_APP, "SIAPP - diagnóstico.bat"), encoding="utf-8").read()
    assert "siapp.py" in diag and "pause" in diag.lower()


def test_nenhuma_mencao_ao_nome_antigo_da_pasta():
    achados = []
    for raiz, dirs, arqs in os.walk(base.PASTA_APP):
        dirs[:] = [d for d in dirs if d not in (".venv", ".git", "ambiente_teste", "_publicar", "__pycache__",
                                                ".pytest_cache", "_backup_git")]
        for a in arqs:
            if a.endswith((".py", ".md", ".bat", ".vbs", ".pyw", ".html", ".js", ".json", ".txt", ".toml", ".yml")):
                caminho = os.path.join(raiz, a)
                if os.path.abspath(caminho) == os.path.abspath(__file__):
                    continue
                texto = open(caminho, encoding="utf-8", errors="ignore").read()
                # só CHANGELOG, CLAUDE.md e guia de teste podem citar o nome antigo (para explicar a troca)
                if "siapp.vf" in texto and a not in ("CHANGELOG.md", "CLAUDE.md", "guia-de-teste.md"):
                    achados.append(caminho)
    assert not achados


# ---------------------------------------------------------------- atualização ao abrir (0.58)
def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def clones(tmp_path):
    """Um "GitHub" (repositório nu) e a pasta do SIAPP clonada dele, na versão 0.1.0."""
    import shutil as _sh
    if not _sh.which("git"):
        pytest.skip("git ausente")
    origem, trabalho, pc = tmp_path / "origem.git", tmp_path / "trabalho", tmp_path / "SIAPP"
    _git("init", "-q", "--bare", "-b", "main", str(origem), cwd=tmp_path)
    _git("clone", "-q", str(origem), str(trabalho), cwd=tmp_path)
    for d in (trabalho,):
        _git("config", "user.email", "t@t", cwd=d)
        _git("config", "user.name", "t", cwd=d)
        _git("checkout", "-q", "-b", "main", cwd=d)
    (trabalho / "motor").mkdir()
    (trabalho / "motor" / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (trabalho / ".gitignore").write_text("ambiente_teste/\n")
    _git("add", ".", cwd=trabalho)
    _git("commit", "-qm", "0.1.0", cwd=trabalho)
    _git("push", "-q", "origin", "main", cwd=trabalho)
    _git("clone", "-q", "-b", "main", str(origem), str(pc), cwd=tmp_path)
    _git("config", "user.email", "t@t", cwd=pc)
    _git("config", "user.name", "t", cwd=pc)

    def nova_versao(v):
        (trabalho / "motor" / "__init__.py").write_text(f'__version__ = "{v}"\n')
        _git("commit", "-qam", v, cwd=trabalho)
        _git("push", "-q", "origin", "main", cwd=trabalho)
    return pc, nova_versao


def test_atalho_traz_a_versao_nova_quando_e_seguro(clones):
    pc, nova_versao = clones
    assert passos.atualizar_codigo(str(pc))["situacao"] == "em_dia"
    nova_versao("0.2.0")
    textos = []
    r = passos.atualizar_codigo(str(pc), textos.append)
    assert r["situacao"] == "atualizado" and (r["de"], r["para"]) == ("0.1.0", "0.2.0")
    assert passos.ler_versao(str(pc)) == "0.2.0" and textos
    passos.guardar_aviso_atualizacao(str(pc), r)
    assert os.path.isfile(passos.caminho_aviso_atualizacao(str(pc)))
    # os dados do usuário (ambiente_teste, fora do git) não atrapalham
    (pc / "ambiente_teste").mkdir(exist_ok=True)
    (pc / "ambiente_teste" / "projeto.sqlite").write_text("x")
    nova_versao("0.3.0")
    assert passos.atualizar_codigo(str(pc))["situacao"] == "atualizado"


def test_atalho_nao_mexe_quando_ha_mudanca_local_ou_esta_desligado(clones):
    pc, nova_versao = clones
    nova_versao("0.2.0")
    (pc / "motor" / "__init__.py").write_text('__version__ = "0.1.0-meu"\n')        # mexeram no código à mão
    r = passos.atualizar_codigo(str(pc))
    assert r["situacao"] == "mudado" and passos.ler_versao(str(pc)) == "0.1.0-meu"
    _git("checkout", "-q", "--", ".", cwd=pc)
    (pc / "local.txt").write_text("x")
    _git("add", "local.txt", cwd=pc)
    _git("commit", "-qm", "local", cwd=pc)                                           # commit que o GitHub não tem
    assert passos.atualizar_codigo(str(pc))["situacao"] == "divergente"
    (pc / "ambiente_teste").mkdir(exist_ok=True)
    (pc / "ambiente_teste" / "preferencias.json").write_text('{"atualizar_ao_abrir": false}')
    assert passos.atualizar_codigo(str(pc))["situacao"] == "desligado"


def test_sem_git_ou_sem_internet_abre_a_versao_da_pasta(clones, tmp_path):
    pc, _ = clones
    assert passos.atualizar_codigo(str(tmp_path))["situacao"] == "sem_git"           # pasta sem .git
    assert passos.atualizar_codigo(str(pc), git=str(tmp_path / "nao-existe"))["situacao"] == "sem_conexao"

    def sem_rede(cmd, cwd=None, timeout=None):
        return subprocess.CompletedProcess(cmd, 128, "", "fatal: unable to access")
    assert passos.atualizar_codigo(str(pc), executar=sem_rede)["situacao"] == "sem_conexao"
