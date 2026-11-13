"""Fontes e prioridade do projeto (0.63) — um lugar só para configurar de onde vêm os topos e as zonas.

Até a 0.62 a ordem das fontes de **topo** mudava em Acervo › Dados consolidados (guardada no banco) e a das **zonas
produtoras** mudava no painel do Modelo 3D (só na tela, perdida ao fechar). O cálculo continua separado — topo de
formação e intervalo de reservatório são coisas diferentes (`motor/topos.py`, `motor/zonas.py`) —, mas a configuração
mora aqui: rótulos, ordem e quais fontes valem, gravados no banco do projeto.

Também aqui: os **critérios de contagem** de "perfil digital" (revisão de 11/11, A13). O mesmo app mostrava números
diferentes (4.562 × 4.557) porque cada tela contava de um jeito. Agora cada número vem com o critério ao lado, e esta
tela mostra os três lado a lado.
"""

from __future__ import annotations

import json

from . import topos as mtp
from . import zonas as mzo
from .banco import Banco

CHAVE_ZONAS = "prioridade_zonas"

EXPLICA_TOPOS = ("Na correlação e no Modelo 3D, cada unidade usa o topo da primeira fonte desta lista que o tiver. Na ficha "
                 "do poço dá para escolher outra, unidade por unidade, vendo as diferenças.")
EXPLICA_ZONAS = ("No Modelo 3D por zonas produtoras, os intervalos vêm das fontes ligadas. Quando duas fontes caem no mesmo "
                 "reservatório, vale a de cima (ou o envelope, se você escolher essa regra no Modelo 3D).")


# ------------------------------------------------------------------------------------------------------------- zonas
def zonas(banco: Banco) -> dict:
    """Ordem de todas as fontes de zona e as que estão ligadas (padrão: todas, menos a tabela sua)."""
    try:
        bruto = json.loads(banco.meta(CHAVE_ZONAS, "") or "{}")
    except (TypeError, ValueError):
        bruto = {}
    ordem = [f for f in bruto.get("ordem", []) if f in mzo.FONTES]
    ordem += [f for f in mzo.PRIORIDADE_PADRAO if f not in ordem]
    if isinstance(bruto.get("ligadas"), list):
        ligadas = {f for f in bruto["ligadas"] if f in mzo.FONTES}
    else:
        ligadas = {f for f in mzo.FONTES if f != "tabela"}
    return {"ordem": ordem, "ligadas": [f for f in ordem if f in ligadas]}


def definir_zonas(banco: Banco, ordem: list[str] | None = None, ligadas: list[str] | None = None) -> dict:
    atual = zonas(banco)
    nova_ordem = [f for f in (ordem if ordem is not None else atual["ordem"]) if f in mzo.FONTES]
    nova_ordem = list(dict.fromkeys(nova_ordem)) + [f for f in mzo.PRIORIDADE_PADRAO if f not in nova_ordem]
    lig = set(ligadas if ligadas is not None else atual["ligadas"]) & set(mzo.FONTES)
    banco.definir_meta(CHAVE_ZONAS, json.dumps({"ordem": nova_ordem, "ligadas": [f for f in nova_ordem if f in lig]}))
    return zonas(banco)


def ligar_zona(banco: Banco, fonte: str, ligar: bool = True) -> dict:
    """Liga ou desliga uma fonte sem mexer na ordem (ex.: a tabela sua, ao importar ou apagar)."""
    z = zonas(banco)
    lig = set(z["ligadas"])
    (lig.add if ligar else lig.discard)(fonte)
    return definir_zonas(banco, z["ordem"], list(lig))


def fontes_zona_em_uso(banco: Banco) -> list[str]:
    """As fontes de zona ligadas, na ordem de prioridade (o que o Modelo 3D usa quando a janela não manda outra)."""
    return zonas(banco)["ligadas"]


