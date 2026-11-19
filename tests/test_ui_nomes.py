"""Os scripts comuns da interface dividem o mesmo escopo global: um nome repetido entre dois arquivos ou quebra a
janela ao abrir (const/let: "já declarado") ou faz uma função esconder a outra em silêncio (1.3)."""
import collections
import os
import re

UI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")


def test_nenhum_nome_global_repetido_entre_os_scripts():
    with open(os.path.join(UI, "index.html"), encoding="utf-8") as f:
        html = f.read()
    # só os scripts comuns: os de type="module" têm escopo próprio
    scripts = re.findall(r'<script src="(js/[^"]+\.js)"></script>', html)
    assert len(scripts) > 10
    nomes = collections.defaultdict(list)
    for rel in scripts:
        with open(os.path.join(UI, rel), encoding="utf-8") as f:
            for linha in f:
                m = re.match(r"^(?:async\s+)?function\s+(\w+)|^(?:const|let|var|class)\s+(\w+)", linha)
                if m:
                    nomes[m.group(1) or m.group(2)].append(rel)
    repetidos = {n: arqs for n, arqs in nomes.items() if len(arqs) > 1}
    assert not repetidos, repetidos
