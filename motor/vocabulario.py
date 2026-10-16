"""
Vocabulário e correção de texto de OCR.

Duas fontes de palavras:
  - recursos/vocabulario_base.json     dicionário de domínio que vem com o SIAPP
  - <projeto>/texto/vocabulario_projeto.json   o que o usuário adiciona pela janela:
        "palavras":  termos próprios (viram atalho de busca e alvo de correção)
        "correcoes": {"BARIGIRAS": "BARREIRAS", ...}  correções explícitas
        "ignorar":   tokens que a correção automática NÃO deve mexer

Regras de segurança da correção:
  1. O OCR original nunca é alterado. A correção é uma camada por cima,
     refeita a qualquer momento a partir do original.
  2. A correção AUTOMÁTICA só mexe em palavras feitas só de letras, com 6+
     letras. Números nunca são corrigidos automaticamente — um número
     "corrigido" para outro número plausível é o pior erro possível.
  3. Correção automática só acontece se houver UM candidato claro no
     vocabulário (mesma inicial, até 1 letra de diferença no tamanho,
     até 1 erro em palavras de 6–8 letras ou 2 erros em 9+). Empate = não corrige.
  4. NÃO corrige flexão: se a diferença está só na terminação (-S, -IS, -ADO,
     -O/-A…), a palavra provavelmente está certa (AMOSTRAS, CANHONEADO,
     ESTÁTICO). Auditado nos 55 textos reais do 7-GMR-13-RN em 15/10/2026.
  5. Toda palavra corrigida fica marcada, com o original, para conferência.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata

_RE_PALAVRA = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")


def normalizar(texto: str) -> str:
    """Sem acento e em maiúsculas: chave de comparação."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn").upper()


def distancia(a: str, b: str, limite: int) -> int:
    """Distância de edição (Levenshtein), parando cedo se passar do limite."""
    if abs(len(a) - len(b)) > limite:
        return limite + 1
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        atual = [i] + [0] * len(b)
        menor = i
        for j, cb in enumerate(b, 1):
            atual[j] = min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb))
            menor = min(menor, atual[j])
        if menor > limite:
            return limite + 1
        anterior = atual
    return anterior[-1]


def limite_erros(n_letras: int) -> int:
    return 0 if n_letras < 6 else (1 if n_letras <= 8 else 2)


# Terminações de flexão/derivação. Se token e candidato só diferem nelas,
# é variante legítima (plural, gênero, particípio), não erro de OCR.
_SUFIXOS = {"", "S", "ES", "IS", "NS", "L", "M", "O", "A", "OS", "AS", "DO", "DA",
            "DOS", "DAS", "ADO", "ADA", "ADOS", "ADAS", "IDO", "IDA", "IO", "AO",
            "CAO", "COES", "OES", "R", "RA", "RAM", "NDO"}


def variante_de_flexao(token: str, candidato: str) -> bool:
    """AMOSTRAS/AMOSTRA, LATERAIS/LATERAL, CANHONEADO/CANHONEIO → True.
    CIMENTACA/CIMENTACAO (letras faltando no fim do token) → False: é erro."""
    k = 0
    while k < min(len(token), len(candidato)) and token[k] == candidato[k]:
        k += 1
    resto_t, resto_c = token[k:], candidato[k:]
    if not resto_t:                      # token é começo do candidato: truncado pelo OCR
        return False
    return len(token) - len(resto_t) >= 4 and resto_t in _SUFIXOS and resto_c in _SUFIXOS


def _no_estilo(modelo: str, palavra: str) -> str:
    """Escreve `palavra` com a mesma caixa do `modelo` (MAIÚSCULA, Título, minúscula)."""
    if modelo.isupper():
        return palavra.upper()
    if modelo[:1].isupper():
        return palavra[:1].upper() + palavra[1:].lower()
    return palavra.lower()


