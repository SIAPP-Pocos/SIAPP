"""Banco do projeto: migrações, vocabulário com origens, fatos e pacotes."""
import json
import sqlite3

from motor import banco as mb
from motor import vocabulario as mv


def test_esquema_criado_uma_vez_e_reaberto(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    assert b.versao_esquema == len(mb.MIGRACOES)
    b.vocab_definir("palavra", "Pendência")
    b2 = mb.Banco(str(tmp_path / "p.sqlite"))           # reabrir não refaz nem apaga
    assert b2.vocab_local()["palavras"] == ["Pendência"]


def test_precedencia_local_pacote_base(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    b.vocab_definir("correcao", "BARIGIRAS", "BARREIRAS", origem="base", pacote="v1")
    b.vocab_definir("correcao", "CANHONElO", "CANHONEIO", origem="pacote", pacote="x")
    b.vocab_definir("correcao", "CANHONElO", "CANHONEADO", origem="base", pacote="v1")
    ef = b.vocab_efetivo()
    assert ef["correcoes"] == {"BARIGIRAS": "BARREIRAS", "CANHONElO": "CANHONEIO"}
    assert ef["origens"] == {"BARIGIRAS": "base", "CANHONELO": "pacote"}
    b.vocab_definir("correcao", "barigiras", "BARREIRA")            # o usuário manda
    assert b.vocab_efetivo()["correcoes"]["barigiras"] == "BARREIRA"
    assert b.vocab_efetivo()["origens"]["BARIGIRAS"] == "local"


def test_o_ocr_estava_certo_vale_contra_a_comunidade(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    b.vocab_definir("correcao", "RELATIVA", "ROTATIVA", origem="base", pacote="v1")
    b.vocab_definir("ignorar", "RELATIVA")
    assert b.vocab_efetivo()["correcoes"] == {}


def test_corretor_distingue_usuario_e_comunidade(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    b.vocab_definir("correcao", "BARIGIRAS", "BARREIRAS", origem="base", pacote="v1")
    b.vocab_definir("correcao", "T-GRMAA3-RN", "7-GMR-13-RN")
    c = mv.Corretor({}, b.vocab_efetivo())
    tipos = {s["t"]: s["tipo"] for s in c.segmentos("FM BARIGIRAS POCO T-GRMAA3-RN")
             if isinstance(s, dict)}
    assert tipos == {"BARREIRAS": "comunidade", "7-GMR-13-RN": "usuario"}


def test_migra_vocabulario_json_uma_vez(tmp_path):
    j = tmp_path / "vocabulario_projeto.json"
    j.write_text(json.dumps({"palavras": ["Açu"], "correcoes": {"BARIGIRAS": "BARREIRAS"},
                             "ignorar": ["AMOSTRAS"]}), encoding="utf-8")
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    assert b.migrar_vocab_json(str(j)) == 3
    assert b.migrar_vocab_json(str(j)) == 0              # segunda vez não duplica
    assert b.vocab_local() == {"palavras": ["Açu"], "correcoes": {"BARIGIRAS": "BARREIRAS"},
                               "ignorar": ["AMOSTRAS"]}
    assert j.exists()                                    # o JSON antigo fica como cópia


def test_fatos_e_desfazer_pacote(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    meu = b.salvar_fato({"poco_id": "7-GMR-13-RN", "tipo": "topo_formacao", "nome": "Açu",
                         "prof_topo": 512.0, "caixa": [0.1, 0.2, 0.3, 0.25]})
    b.salvar_fato({"poco_id": "7-GMR-13-RN", "tipo": "topo_formacao", "nome": "Jandaíra",
                   "prof_topo": 10.0, "origem": "pacote", "pacote": "p1"})
    fs = b.fatos("7-GMR-13-RN")
    assert [f["nome"] for f in fs] == ["Jandaíra", "Açu"]       # ordenados por profundidade
    assert fs[1]["caixa"] == [0.1, 0.2, 0.3, 0.25]
    assert b.remover_fato(fs[0]["id"]) == 0                     # da comunidade: não se apaga avulso
    assert b.desfazer_pacote("p1")["fatos"] == 1
    assert [f["id"] for f in b.fatos()] == [meu]


def test_check_de_origem(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    try:
        b.vocab_definir("correcao", "X", "Y", origem="qualquer")
        assert False, "origem inválida deveria ser recusada"
    except sqlite3.IntegrityError:
        pass
