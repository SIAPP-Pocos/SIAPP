# Arquitetura

## Visão geral

```
┌──────────────────────── janela (pywebview) ────────────────────────┐
│  ui/  HTML + CSS + JavaScript puros                                  │
│        │  window.pywebview.api.<função>()   ▲ eventoDownload(…)       │
│        ▼                                    │ eventoDocumento(…)      │
│  siapp.py  — camada fina: valida, chama o motor, devolve dicionários  │
└────────────┬───────────────────────────────────────────────────────┘
             ▼
  motor/  (não conhece a interface; pode ser usado por script ou notebook)
    reate.py       portal REATE via WebDAV: listar, mapear poço, baixar com retomada
    downloads.py   fila em segundo plano, um arquivo por vez
    documentos.py  texto (embutido/OCR), índice SQLite FTS5, imagem de página
    vocabulario.py dicionário de domínio e correção de OCR
    projeto.py     pasta de projeto, procedência, escrita atômica
             ▼
  ambiente_teste/  — pasta de projeto (contrato entre as partes)
```

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
| Escrita atômica (`.tmp` + troca) em todo JSON | Interrupção nunca deixa arquivo pela metade |

## Pasta de projeto

```
ambiente_teste/
├── siapp.json                         configuração + histórico de cada ação
├── catalogo/<Bacia>/                  o que existe no portal (só listagem)
│   ├── categorias.json
│   ├── <Categoria>.json
│   └── arvores/<poço>.json
├── bruto/                             arquivos baixados, intocados
│   ├── <Bacia>/<poço>/<pastas do portal>/<arquivo>
│   └── registro_downloads.json        origem de cada arquivo
├── texto/                             texto extraído
│   ├── <mesmo caminho de bruto>.json  texto + posição das palavras, por página
│   ├── resumo.json
│   ├── vocabulario_projeto.json       palavras e correções do usuário
│   └── indice.sqlite                  índice de busca (derivado; pode ser apagado)
├── pocos/                             (próximas versões) curvas padronizadas
└── execucoes/                         (próximas versões) processamentos + parâmetros
```

## Armadilhas já encontradas

- O OCR embutido do PyMuPDF devolve **texto vazio, sem erro**, se receber imagem em tons de cinza.
- No Windows, `python` pode apontar para a cópia incompleta do Python do MySQL Shell — o
  `iniciar.bat` nunca usa `python` puro nem `activate.bat`.
- `"CONVENCIONAIS"` não contém `"CONVENCIONAL"`: a busca de pasta usa o radical `CONVENCION`.
- Servidor que ignora `Range` e responde 200 corromperia o arquivo se o download fosse anexado.
- Categorias grandes do REATE vêm divididas em subpastas `…_parteN`.
