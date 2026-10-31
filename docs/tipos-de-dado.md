# Procurar por tipo de dado (0.49)

Dados › **Procurar por tipo de dado**. Responde "em quais poços há petrofísica? PVT? sísmica de poço?" sem abrir poço
a poço e **sem baixar nem pedir nada ao portal**. Código: `motor/tipos_dado.py`, `ponte/tipos.py`, `ui/js/tipos_dado.js`.

## De onde vem a resposta

Do **levantamento do acervo** (Dados › Levantamento do acervo): ele lista todos os arquivos de cada poço (tabela
`acervo_arquivos`, com a pasta de cada arquivo). A busca só consulta essa tabela. Por isso:

- só aparecem poços **já levantados**; bacia nova pede levantamento antes;
- se o portal mudar, é preciso levantar de novo para refletir.

## Como o tipo é reconhecido

Pelo **nome da pasta** do arquivo dentro do poço, ignorando maiúsculas, acentos, espaços e pontuação. O REATE escreve
a mesma pasta de vários jeitos; todos contam como um tipo só. Exemplo, petrofísica básica: `PETROFISICABASICA`,
`PETROFISICA_BASICA`, `Petrofisica_basica`, `Petrofisicabasica` e até `Petrofica_basica` (erro de grafia que existe no
portal). Há uma regra por tipo em `TIPOS` (`motor/tipos_dado.py`): "contém" ou "igual a" sobre cada segmento do caminho.
Teste de formação (TFR) e teste de formação **a cabo** são tipos separados.

Um arquivo pode contar em mais de um tipo (o perfil digital processado é também perfil digital).

## Na tela

1. Escolha a bacia (ou todas as levantadas) e marque os tipos (nenhum vem marcado). Cada tipo mostra quantos poços,
   quantos arquivos e quantos bytes o levantamento viu, o que é e com que parte do SIAPP trabalha.
2. **Mostrar poços que têm**: *todos os tipos marcados* (interseção) ou *pelo menos um* (união).
3. **Procurar**: tabela com os poços, a bacia, a categoria e, por tipo, quantos arquivos e que tamanho. Nada vem
   marcado.
4. Com os poços que **você marcar**:
   - **Ver os marcados no mapa** (até 300 por vez), com o destaque que o mapa já tem;
   - **Baixar os arquivos dos marcados**: só os arquivos dos tipos procurados (não o poço inteiro), com o total de
     arquivos e bytes e um botão de confirmar. Entram na fila de downloads de sempre e caem em `ambiente_teste/bruto/`;
   - **Exportar a busca (CSV)**: um arquivo do portal por linha, em `ambiente_teste/exportacoes/tipos_de_dado/`.
5. **Ficha** abre o poço no mapa.

## Restringir a um grupo de poços (0.51)

- **Campo**: digite em "Só os poços do campo" (a lista vem do cadastro da ANP). Sem o cadastro baixado, avisa.
- **Seção**: no painel de poços da Seção, **Dados destes poços** abre esta tela só com eles.
- **Mapa**: no painel de destaques, **Dados destes poços** faz o mesmo com os poços destacados.
- A restrição vale para a contagem dos tipos, a busca, o CSV e o download; a etiqueta "Só …" mostra e tira a restrição.
  Uma lista vazia dá resultado vazio (nunca "tudo").

## Limites

- A pasta diz que **há** arquivos desse tipo, não que estão completos nem que o SIAPP sabe lê-los. Hoje o SIAPP lê
  petrofísica básica, PVT, geoquímica, sísmica de poço, PAG, perfis, direcionais, AGP e esquemas; os demais tipos
  (petrofísica avançada, petrografia, fotos…) só aparecem na busca e no download.
- Pastas fora do padrão (`Dados de Rochas e Fluidos` sem subpasta, 15 poços no levantamento atual) não entram em
  nenhum tipo.
- Baixar muitos poços de um tipo grande (perfis digitais: centenas de GB) pede cuidado; a tela avisa acima de 2 GB.
- Baixar abre a conexão com a bacia do poço (uma bacia por vez).

## Testes

`tests/test_tipos_dado.py` (motor e ponte, com um levantamento sintético) e `test_procurar_por_tipo_de_dado_…` em
`tests/test_interface.py` (nada marcado, busca "todos"/"algum", confirmação do download).
