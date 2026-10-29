# Perfis já processados pela operadora

*SIAPP 0.41 — bloco 9, item 5.* Código: `motor/operador.py`; famílias em `recursos/mnemonicos.json`.

Parte do acervo do REATE traz, além das curvas medidas, as **curvas que a operadora calculou** na interpretação:
argilosidade (VSH, VCL), porosidade efetiva e total (PHIE, PHIT), saturação de água (SW, SWE) e, às vezes,
permeabilidade (PERM, KINT). Ficam na pasta **"Perfil Digital Processado"** (230 arquivos em 125 poços da Potiguar e
de Alagoas no levantamento de 28/10/2026) ou em arquivos com sufixo `_adic` junto dos perfis comuns
(ex.: 1-BRSA-1348-RN, com PHIE, SW e VSH).

## Famílias novas

| Família | Mnemônicos | Unidade |
|---|---|---|
| VSH — argilosidade | VSH, VCL, VSHALE, VCLAY, VSH_GR, VCLGR… | v/v (ou %) |
| PHIE — porosidade efetiva | PHIE, PHIEF, PHI_E, EPOR, PHIE_ND… | v/v (ou %) |
| PHIT — porosidade total | PHIT, PHIT_ND, TPOR… | v/v (ou %) |
| SW — saturação de água | SW, SWE, SWT, SW_AR, SUWI… | v/v (ou %) |
| PERM — permeabilidade | PERM, KINT, PERMH, PERMV… | mD |

Todas com `"interpretacao": true`. A saturação da zona lavada (SXO) não entra em SW.

## Pesquisa: quais poços já têm interpretação

O levantamento do acervo guarda a lista de curvas de cada arquivo. Por isso a pesquisa **não baixa nada**:

- ao abrir o projeto, quando o arquivo de mnemônicos muda de versão, as famílias do levantamento são refeitas a
  partir das listas guardadas (o levantamento já feito passa a conhecer as famílias novas);
- **Dados › Levantamento › "Perfis já processados pela operadora"**: quantos poços da bacia têm curva interpretada
  e o botão "Listar os poços" (poço, categoria, curvas, arquivos, ficha). "Completo" = tem Vsh, φ e Sw;
- **Mapa › Com a curva**: "interpretação da operadora (Vsh, φ ou Sw)", ou só Vsh, φ efetiva ou Sw.

## Comparação com a avaliação do SIAPP

Com o perfil processado do poço **aberto** na aba Perfis (inventariado), toda avaliação de formação desse poço
mostra, abaixo do resultado, as médias de cada intervalo:

- **no intervalo inteiro**: Vsh, φ e Sw do SIAPP ao lado dos da operadora;
- **no net pay do SIAPP**: φ e Sw das duas, só onde o SIAPP achou pay.

A curva da operadora é levada para a grade da avaliação por interpolação (sem amostra a menos de 3 passos, fica de
fora); em porcentagem (unidade % ou mediana > 1,5), vira fração. φ usa a efetiva e, sem ela, a total. Diferença
grande (Vsh ou Sw > 0,15, φ > 0,05) fica em destaque: é para olhar os parâmetros (Rw, a, m, n, GR limpo e da
argila), as curvas e os cortes — nenhuma das duas interpretações é a certa por definição.
