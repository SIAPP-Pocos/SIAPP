# Levantamento do acervo

Aba **Mapa → Levantamento do acervo**. Responde, para uma bacia inteira ou algumas
categorias: **quais poços têm perfil digital, quais só têm imagem e quais não têm perfil** —
olhando o conteúdo dos arquivos, sem baixá-los.

## Como funciona

1. **Listagem.** Para cada categoria, o SIAPP pede ao portal a árvore inteira de cada pasta
   "parte" numa requisição só (WebDAV `PROPFIND` com `Depth: infinity`). Uma parte com 100
   poços (1.739 itens) volta em ~3 s. Se o portal recusar, lista poço a poço.
2. **Classificação.** Para cada arquivo que pode ser perfil (dentro de uma pasta de perfis —
   `Perfil Convencional`, `Perfis_digitais`… — ou com extensão de perfil), lê **só o primeiro
   1 KB** (`Range: bytes=0-1023`; o portal responde `206`) e reconhece o formato pela
   assinatura (`motor/formatos.py`):

   | Começo do arquivo | Formato |
   |---|---|
   | `   1V1.00RECORD` | DLIS |
   | 8 bytes zero + posição do próximo bloco | envelope TIF de fita → LIS (ou DLIS) dentro |
   | registro físico LIS (tipo 128–133) | LIS |
   | `~V` | LAS |
   | `II*\0` / `MM\0*` | imagem TIFF |
   | `%PDF` | PDF |

   Por padrão só lê o que o nome não garante (sobretudo `.tif`); `.dlis`, `.lis`, `.las` e
   `.pdf` confiam na extensão. A opção **Conferir também `.dlis` e `.las`** lê todos.
3. **Situação do poço:** *perfil digital* (algum DLIS/LIS/LAS), *só imagem* (só TIFF/PDF na
   pasta de perfis), *sem perfil* (nenhum arquivo de perfil) ou *falta conferir* (o
   levantamento foi interrompido antes de ler algum `.tif`).

### Lista de curvas (opcional)

Com **Listar as curvas**, o SIAPP lê até 256 KB de cada DLIS/LIS (32 KB de LAS). DLIS e LIS
descrevem os canais antes dos dados, então o `dlisio` lê o pedaço cortado e devolve os
mnemônicos; cada um é classificado na família (GR, RHOB, NPHI, DT…, de
`recursos/mnemonicos.json`). Arquivos com várias corridas repetem a descrição mais adiante:
nesse caso a lista é **parcial** (a ficha mostra "N curva(s)+"). Exemplo medido: no
`1-AURI-12-RN_AIT_P.DLIS` (192 MB), os 685 canais já estão nos primeiros 256 KB.

## Custo

| | Requisições | Dados |
|---|---|---|
| Listagem de uma categoria com N partes | N + 1 | ~5 KB por poço |
| Classificação | 1 por arquivo ambíguo | 1 KB cada |
| Com lista de curvas | 1 por arquivo de perfil | até 256 KB cada |

Entre requisições o SIAPP espera 0,3 s (cortesia com o servidor). A Bacia Potiguar
(~8.800 pastas de poço no catálogo) lista em poucos minutos; a classificação depende de
quantos `.tif` houver. **Cancelar** guarda o que já foi lido; levantar de novo continua de
onde parou, e só relê um arquivo se o tamanho dele mudou no portal.

## Resultados

- Painel com a fração de poços por situação, a tabela "o nome engana" (ex.: `.tif → LIS`),
  as famílias de curvas e a divisão por categoria.
- Mapa: **Cor dos poços → levantamento do acervo**, filtros **No acervo** e **Com a curva**.
- Ficha do poço: cada arquivo de perfil com o formato real e, se listadas, as curvas.
- **Exportar CSV** grava em `ambiente_teste/exportacoes/levantamento/`:
  `levantamento_<bacia>_<data>_pocos.csv` (um poço por linha, com `tem_GR`, `tem_RHOB`…,
  coordenadas da ANP) e `_arquivos.csv` (um arquivo por linha, extensão × formato real).

Tudo fica no banco do projeto (`acervo_pocos`, `acervo_arquivos`) e alimenta também o
catálogo de pastas do REATE (a lista "No portal REATE" da ficha).
