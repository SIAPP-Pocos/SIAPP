# Arquitetura

## Visão geral

```
┌──────────────────────────── janela (pywebview) ─────────────────────────────┐
│  ui/index.html + ui/js/<aba>.js        HTML, CSS e JavaScript puros           │
│        │  window.pywebview.api.<função>()        ▲ eventoDownload(…)          │
│        ▼                                         │ eventoDocumento(…)         │
│                                                  │ eventoLevantamento(…)      │
│  ponte/  API da janela, uma parte por aba (catalogo, pocos, documentos,       │
│          vocabulario, fatos, perfis, comunidade, levantamento, secao,         │
│          ferramentas, bloco, externos) — valida,                                        │
│          chama o motor, devolve dicionários; nunca deixa exceção chegar ao JS │
└──────────────┬───────────────────────────────────────────────────────────────┘
               ▼
  motor/  (não conhece a interface; pode ser usado por script ou notebook)
    reate.py        portal REATE via WebDAV          banco.py       projeto.sqlite
    downloads.py    fila em segundo plano            pocos.py       nome canônico, cadastro ANP
    documentos.py   texto/OCR, índice FTS5           perfis.py      DLIS/LIS/LAS → metros
    vocabulario.py  correção de OCR em camadas       comunidade.py  pacotes e base
    projeto.py      pasta de projeto, procedência    registro.py    siapp.log
    formatos.py     formato pelo conteúdo (1 KB)     levantamento.py  acervo da bacia, sem baixar
    avaliacao.py    Vsh, φ, Sw, net pay no intervalo-alvo (registro em execucoes/)
    agp.py          AGP da ANP: topos, lama, testes, litologia (tabelas agp, agp_unidades)
    secao.py        seção estratigráfica pelos topos do AGP → SVG (PNG/PDF pelo PyMuPDF)
    secao_classica.py  estilo clássico: padrões de rocha, carimbo, mapa de localização
    bloco.py        bloco 3D: contorno convexo, Delaunay, superfícies de topo (só numpy) → janela com three.js
    bloco_solido.py bloco fechado: limites das camadas em grade (topo a topo ou espessuras), malha do contorno, perfil A–A′
    interpolacao.py linear, IDW, spline, krigagem, tendência + krigagem; variograma; "sem um poço" de cada um; escalas
    bloco_validacao.py deixar um poço de fora, comparação dos métodos (tabela, figura) e prognóstico
    bloco_mapas.py  grade UTM regular → GeoTIFF (escrito à mão, chaves GeoTIFF do EPSG) e XYZ
    bloco_eclipse.py deck ECLIPSE: GRDECL corner-point em UTM, FIPNUM, PORO/NTG, poços; o resto em .inc provisórios
    bloco_volumetria.py rocha × N/G × φ × (1 − Sw) por formação, cada parâmetro com a origem
    bloco_glb.py    glTF binário (JSON + buffer) do bloco fechado
    utm.py          SIRGAS 2000 / UTM, séries de Krüger (6ª ordem)
    bloco_figura.py figura estática do bloco (SVG → PDF/PNG pelo PyMuPDF)
    producao.py     produção da ANP por campo (por poço, por zona, PD) → producao_poco, producao_zona, campos_anp
    camadas.py      camadas geográficas: EPE (ArcGIS REST), ANP (zip), IBGE BC250 (Range) → sig/*.geojson
    direcionais.py  dados direcionais: 5 leiautes, curvatura mínima (tabela direcionais)
    ferramentas.py  esquemas de ferramentas: tipo da corrida, ferramentas, vínculo com os perfis (tabela esquemas)
               ▼
  ambiente_teste/  — pasta de projeto (contrato entre as partes)
```

## O banco do projeto

`ambiente_teste/projeto.sqlite` tem **o mesmo modelo de dados da base comunitária**.
Em vez de "dados locais" e "dados da comunidade" em lugares diferentes, cada linha
diz de onde veio:

| `origem` | O que é | Como sai |
|---|---|---|
| `local` | feito neste computador | é exportado como contribuição |
| `pacote` | veio de um pacote importado (com o id do pacote) | "Desfazer" remove o pacote inteiro |
| `base` | veio da base comunitária publicada | substituído a cada atualização da base |

Precedência quando discordam: **local > pacote > base**. Exportar = "o que é local";
importar = inserir com outra origem. Um código só para os dois lados.

| Tabela | Conteúdo |
|---|---|
| `vocab` | palavras, correções de OCR e exceções ("o OCR estava certo") |
| `pocos` | cadastro oficial da ANP, uma linha por poço; `id` = nome canônico |
| `apelidos` | outras grafias → id canônico (nome do operador, nomes de arquivo antigos) |
| `reate` | pastas de poço vistas no portal (bacia, categoria, parte, caminho) |
| `arquivos` | arquivos baixados, com caminho no portal, data e SHA-256 |
| `perfis`, `curvas` | inventário dos DLIS/LIS/LAS: quadros, curvas, família, unidade, intervalo |
| `fatos` | dados com fonte: topo de formação, intervalo-alvo, revestimento, teste… |
| `pacotes` | contribuições exportadas e importadas, bases aplicadas |