# ------------------------------------------------------------------------------------------------------------- tudo
def ler(banco: Banco, tem_tabela: bool = False) -> dict:
    return {
        "topos": {"ordem": mtp.precedencia(banco), "rotulos": dict(mtp.FONTES), "explicacao": EXPLICA_TOPOS},
        "zonas": {**zonas(banco), "rotulos": dict(mzo.FONTES), "explicacao": EXPLICA_ZONAS, "tem_tabela": tem_tabela},
    }


# ------------------------------------------------------------------------------------------- critérios de contagem
CRITERIOS_PERFIL = {
    "conteudo": {
        "rotulo": "perfil digital conferido no portal",
        "explicacao": "O levantamento abriu os arquivos da pasta do poço no REATE e achou DLIS, LIS ou LAS pelo conteúdo "
                      "(não só pela extensão). Precisa da bacia levantada.",
    },
    "pasta": {
        "rotulo": "pasta de perfis digitais no portal",
        "explicacao": "O poço tem, no REATE, uma pasta com nome de perfis digitais (Perfis digitais, Perfil convencional…). "
                      "Não abre os arquivos: a pasta pode ter só imagem.",
    },
    "baixado": {
        "rotulo": "perfil digital baixado",
        "explicacao": "Algum DLIS, LIS ou LAS deste poço já está no projeto (baixado e conferido pelo conteúdo).",
    },
}
ORDEM_CRITERIOS = ("conteudo", "pasta", "baixado")


def pocos_com_perfil(banco: Banco, criterio: str, bacia: str | None = None) -> set[str]:
    """Poços distintos (pelo nome do poço; a pasta do portal quando o poço não foi identificado) por critério."""
    from . import tipos_dado as mtd
    if criterio not in CRITERIOS_PERFIL:
        raise ValueError(f"Critério desconhecido: {criterio}")
    filtro, args = ("AND bacia = ?", [bacia]) if bacia else ("", [])
    with banco.leitura() as c:
        if criterio == "conteudo":
            return {r[0] or r[1] for r in c.execute(
                f"SELECT poco_id, nome_pasta FROM acervo_pocos WHERE situacao = 'digital' {filtro}", args)}
        if criterio == "baixado":
            return {r[0] for r in c.execute(
                f"SELECT DISTINCT poco_id FROM arquivos WHERE tipo = 'perfil' AND poco_id IS NOT NULL "
                f"AND poco_id != '' {filtro}", args)}
        linhas = c.execute(
            f"""SELECT DISTINCT a.pasta, p.poco_id, p.nome_pasta FROM acervo_arquivos a
                LEFT JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                {('WHERE a.bacia = ?' if bacia else '')}""", args).fetchall()
    e_perfil: dict[str, bool] = {}
    saida = set()
    for pasta, pid, nome in linhas:
        if pasta not in e_perfil:
            e_perfil[pasta] = "perfis_digitais" in mtd.tipos_da_pasta(pasta)
        if e_perfil[pasta]:
            saida.add(pid or nome)
    return saida


def contar_perfil(banco: Banco, bacia: str | None = None) -> dict:
    """Os três números de "perfil digital", cada um com o seu critério, e quanto um difere do outro."""
    conj = {k: pocos_com_perfil(banco, k, bacia) for k in ORDEM_CRITERIOS}
    linhas = [{"chave": k, **CRITERIOS_PERFIL[k], "n": len(conj[k])} for k in ORDEM_CRITERIOS]
    return {
        "bacia": bacia or "",
        "criterios": linhas,
        "so_pasta": len(conj["pasta"] - conj["conteudo"]),         # pasta com nome de perfil, sem perfil digital dentro
        "so_conteudo": len(conj["conteudo"] - conj["pasta"]),      # perfil digital fora de uma pasta com esse nome
        "baixado_ou_conteudo": len(conj["baixado"] | conj["conteudo"]),
    }


def criterio(chave: str) -> dict:
    """Rótulo e explicação de um critério, para mandar junto com um número."""
    return {"chave": chave, **CRITERIOS_PERFIL[chave]}
