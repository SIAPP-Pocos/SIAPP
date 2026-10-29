# Topos de formação de várias fontes: comparar e escolher

*SIAPP 0.45.* Código: `motor/topos.py`; tabela `escolhas` (migração 11).

O mesmo topo pode vir de até quatro fontes:

| Fonte | De onde | Observação |
|---|---|---|
| AGP | AGP da ANP (levantamento do acervo) | topo interpretado pela operadora, com fonte e qualidade |
| Transcrito | você (Documentos › transcrição, Perfis › marcar topo) ou a comunidade | dado com página de origem |
| RFP | topos constatados do Relatório Final de Poço | alguns RFP não trazem o nome: o topo ganha o nome da formação da calha mais perto, até 10 m (um para um) |
| Calha (PAG) | primeira amostra de cada formação na descrição de calha | o topo real fica entre a amostra de cima e essa (3 ou 9 m) |

## Como as fontes se juntam

A **unidade** de cada candidato sai do nome: "FM AÇU", "Formação Açu", "Açu" e a sigla ACU do AGP viram a mesma
chave (a sigla do `recursos/estratigrafia.json`, quando a unidade está lá; senão, o nome sem acento e sem o prefixo de
nível). De cada fonte vale o topo mais raso da unidade.

## Qual vale

1. A **escolha do usuário** para aquela unidade naquele poço (Ficha do poço › "Topos de formação — compare as fontes e
   escolha"): uma fonte, ou "não usar".
2. Sem escolha, a **ordem do projeto** (Dados › Dados consolidados › "Topos: qual fonte vale quando você não
   escolhe"). Padrão: **AGP → transcrito → RFP → calha** — onde há AGP, nada muda em relação às versões anteriores.

A ficha mostra, por unidade, o topo de cada fonte, a **diferença** entre a maior e a menor (em vermelho acima de 5 m),
o topo usado (em negrito) e de qual documento veio cada valor (ao passar o mouse). Toda escolha fica registrada no
histórico do projeto (`siapp.json`).

## Onde o topo efetivo é usado

- **Seção estratigráfica**: os poços com topo de qualquer fonte entram na lista e no corredor; a coluna "fonte" de
  cada unidade diz de onde veio. Sem AGP, a mesa rotativa e a profundidade final vêm do cadastro ou dos formulários.
- **Bloco 3D**: as mesmas unidades.
- O datum da seção pode ser qualquer unidade efetiva.

No 1-BRSA-1304-BA (sem AGP), os 10 topos do RFP, nomeados pela calha, viram a coluna do poço; as duas fontes diferem
até 6 m (Pojuca: RFP 453, calha 459 m).