Migrações numeradas (`motor/banco.py:MIGRACOES`) atualizam o banco de quem já usa o
SIAPP sem perder nada. Nunca se edita uma migração publicada: acrescenta-se outra.

## O identificador do poço

O mesmo poço aparece como `7-GMR-13-RN` (REATE, ANP), `7GMR_0013__RN` (arquivos antigos)
e `7GMR13RN` (operador). `motor/pocos.py:canonico()` reduz todas ao nome ANP
(Resolução 699/2017): `<tipo>-<sigla>-<número><sufixo>-<UF>`, inclusive poços no mar
(`-RJS`) e com sufixo (`26D`, `59H`). Nomes fora do padrão usam uma chave só com letras e
números; apelidos conhecidos resolvem para o id certo.

O DLIS grava o **número de cadastro da ANP** do poço (`well_id`): o SIAPP confere com o
cadastro e avisa se o arquivo estiver na pasta de outro poço.

## Decisões

| Decisão | Motivo |
|---|---|
| Janela HTML com motor Python (pywebview), não navegador puro | O REATE não libera acesso cruzado (CORS) e não há leitor maduro de DLIS em JavaScript |
| WebDAV direto, sem automação de navegador | O portal é um Nextcloud público; o protocolo é mais leve e estável |
| Pasta de projeto fixa ao lado do aplicativo | Ao compactar a pasta, os dados vão junto e ficam no mesmo lugar para todos |
| Downloads um por vez, com pausa | O portal pede para não baixar vários grupos simultaneamente |
| Nenhum arquivo pré-selecionado para download | Passada principal, repetida e teste de formação servem a finalidades diferentes |
| OCR local com Tesseract embutido no PyMuPDF | Gratuito, offline, sem instalar programa extra |
| Correções como camada sobre o OCR original | O original nunca se perde; tudo é reversível e auditável |
| Números só por transcrição conferida, nunca por regra global | Num teste real, 6 de 18 profundidades lidas por OCR estavam erradas |
| Mesmo modelo de dados no banco local e na base comunitária | Exportar e importar viram consultas, não conversões |
| Caminhos relativos sempre com "/" | A pasta de projeto funciona igual no Windows, Linux e macOS |
| three.js copiado para `ui/vendor/three/` (módulo ES, carregado por *import map*) | O bloco 3D abre sem internet; a geometria é toda do motor, a janela só desenha |
| Leaflet copiado para `ui/vendor/` | O mapa abre mesmo sem acesso a CDN; só o fundo do mapa precisa de internet |
| Escrita atômica (`.tmp` + troca) em todo JSON | Interrupção nunca deixa arquivo pela metade |

## Pasta de projeto

```
ambiente_teste/
├── siapp.json                         configuração (autor, última bacia) + histórico de cada ação
├── projeto.sqlite                     banco do projeto
├── siapp.log                          registro de erros (o que enviar quando algo falhar)
├── catalogo/<Bacia>/                  o que existe no portal (só listagem)
│   ├── categorias.json, <Categoria>.json
│   └── arvores/<poço>.json
├── bruto/                             arquivos baixados, intocados
│   ├── <Bacia>/<poço>/<pastas do portal>/<arquivo>
│   └── registro_downloads.json        origem de cada arquivo
├── texto/                             texto extraído
│   ├── <mesmo caminho de bruto>.json  texto + posição das palavras, por página
│   ├── resumo.json
│   └── indice.sqlite                  índice de busca (derivado; pode ser apagado)
├── pocos/<poço>/                      cache das curvas (.npz) e inventário de cada perfil
├── cadastro/tabela-pocos.csv          última Tabela de Poços baixada da ANP
├── exportacoes/<poço>/                LAS e CSV exportados
├── fontes/anp/producao/               cópia compactada dos CSVs nacionais de produção da ANP
├── sig/                               camadas geográficas (GeoJSON + shapefile original) e camadas.json
├── contribuicoes/                     pacotes exportados por este computador
└── comunidade/siapp-dados.sqlite      última base comunitária baixada
```

## Armadilhas já encontradas

- O OCR embutido do PyMuPDF devolve **texto vazio, sem erro**, se receber imagem em tons de cinza.
- No Windows, `python` pode apontar para a cópia incompleta do Python do MySQL Shell — o
  `iniciar.bat` nunca usa `python` puro nem `activate.bat`.
- `"CONVENCIONAIS"` não contém `"CONVENCIONAL"`: a busca de pasta usa o radical `CONVENCION`.
- Servidor que ignora `Range` e responde 200 corromperia o arquivo se o download fosse anexado.
- Categorias grandes do REATE vêm divididas em subpastas `…_parteN`.
- DLIS da Schlumberger: índice de profundidade em **décimos de polegada** (`0.1 in`).
- `GREZ` começa com "GR" mas é uma função de custo, não raio gama; `DCAL` é cáliper
  diferencial, não diâmetro do poço. As famílias usam lista de preferência, e padrões
  só onde são seguros.
- A Tabela de Poços da ANP usa `;`, vírgula decimal (às vezes ponto), datas `dd/mm/aaaa hh:mm`
  e espaços sobrando nos campos (`"7 "`).
