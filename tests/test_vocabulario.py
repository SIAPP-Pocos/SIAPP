"""Correção de texto de OCR. Os casos vêm da auditoria em 55 páginas reais (7-GMR-13-RN)."""
import os

import pytest

from motor import vocabulario as mv

BASE = mv.ler_base(os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "vocabulario_base.json"))


@pytest.fixture
def corretor():
    return mv.Corretor(BASE, mv.projeto_vazio())


@pytest.mark.parametrize("ocr,certo", [
    ("cimonto", "cimento"), ("BARIGIRAS", "BARREIRAS"), ("CECULACÃO", "CIRCULAÇÃO"),
    ("Clmantação", "Cimentação"), ("PISTOSEIO", "PISTONEIO"), ("CIMENTAÇA", "CIMENTAÇÃO")])
def test_corrige_erros_reais_de_ocr(corretor, ocr, certo):
    assert corretor.corrigir(f"x {ocr} y") == f"x {certo} y"


@pytest.mark.parametrize("certa", [
    "AMOSTRAS", "LATERAIS", "CANHONEADO", "ESTÁTICO", "Completado", "RELATIVA", "FLUIDOS"])
def test_nao_estraga_palavra_certa(corretor, certa):
    """Regressão: a 1ª versão trocava todas estas (plural, gênero, particípio, palavra parecida)."""
    assert corretor.corrigir(certa) == certa


def test_numeros_nunca_sao_corrigidos_automaticamente(corretor):
    assert corretor.corrigir("PROFUNDIDADE 1834,0 m 30.11.87 288") == "PROFUNDIDADE 1834,0 m 30.11.87 288"


def test_segmentos_marcam_original_e_tipo(corretor):
    seg = [s for s in corretor.segmentos("BARIGIRAS e cimonto") if isinstance(s, dict)]
    assert seg == [{"t": "BARREIRAS", "orig": "BARIGIRAS", "tipo": "auto"},
                   {"t": "cimento", "orig": "cimonto", "tipo": "auto"}]


def test_correcao_do_usuario_tem_prioridade_e_aceita_codigo_de_poco():
    proj = {"palavras": [], "correcoes": {"T-GRMAA3-RN": "7-GRM-13-RN", "BARIGIRAS": "BARRERAS"}, "ignorar": []}
    c = mv.Corretor(BASE, proj)
    assert c.corrigir("1 po T-GRMAA3-RN BARIGIRAS") == "1 po 7-GRM-13-RN BARRERAS"


def test_ignorar_desfaz_correcao_automatica():
    c = mv.Corretor(BASE, {"palavras": [], "correcoes": {}, "ignorar": ["COLINA"]})
    assert c.corrigir("COLINA") == "COLINA"


def test_palavra_do_usuario_vira_referencia():
    c = mv.Corretor(BASE, {"palavras": ["Tubarão"], "correcoes": {}, "ignorar": []})
    assert c.corrigir("Tubanão") == "Tubarão"


@pytest.mark.parametrize("titulo,confiavel", [
    ("RELATÓRIO GEOLÓGICO QUINZENAL", True), ("— DADOS DE REVESTIMENTO", True),
    ("— pADOS DE TAMPÕES DE CIMENTO", True), ("POÇO: 7-GMR-13-RN", True),
    ("TRANSA EEE EM IREEN CAS add ERASMO AAA", False), ("< sc E SC ADA DZ /2/7: a A VESENNA AE", False),
    ("o' To 7URO1ANONAA DO LUTTEIZDIOTOTLI oieee O", False), ("", False)])
def test_titulo_confiavel(titulo, confiavel):
    assert mv.titulo_confiavel(titulo) is confiavel
