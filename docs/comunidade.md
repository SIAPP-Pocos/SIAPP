# Base comunitária

O SIAPP é a ferramenta; o repositório [SIAPP-dados](https://github.com/SIAPP-Pocos/SIAPP-dados)
é a base. O que uma pessoa corrige ou transcreve vira um **pacote de contribuição**; os
pacotes aceitos são compilados numa **base** que todo mundo baixa.

```
  SIAPP (você)                    SIAPP-dados (GitHub)                 SIAPP (outra pessoa)
  ─────────────                   ────────────────────                 ────────────────────
  corrige o OCR,                  pull request com o pacote            Comunidade →
  transcreve dados   ──exporta──▶ validação automática  ──etiqueta──▶  Atualizar a base
  (origem local)                  revisão humana          vAAAA.MM.N    (origem base)
                                  compilação → Release
```

## O pacote (formato v2)

Arquivo JSON em `ambiente_teste/contribuicoes/AAAA-MM-DD_sobrenome_siapp.json`:

| Campo | Conteúdo |
|---|---|
| `id`, `criado_em`, `siapp_versao`, `licenca` | identificação; licença sempre CC-BY-4.0 |
| `autor` | nome (obrigatório), instituição, ORCID |
| `vocabulario.correcoes` | `{de, para}`: forma lida pelo OCR → forma escrita no papel |
| `vocabulario.palavras` | termos técnicos (atalhos de busca e referência para a correção) |
| `vocabulario.manter_original` | palavras que a correção automática não deve mexer |
| `fatos` | dado transcrito: poço, tipo, nome, profundidades, valor e **fonte** |
| `apelidos` | outras grafias do nome de um poço |

A fonte de um fato tem tudo o que um revisor precisa para conferir sem o pacote trazer
o documento: `sha256` e `caminho_remoto` do arquivo no REATE, `pagina` e `caixa`
(`[x0, y0, x1, y1]`, frações da largura e da altura da imagem da página).

**Nada do REATE vai no pacote.** O acervo continua sendo baixado do portal público.

## Regras que o SIAPP e o validador do SIAPP-dados aplicam

- Correção global de **número ou palavra de 1–2 letras é recusada**: trocar "87" por "83"
  em todos os documentos estragaria valores certos. Números entram como fatos, página a página.
- Profundidade entre −100 e 12.000 m; base nunca acima do topo.
- Correções que discordam entre autores e o mesmo fato enviado por autores diferentes
  são **conflitos**: o validador mostra os dois autores e a revisão decide, olhando a imagem.

## Importar o pacote de outra pessoa

Aba Comunidade → **Escolher pacote…**. Antes de gravar, o SIAPP mostra:

- o que entra (correções, palavras, dados transcritos);
- o que você já tem;
- as correções que **discordam** das suas — e a sua continua valendo (local > pacote > base).

Cada pacote importado pode ser **desfeito** inteiro. "O OCR estava certo" também vale
contra correções da comunidade, só no seu computador.

## Base comunitária

**Atualizar pela internet** baixa a Release mais recente do SIAPP-dados
(`siapp-dados.sqlite`) e substitui tudo o que tinha origem `base`. Enquanto o repositório
for privado, use **Importar de arquivo…** com o `.sqlite` gerado por
`python ferramentas/compilar.py` no SIAPP-dados.

O formato da base (`versao_formato_base` 1) está descrito em `ferramentas/compilar.py`
do SIAPP-dados; o SIAPP recusa base de versão mais nova que a que conhece.
