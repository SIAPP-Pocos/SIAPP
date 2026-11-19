"""Ajuda "Como usar o SIAPP" (1.2): os rótulos citados existem na tela e as poses do mascote estão no lugar."""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(RAIZ, "ui")


def _ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def _sem_espacos(texto):
    return re.sub(r"\s+", "", texto)


def _texto_da_interface():
    """Texto visível do index.html (sem as tags) e os textos escritos pelos scripts, sem espaços: "1 Acervo" no
    guia bate com <span class="aba-num">1</span>Acervo."""
    html = _ler(os.path.join(UI, "index.html"))
    partes = [re.sub(r"<[^>]+>", "", html)]
    pasta_js = os.path.join(UI, "js")
    for nome in os.listdir(pasta_js):
        if nome.endswith(".js") and nome != "ajuda.js":
            partes.append(_ler(os.path.join(pasta_js, nome)))
    return _sem_espacos("\n".join(partes).replace("&amp;", "&"))


def test_rotulos_da_ajuda_existem_na_interface():
    js = _ler(os.path.join(UI, "js", "ajuda.js"))
    rotulos = set(re.findall(r"\*\*(.+?)\*\*", js))
    assert len(rotulos) > 40
    assert not any(re.match(r"\d ", r) for r in rotulos), "abas com ponto depois do número: **4. Poços**"
    tela = _texto_da_interface()
    # "4. Poços" na ajuda = <span class="aba-num">4</span>Poços na tela
    faltando = sorted(r for r in rotulos if _sem_espacos(re.sub(r"^(\d)\.", r"\1", r)) not in tela)
    assert not faltando, f"rótulos do guia que não aparecem na tela: {faltando}"


def test_cada_assunto_tem_uma_pose_que_existe():
    js = _ler(os.path.join(UI, "js", "ajuda.js"))
    poses = set(re.findall(r'pose: "(\w+)"', js))
    assert {"acenando", "apontando", "lupa", "ops"} <= poses
    for pose in poses:
        caminho = os.path.join(UI, "img", "mascote", f"{pose}.png")
        assert os.path.isfile(caminho), caminho
        assert os.path.getsize(caminho) < 60_000          # leves: a janela abre rápido
    html = _ler(os.path.join(UI, "index.html"))
    assert 'src="img/mascote/acenando.png"' in html       # o do canto do Início
    assert 'src="js/ajuda.js"' in html


def test_atalhos_da_ajuda_levam_a_abas_que_existem():
    js = _ler(os.path.join(UI, "js", "ajuda.js"))
    destinos = set(re.findall(r'ir: \["[^"]+", "(\w+)"\]', js))
    janelas = _ler(os.path.join(UI, "js", "janelas.js"))
    conhecidos = set(re.findall(r'"(\w+)"', janelas))
    assert destinos and destinos <= conhecidos, destinos - conhecidos