# ================================================================ arquivos
def ler_base(caminho: str) -> dict:
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f).get("categorias", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def projeto_vazio() -> dict:
    return {"palavras": [], "correcoes": {}, "ignorar": []}


def ler_projeto(caminho: str) -> dict:
    try:
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return projeto_vazio()
    return {**projeto_vazio(), **d}


# ================================================================ corretor
class Corretor:
    def __init__(self, base: dict, projeto: dict):
        self.base = base
        self.projeto = projeto
        termos = [t for lista in base.values() for t in lista] + list(projeto.get("palavras", []))
        # palavra normalizada -> forma de exibição (com acento)
        self.vocab: dict[str, str] = {}
        for termo in termos:
            for p in _RE_PALAVRA.findall(termo):
                if len(p) >= 6:
                    self.vocab.setdefault(normalizar(p), p)
        self.ignorar = {normalizar(t) for t in projeto.get("ignorar", [])}
        self.correcoes = {normalizar(k): v for k, v in projeto.get("correcoes", {}).items() if k.strip()}
        # explícitas podem ter número/hífen ("T-GRMAA3-RN") → casamento por token inteiro
        self._re_explicitas = None
        if self.correcoes:
            chaves = sorted(projeto["correcoes"], key=len, reverse=True)
            self._re_explicitas = re.compile(
                r"(?<![\w-])(" + "|".join(re.escape(k) for k in chaves if k.strip()) + r")(?![\w-])",
                re.IGNORECASE)
        self._cache: dict[str, str | None] = {}

    def _candidato(self, palavra: str) -> str | None:
        chave = normalizar(palavra)
        if chave in self._cache:
            return self._cache[chave]
        res = None
        lim = limite_erros(len(chave))
        if lim and chave not in self.vocab and chave not in self.ignorar:
            achados = []
            for v in self.vocab:
                if v[0] != chave[0] or abs(len(v) - len(chave)) > 1:
                    continue
                d = distancia(chave, v, lim)
                if d <= lim:
                    achados.append((d, v))
            if achados:
                achados.sort()
                if len(achados) == 1 or achados[0][0] < achados[1][0]:   # sem empate
                    if not variante_de_flexao(chave, achados[0][1]):
                        res = self.vocab[achados[0][1]]
        self._cache[chave] = res
        return res

    def segmentos(self, texto: str) -> list:
        """Texto dividido em pedaços: str (inalterado) ou
        {"t": corrigido, "orig": lido pelo OCR, "tipo": "usuario"|"auto"}."""
        pedacos: list = []
        pos = 0
        explicitas = list(self._re_explicitas.finditer(texto)) if self._re_explicitas else []
        cortes = [(m.start(), m.end(), "usuario", m.group(0)) for m in explicitas]
        ocupado = [(a, b) for a, b, _, _ in cortes]
        for m in _RE_PALAVRA.finditer(texto):
            if any(a <= m.start() < b for a, b in ocupado):
                continue
            cand = self._candidato(m.group(0))
            if cand and normalizar(cand) != normalizar(m.group(0)):
                cortes.append((m.start(), m.end(), "auto", m.group(0)))
        for ini, fim, tipo, orig in sorted(cortes):
            if ini > pos:
                pedacos.append(texto[pos:ini])
            novo = (self.correcoes[normalizar(orig)] if tipo == "usuario"
                    else _no_estilo(orig, self._candidato(orig)))
            pedacos.append({"t": novo, "orig": orig, "tipo": tipo})
            pos = fim
        if pos < len(texto):
            pedacos.append(texto[pos:])
        return pedacos

    def corrigir(self, texto: str) -> str:
        return "".join(p if isinstance(p, str) else p["t"] for p in self.segmentos(texto))

    def palavras_chave(self) -> dict:
        """Categorias de atalhos de busca (base + as do usuário)."""
        cats = dict(self.base)
        if self.projeto.get("palavras"):
            cats = {"Minhas palavras": list(self.projeto["palavras"]), **cats}
        return cats


def titulo_confiavel(titulo: str) -> bool:
    """Descarta títulos que são ruído de OCR. Ruído típico: letras triplicadas
    (EEE), maiúsculas e minúsculas misturadas no meio da palavra (aceaBagech,
    SiSILiDADE), dígitos dentro da palavra (Z6lsÁ), palavra sem vogal, ou
    poucas letras úteis no meio de símbolos ("< sc E SC ADA DZ /2/7:")."""
    sem_espaco = re.sub(r"\s", "", titulo)
    if not sem_espaco:
        return False
    palavras = [re.sub(r"^[^A-Za-zÀ-ÿ0-9]+|[^A-Za-zÀ-ÿ0-9]+$", "", w) for w in titulo.split()]
    palavras = [w for w in palavras if len(w) >= 3]
    if not palavras:
        return False
    letras = [c for w in palavras for c in w if c.isalpha()]
    titulo_maiusculo = sum(c.isupper() for c in letras) >= 0.7 * max(len(letras), 1)

    def ruim(w: str) -> bool:
        if re.fullmatch(r"\d{1,2}-[A-Z]{2,5}-\d{1,4}[A-Z]{0,2}-[A-Z]{2}", w):
            return False                                  # código de poço (7-GMR-13-RN)
        if not re.fullmatch(r"[A-Za-zÀ-ÿ]+", w):
            return True                                   # dígito ou símbolo no meio
        if re.search(r"(.)\1\1", w.upper()):
            return True                                   # EEE, AAA
        if w.isupper() and len(w) <= 4:
            return False                                  # sigla (GMR, PSI)
        if not re.search(r"[AEIOUaeiouÀ-ÿ]", w):
            return True
        if titulo_maiusculo and not w.isupper() and not w[1:].isupper():
            return True                                   # só a 1ª letra trocada (pADOS) é tolerada                                   # 'add', 'capeÇA' num título em caixa alta
        if not titulo_maiusculo and not (w.islower() or w.istitle()):
            return True
        return False

    ruins = sum(ruim(w) for w in palavras)
    uteis = sum(len(w) for w in palavras if not ruim(w))
    return ruins <= 0.3 * len(palavras) and uteis >= 0.4 * len(sem_espaco)
