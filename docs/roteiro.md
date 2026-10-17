# Roteiro

Decidido em 16/10/2026: primeiro as **funcionalidades novas**; as melhorias do que já
existe e a validação científica ficam **para o final**, antes do lançamento (1.0).

## Agora — funcionalidades novas

- [x] **Esquema de ferramentas** (0.17): ler os PDFs da pasta "Esquema de Ferramentas",
      reconhecer as ferramentas da coluna e rotular os perfis do poço (passada principal,
      repetida, testador de formação, imagem, RMN…). Ver `docs/ferramentas.md`.
- [ ] **Bloco 3D** (próximo): contexto espacial dos poços e topos (não é resultado
      quantitativo; ver a Especificação Funcional).

## No final — melhorias do que já existe

- [ ] **Download em lote**: baixar os perfis dos poços de uma seção, de um campo ou do filtro
      do mapa, com uma tabela por poço (nada pré-marcado; atalhos só para marcar) e leitura
      automática ao terminar. Os rótulos de corrida da 0.17 ajudam a escolher (ex.: só a
      perfilagem convencional, passada principal).
- [ ] **Seção pelo mapa**: clicar nos poços A e B no mapa, ver a linha da seção desenhada no
      mapa, abrir a seção pela ficha de um campo.
- [ ] **Instalador para Windows** (.exe que roda sem instalar Python).
- [ ] Ajustes finos do estilo clássico da seção a partir de uma figura de referência
      (ex.: Boletim de Geociências da Petrobras).
- [ ] Esquemas: ampliar o dicionário de ferramentas (Halliburton, Baker, Weatherford) com
      esquemas reais desses fabricantes.

## No final — validação científica

- [ ] Avaliação de formação contra valores publicados (poço com Rw conhecido).
- [ ] Seções estratigráficas conferidas com a carta estratigráfica e a geologia do campo.
- [ ] Avaliação em lote por formação (tabela poço × formação) — depende do download em lote.
- [ ] Esquemas: conferir uma amostra maior (ex.: 100 esquemas sorteados) contra o PDF.

## Antes do lançamento

- [ ] Termos de uso dos dados da ANP; DOI (Zenodo); publicar no GitHub (SIAPP-Pocos).
