"""Arquivos baixados (0.54): tudo o que está em `ambiente_teste/bruto/`, de qualquer formato, com o que o SIAPP fez com cada um.

A lista vem do **disco** (o que de fato está lá), cruzada com o banco do projeto: tipo e data do download (`arquivos`), perfis
inventariados (`perfis`), leituras de dados do poço (`leituras`, `dados_poco`) e texto extraído de documentos. Nada aqui lê o
conteúdo dos arquivos, só o começo (1 KB) dos `.tif` que o banco não conhece, para saber se é imagem ou perfil.

**Apagar** manda o arquivo para a Lixeira do Windows (dá para restaurar) e tira do banco o que foi *derivado* dele: leituras,
dados do poço, perfil inventariado, índice de busca, texto extraído. O trabalho **seu** (transcrições em `fatos` e correções
de página em `paginas_revisadas`) nunca é apagado: continua no banco, citando o arquivo de origem.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
from datetime import datetime

from . import dados_poco as mdp
from . import formatos
from . import pocos as mpo
from .banco import Banco

NOME_REGISTRO = "registro_downloads.json"

# Programas e scripts: o SIAPP nunca os abre (só "Mostrar na pasta"). Um arquivo baixado de fora pode ter qualquer nome.
EXECUTAVEIS = {".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".psm1", ".psd1", ".vbs", ".vbe", ".js", ".jse",
               ".wsf", ".wsh", ".hta", ".lnk", ".jar", ".reg", ".dll", ".sys", ".cpl", ".pif", ".msc", ".appx", ".msix",
               ".gadget", ".application", ".url", ".chm", ".iso", ".vhd", ".vhdx"}

CATEGORIAS = {"documento": "Documento (PDF, imagem)", "perfil": "Perfil de poço", "planilha": "Planilha",
              "sismica": "Sísmica (SEG-Y)", "texto": "Texto / dados (txt, json, xml)", "compactado": "Compactado (zip…)",
              "outro": "Outro"}
_POR_EXTENSAO = {
    ".xls": "planilha", ".xlsx": "planilha", ".xlsm": "planilha", ".csv": "planilha", ".ods": "planilha",
    ".sgy": "sismica", ".segy": "sismica",
    ".txt": "texto", ".json": "texto", ".xml": "texto", ".md": "texto", ".dat": "texto", ".asc": "texto",
    ".zip": "compactado", ".rar": "compactado", ".7z": "compactado", ".gz": "compactado", ".tar": "compactado",
    ".doc": "documento", ".docx": "documento", ".rtf": "documento", ".ppt": "documento", ".pptx": "documento",
    ".dwg": "outro",
}
ROTULOS_EXT = {".pdf": "PDF", ".xls": "Excel (.xls)", ".xlsx": "Excel (.xlsx)", ".xlsm": "Excel (.xlsm)", ".csv": "CSV",
               ".sgy": "SEG-Y", ".segy": "SEG-Y", ".txt": "texto", ".json": "JSON", ".xml": "XML", ".zip": "ZIP",
               ".rar": "RAR", ".7z": "7-Zip", ".dlis": "DLIS", ".lis": "LIS", ".las": "LAS", ".tif": "imagem TIFF",
               ".tiff": "imagem TIFF", ".png": "imagem PNG", ".jpg": "imagem JPEG", ".jpeg": "imagem JPEG",
               ".doc": "Word", ".docx": "Word", ".dat": "dados", ".asc": "texto ASCII"}

# O que cada leitor alimenta, em palavras simples
ONDE_LEITOR = {"cdpe": "Ficha do poço (formulários da ANP)", "pressoes": "Ficha do poço › Pressões",
               "pvt": "Ficha do poço › PVT", "pag": "Ficha do poço › PAG (lama e calha)",
               "checkshot": "Ficha do poço › Sísmica de poço; Perfis (tempo)", "geoquimica": "Ficha do poço › Geoquímica",
               "petrofisica": "Ficha do poço › Petrofísica de testemunho; Avaliação (comparação)"}
ONDE_PERFIL = "Aba Perfis; Avaliação de formação; Seção"
LEVANTAMENTO = {"agp": ("AGP lido pelo levantamento (topos de formação, lama, testes)", "Seção; Bloco 3D; Ficha (topos); Avaliação"),
                "direcionais": ("Trajetória do poço lida pelo levantamento", "Bloco 3D (poços desviados)"),
                "esquemas": ("Esquema de ferramentas lido pelo levantamento (OCR)", "Perfis (rótulos das corridas); Ficha")}
ONDE_TEXTO = "Aba Documentos (busca e leitura)"


def pode_abrir(nome: str) -> bool:
    return os.path.splitext(nome)[1].lower() not in EXECUTAVEIS


def rotulo_formato(ext: str, formato_perfil: str | None = None) -> str:
    if formato_perfil:
        nome = formatos.NOMES.get(formato_perfil, formato_perfil.upper())
        return nome if ext == f".{formato_perfil}" else f"{nome} (em {ext or 'sem extensão'})"
    return ROTULOS_EXT.get(ext, f"arquivo {ext}" if ext else "arquivo sem extensão")


def categoria(ext: str, tipo_banco: str | None, formato_perfil: str | None) -> str:
    if formato_perfil or tipo_banco == "perfil" or ext in (".dlis", ".lis", ".las"):
        return "perfil"
    if tipo_banco == "documento" or ext in (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        return "documento"
    return _POR_EXTENSAO.get(ext, "outro")


# ----------------------------------------------------------------------------------------------------------------- lista
def _contextos(projeto, banco: Banco) -> dict:
    with banco.conexao() as c:
        arquivos = {r["rel"]: dict(r) for r in c.execute(
            "SELECT rel, bacia, poco_id, tipo, baixado_em, caminho_remoto FROM arquivos")}
        perfis = {r["rel"]: dict(r) for r in c.execute("SELECT rel, formato, n_curvas, erro FROM perfis")}
        leituras = {r["rel"]: dict(r) for r in c.execute("SELECT rel, leitor, n, erro FROM leituras")}
        tipos_dados: dict[str, dict[str, int]] = {}
        for r in c.execute("SELECT rel, tipo, COUNT(*) n FROM dados_poco GROUP BY rel, tipo"):
            tipos_dados.setdefault(r["rel"], {})[r["tipo"]] = r["n"]
        # AGP, dados direcionais e esquemas de ferramentas são lidos pelo levantamento, por outro caminho (tabelas
        # próprias, ligadas ao arquivo pelo caminho no portal)
        remotos: dict[tuple, tuple] = {}
        for tabela, rotulo in (("agp", "agp"), ("direcionais", "direcionais"), ("esquemas", "esquemas")):
            for r in c.execute(f"SELECT bacia, caminho, erro FROM {tabela}"):
                remotos[(r["bacia"], r["caminho"])] = (rotulo, r["erro"])
    return {"arquivos": arquivos, "perfis": perfis, "leituras": leituras, "tipos_dados": tipos_dados, "remotos": remotos,
            "texto": projeto.resumo_texto(), "registro": projeto.registro_downloads()}


def _situacao(rel: str, nome: str, ext: str, cat: str, ctx: dict, remoto: tuple | None = None) -> tuple[str, str, str]:
    """(estado, frase, onde o dado aparece)."""
    if nome.endswith(".part"):
        return "incompleto", "Download incompleto (pode ser retomado ou apagado).", ""
    onde = []
    estado, frase = "sem_leitor", "O SIAPP ainda não lê este tipo de arquivo (dá para abri-lo e usar fora)."
    lei = ctx["leituras"].get(rel)
    per = ctx["perfis"].get(rel)
    tex = ctx["texto"].get(rel)
    if lei:
        if lei["erro"]:
            return "erro", f"Erro ao ler: {lei['erro']}", ""
        leitor = mdp.LEITORES.get(lei["leitor"])
        nomes = [mdp.TIPOS.get(t, t) for t in sorted(ctx["tipos_dados"].get(rel, {}))]
        estado = "lido"
        frase = f"Lido: {lei['n']} dado(s)" + (f" ({', '.join(nomes)})" if nomes else "")
        onde.append(ONDE_LEITOR.get(lei["leitor"], getattr(leitor, "NOME", lei["leitor"])))
    if per:
        if per["erro"]:
            return "erro", f"Perfil com erro: {per['erro']}", ""
        estado = "perfil" if estado == "sem_leitor" else estado
        frase = (frase + "; " if estado == "lido" else "") + f"Perfil inventariado ({per['n_curvas'] or 0} curvas)"
        onde.append(ONDE_PERFIL)
    if tex:
        estado = "texto" if estado == "sem_leitor" else estado
        modo = f"{tex.get('ocr', 0)} por OCR" if tex.get("ocr") else "texto embutido"
        frase = (frase + "; " if frase and estado != "texto" else "") + f"Texto extraído ({tex.get('n_paginas', '?')} págs., {modo})"
        onde.append(ONDE_TEXTO)
    lev = ctx["remotos"].get(remoto) if remoto else None
    if lev and estado == "sem_leitor":
        if lev[1]:
            return "erro", f"Erro ao ler: {lev[1]}", ""
        estado, frase = "lido", LEVANTAMENTO[lev[0]][0]
        onde.append(LEVANTAMENTO[lev[0]][1])
    if estado == "sem_leitor":
        leitor = mdp.leitor_para(rel)
        if leitor:
            estado, frase = "pendente", f"Pode ser lido ({mdp.LEITORES[leitor].NOME.split('(')[0].strip()}): abra o projeto para ler."
        elif cat == "documento" and ext in (".pdf", ".tif", ".tiff"):
            estado, frase = "pendente", "Ainda não processado: Documentos › Processar."
        elif cat == "perfil":
            estado, frase = "pendente", "Perfil ainda não aberto: aba Perfis."
    return estado, frase, "; ".join(dict.fromkeys(onde))


def listar(projeto, banco: Banco) -> dict:
    """Todos os arquivos de `bruto/`, com tipo, formato, tamanho, data e situação."""
    ctx = _contextos(projeto, banco)
    por_nome: dict[str, str] = {}
    saida = []
    base = projeto.pasta_bruto
    registro_por_rel = {v.get("arquivo_local"): v for v in ctx["registro"].values() if isinstance(v, dict)}
    for raiz, dirs, nomes in os.walk(base):
        dirs.sort()
        for nome in sorted(nomes):
            caminho = os.path.join(raiz, nome)
            sob = os.path.relpath(caminho, base).split(os.sep)
            if len(sob) == 1 and nome == NOME_REGISTRO:
                continue
            rel = projeto.rel(caminho)
            try:
                st = os.stat(caminho)
            except OSError:
                continue
            ext = os.path.splitext(nome)[1].lower()
            reg = ctx["arquivos"].get(rel) or {}
            per = ctx["perfis"].get(rel)
            tipo_banco = reg.get("tipo") or None
            if not tipo_banco and ext in (".tif", ".tiff"):
                tipo_banco = formatos.tipo(caminho)                       # 1 KB: imagem ou perfil em envelope
            cat = categoria(ext, tipo_banco, per["formato"] if per else None)
            bacia = sob[0] if len(sob) > 1 else ""
            poco = sob[1] if len(sob) > 2 else ""
            pasta = "/".join(sob[2:-1]) if len(sob) > 3 else ""
            if poco not in por_nome:
                por_nome[poco] = reg.get("poco_id") or (mpo.resolver(banco, poco) if poco else "")
            remoto = (reg.get("bacia"), reg.get("caminho_remoto")) if reg.get("caminho_remoto") else None
            estado, frase, onde = _situacao(rel, nome, ext, cat, ctx, remoto)
            quando = reg.get("baixado_em") or (registro_por_rel.get(rel) or {}).get("baixado_em") \
                or datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
            saida.append({"rel": rel, "bacia": bacia, "poco": poco, "poco_id": reg.get("poco_id") or por_nome[poco],
                          "pasta": pasta, "nome": nome, "ext": ext, "bytes": st.st_size, "data": quando,
                          "categoria": cat, "formato": rotulo_formato(ext, per["formato"] if per else None),
                          "estado": estado, "situacao": frase, "onde": onde, "pode_abrir": pode_abrir(nome),
                          "registrado": rel in ctx["arquivos"]})
    return {"arquivos": saida, "n": len(saida), "bytes": sum(a["bytes"] for a in saida),
            "categorias": CATEGORIAS, "bacias": sorted({a["bacia"] for a in saida if a["bacia"]})}


# ---------------------------------------------------------------------------------------------------------------- Lixeira
class _SHFILEOPSTRUCT(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("wFunc", ctypes.c_uint), ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", ctypes.c_int),
                ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", ctypes.c_wchar_p)]


def enviar_para_lixeira(caminho: str) -> str:
    """Manda o arquivo para a Lixeira do Windows (dá para restaurar). Devolve "lixeira". Fora do Windows apaga de vez
    ("apagado"), só para os testes. Nunca apaga de vez no Windows: se a Lixeira falhar, levanta OSError."""
    caminho = os.path.abspath(caminho)
    if sys.platform != "win32":
        os.remove(caminho)
        return "apagado"
    op = _SHFILEOPSTRUCT()
    op.wFunc = 3                                    # FO_DELETE
    op.pFrom = caminho + "\0"                       # lista terminada em duplo nulo (o ctypes põe o segundo)
    op.fFlags = 0x0040 | 0x0010 | 0x0400 | 0x0004   # ALLOWUNDO | NOCONFIRMATION | NOERRORUI | SILENT
    r = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if r != 0 or op.fAnyOperationsAborted:
        raise OSError(f"O Windows não conseguiu mandar o arquivo para a Lixeira (código {r}).")
    return "lixeira"


# ---------------------------------------------------------------------------------------------------------------- apagar
def impacto(projeto, banco: Banco, rel: str) -> dict:
    """O que acontece se o arquivo for apagado: o que sai (derivado) e o que fica (trabalho seu)."""
    with banco.conexao() as c:
        n = lambda sql: c.execute(sql, (rel,)).fetchone()[0]                                   # noqa: E731
        derivado = {"dados_do_poco": n("SELECT COUNT(*) FROM dados_poco WHERE rel = ?"),
                    "leitura": n("SELECT COUNT(*) FROM leituras WHERE rel = ?"),
                    "perfil_inventariado": n("SELECT COUNT(*) FROM perfis WHERE rel = ?"),
                    "texto_extraido": 1 if rel in projeto.resumo_texto() else 0}
        seu = {"transcricoes": n("SELECT COUNT(*) FROM fatos WHERE fonte_rel = ?"),
               "paginas_corrigidas": n("SELECT COUNT(*) FROM paginas_revisadas WHERE rel = ?")}
    return {"sai": derivado, "fica": seu}


def _limpar_registro(projeto, rel: str) -> int:
    reg = projeto.registro_downloads()
    antes = len(reg)
    reg = {k: v for k, v in reg.items() if not (isinstance(v, dict) and v.get("arquivo_local") == rel)}
    if len(reg) != antes:
        from .projeto import salvar_json
        salvar_json(projeto.caminho_registro, reg)
    return antes - len(reg)


def apagar(projeto, banco: Banco, rel: str, indice=None, enviar=None) -> dict:
    """Manda o arquivo para a Lixeira e limpa o que o SIAPP derivou dele. O trabalho do usuário fica."""
    caminho = projeto.caminho_seguro(rel)                                       # recusa o que está fora de bruto/
    rel = projeto.rel(caminho)
    if os.path.basename(caminho) == NOME_REGISTRO and os.path.dirname(caminho) == projeto.pasta_bruto:
        raise ValueError("Este arquivo é o registro de procedência dos downloads: o SIAPP precisa dele.")
    if os.path.isdir(caminho):
        raise ValueError("Isto é uma pasta: apague arquivo por arquivo.")
    efeito = impacto(projeto, banco, rel)
    destino = "ausente"
    if os.path.isfile(caminho):
        destino = (enviar or enviar_para_lixeira)(caminho)
    with banco.conexao() as c:
        for tabela in ("dados_poco", "leituras", "curvas", "perfis", "arquivos"):
            c.execute(f"DELETE FROM {tabela} WHERE rel = ?", (rel,))
    if indice is not None:
        indice.remover_documento(rel)
    texto = projeto.caminho_texto(rel)
    if os.path.isfile(texto):
        os.remove(texto)
    resumo = projeto.resumo_texto()
    if rel in resumo:
        from .projeto import salvar_json
        resumo.pop(rel)
        salvar_json(projeto.caminho_resumo_texto, resumo)
    _limpar_registro(projeto, rel)
    return {"rel": rel, "destino": destino, **efeito}
