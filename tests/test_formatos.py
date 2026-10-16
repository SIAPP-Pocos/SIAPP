"""Formato pelo conteúdo: o REATE tem DLIS com extensão .tif."""
import os

import pymupdf

from motor import formatos

# começo real de 5PX__0011__RN_5PX__0011__RN.tif (5-PX-11-RN, Perfil Convencional)
SUL_DLIS = b"   1V1.00RECORD16384RECALL TO DLIS DATA TRANSFER STORAGE SET ID " + b" " * 16


def escrever(pasta, nome, conteudo):
    caminho = os.path.join(pasta, nome)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho


def test_reconhece_pelo_conteudo(tmp_path):
    t = str(tmp_path)
    pdf = pymupdf.open()
    pdf.new_page()
    assert formatos.formato(escrever(t, "a.tif", SUL_DLIS + b"\x00" * 200)) == "dlis"
    assert formatos.formato(escrever(t, "b.pdf", pdf.tobytes())) == "pdf"
    assert formatos.formato(escrever(t, "c.dat", b"II*\x00" + b"\x00" * 20)) == "tif"
    assert formatos.formato(escrever(t, "d.txt", b"# comentario\r\n~VERSION INFORMATION\r\n")) == "las"
    assert formatos.formato(escrever(t, "e.lis", b"\x00\x84\x00\x00")) == "lis"   # sem assinatura: extensão
    assert formatos.formato(escrever(t, "f.xyz", b"qualquer coisa")) == ""
    assert formatos.tipo(os.path.join(t, "a.tif")) == "perfil"
    assert formatos.tipo(os.path.join(t, "nao-existe.tif")) == "documento"   # sem arquivo: extensão
    assert formatos.tipo(os.path.join(t, "f.xyz")) == "outro"


def test_dlis_com_extensao_tif_vai_para_perfis(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", "5-PX-11-RN", "Perfil Convencional")
    os.makedirs(pasta)
    escrever(pasta, "5PX__0011__RN_5PX__0011__RN.tif", SUL_DLIS + b"\x00" * 200)
    rel = "bruto/Potiguar/5-PX-11-RN/Perfil Convencional/5PX__0011__RN_5PX__0011__RN.tif"
    # projeto de antes da 0.11.1: o banco registrou o arquivo como documento, pela extensão
    api._banco.registrar_arquivo(rel, bacia="Potiguar", poco_id="5-PX-11-RN", tipo="documento")
    api._abrir_projeto(api._projeto.pasta)
    assert api._banco.arquivo(rel)["tipo"] == "perfil"
    assert api.documentos()["documentos"] == []
    p = api.perfis()["perfis"]
    assert [(x["nome"], x["formato"]) for x in p] == [("5PX__0011__RN_5PX__0011__RN.tif", "dlis")]
    r = api.ver_pagina(rel, 1)
    assert not r["ok"] and "aba Perfis" in r["erro"]
