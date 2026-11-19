// SIAPP — "Como usar o SIAPP" (1.2): a ajuda do programa, aberta pelo mascote no canto do Início ou por
// Ajuda › Como usar o SIAPP. Um assunto por etapa do trabalho, com o caminho de botões e um atalho para a aba.
//
// Os nomes entre ** ** são os rótulos que aparecem na tela: se um botão mudar de nome, mude aqui também
// (tests/test_interface.py confere que cada um existe em ui/index.html).
"use strict";

const COMO_USAR = [
  {
    id: "inicio", titulo: "Primeiros passos", pose: "acenando",
    fala: "Oi! Eu mostro o caminho. Escolha um assunto ao lado.",
    intro: "O SIAPP busca os dados públicos de poços da ANP (portal REATE) e organiza tudo numa pasta de projeto, no " +
      "seu computador. O caminho mais comum é este:",
    passos: [
      "Em **Início**, abra um projeto ou crie um em **Novo projeto**. Tudo o que você baixar e fizer fica na pasta dele.",
      "Em **1 Acervo** › **Catálogo do REATE**, escolha a bacia, clique em **Conectar** e escolha uma categoria.",
      "Abra um poço para ver as pastas e os arquivos dele, marque só o que quer e clique em **Baixar selecionados**. " +
        "Nada vem marcado.",
      "O que foi baixado abre em **2 Documentos** (PDF e imagens escaneadas) e em **3 Perfis** (DLIS, LIS e LAS).",
      "Em **4 Poços**, veja os poços no mapa e abra a ficha de cada um.",
      "Com os topos de formação, monte a seção em **5 Correlação** e o bloco em **6 Modelo 3D**.",
    ],
    dica: "Os números do topo (1 a 6) seguem a ordem do trabalho, mas você pode ir direto à aba que quiser.",
    ir: ["Ir ao Catálogo do REATE", "catalogo"],
  },
  {
    id: "acervo", titulo: "Achar dados no acervo", pose: "lupa",
    fala: "Dá para saber o que cada poço tem antes de baixar um único arquivo.",
    intro: "A aba **1 Acervo** tem tudo o que se baixa. Para achar os dados certos:",
    passos: [
      "**Catálogo do REATE**: escolha a bacia, clique em **Conectar**, escolha a categoria e abra um poço. Você vê as " +
        "pastas, os arquivos e o tamanho de cada um.",
      "**Levantamento**: para uma bacia inteira, o SIAPP lê só o começo de cada arquivo e diz quais poços têm perfil " +
        "digital, só imagem ou nada. Escolha as categorias e clique em **Levantar**.",
      "**Buscar por tipo**: depois do levantamento, marque os tipos de dado (por exemplo, PVT e perfis digitais), " +
        "escolha **todos os tipos marcados** em **Mostrar poços que têm**, escreva o campo, se quiser, e clique em " +
        "**Procurar**. Nada é baixado para procurar.",
      "**Meus arquivos**: tudo o que já foi baixado para o projeto, de qualquer formato.",
      "Em **Mais**: **Cadastro da ANP**, **Produção da ANP**, **Camadas geográficas** e **Dados consolidados**.",
    ],
    dica: "Os downloads correm em segundo plano e, se a internet cair, continuam de onde pararam.",
    ir: ["Ir a Buscar por tipo", "tipos"],
  },
  {
    id: "documentos", titulo: "Ler documentos", pose: "apontando",
    fala: "O OCR encontra a página. O número, você confere na imagem.",
    intro: "Relatórios, boletins e perfis escaneados abrem em **2 Documentos**.",
    passos: [
      "Os PDFs e as imagens baixados aparecem em **Documentos baixados**. Os escaneados precisam de leitura por OCR: " +
        "clique em **Processar pendentes**.",
      "Escreva na busca (por exemplo, cimentação ou perda de circulação) e clique em **Buscar**. A busca ignora " +
        "acentos e tolera erros do OCR.",
      "Clique num resultado para abrir a página. **Ampliar** mostra a página em tela cheia, com zoom.",
      "Para guardar um número, abra **Transcrever um dado desta página**, desenhe uma caixa em volta do valor, " +
        "confira cada dígito na imagem e clique em **Salvar dado**. O dado fica com a página e a caixa como fonte.",
    ],
    dica: "Viu uma palavra lida errado? Clique nela para corrigir em todos os documentos.",
    ir: ["Ir a Documentos", "docs"],
  },
  {
    id: "perfis", titulo: "Perfis e avaliação", pose: "pensando",
    fala: "Escolha as curvas, marque o intervalo e calcule.",
    intro: "Os perfis digitais (DLIS, LIS e LAS) abrem em **3 Perfis**, já em metros e com as curvas separadas por família.",
    passos: [
      "Em **Arquivos de perfil**, escolha um arquivo baixado.",
      "**Visão padrão** mostra uma curva de cada família. Roda do mouse rola, Ctrl + roda aproxima e arrastar na " +
        "vertical marca um intervalo.",
      "Em **Intervalo-alvo ou topo de formação**, dê um nome, o topo e a base e clique em **Salvar**.",
      "Em **Avaliação de formação no intervalo-alvo**, confira os parâmetros e clique em **Calcular**: argilosidade, " +
        "porosidade, saturação e net pay, com cada parâmetro registrado.",
      "Exporte as curvas marcadas em **LAS** ou **CSV**.",
    ],
    dica: "No gráfico, as linhas verdes tracejadas são os topos de formação do AGP.",
    ir: ["Ir a Perfis", "perfis"],
  },
  {
    id: "pocos", titulo: "Poços no mapa", pose: "apontando",
    fala: "Clique num poço: a ficha junta tudo o que já se sabe dele.",
    intro: "A aba **4 Poços** mostra os poços no mapa, com cores pelo que há no acervo.",
    passos: [
      "O mapa usa o cadastro de poços da ANP. Baixe uma vez em **1 Acervo** › **Mais** › **Cadastro da ANP**, no " +
        "botão **Baixar da ANP**.",
      "Use os **Filtros** para ver só os poços que interessam.",
      "Clique num poço para abrir a ficha: cadastro, pastas no REATE, arquivos baixados, curvas, AGP e esquemas de " +
        "ferramentas.",
      "Em **Destacar poços**, escreva os nomes para deixá-los maiores e com o nome sempre à vista.",
      "**Desenhar a linha da seção** leva os poços perto da linha para a Correlação.",
    ],
    dica: "Ctrl+K busca um poço pelo nome em qualquer aba.",
    ir: ["Ir a Poços", "mapa"],
  },
  {
    id: "correlacao", titulo: "Montar uma seção", pose: "apontando",
    fala: "Os topos de formação ligam um poço ao outro.",
    intro: "A seção estratigráfica de **5 Correlação** usa os topos de formação do AGP de cada poço.",
    passos: [
      "Os topos vêm do AGP: leia os AGPs no **Levantamento** do acervo.",
      "Em **Poços da seção**, escreva o nome do poço e clique em **Adicionar** (até 20 poços). Ou, em " +
        "**Achar poços ao longo de uma linha**, escolha os poços das pontas e clique em **Buscar poços na linha**.",
      "Clique em **Montar a seção**. Ela pode ficar em cota ou nivelada num datum.",
      "Exporte a figura em **SVG**, **PNG** (300 ppp) ou **PDF**, e os topos usados em **CSV**.",
    ],
    dica: "O SIAPP avisa quando um topo salta muito entre poços vizinhos: vale conferir no documento.",
    ir: ["Ir a Correlação", "secao"],
  },
  {
    id: "modelo", titulo: "Modelo 3D", pose: "joinha",
    fala: "Um clique monta o bloco de um campo.",
    intro: "Em **6 Modelo 3D**, os topos de formação viram superfícies e um bloco em três dimensões.",
    passos: [
      "Em **Poços do bloco**, escolha de onde vêm os poços (um campo, em volta de um poço, a bacia toda ou os poços da " +
        "seção) e clique em **Trazer os poços**.",
      "Escolha o método de interpolação. **Qual método usar?** explica cada um, e **Usar o indicado** preenche por você.",
      "Clique em **Montar o bloco**. **Trazer o campo e montar** faz os dois passos de uma vez.",
      "No visor: **Visualizar**, **Validar** (quanto o bloco erra sem cada poço), **Mapa 2D** e **Exportar** " +
        "(mapas para o QGIS, arquivo para simulador, volumetria e modelo 3D).",
    ],
    dica: "O bloco é contexto espacial, não resultado: confira com o que se sabe da geologia da área.",
    ir: ["Ir ao Modelo 3D", "bloco"],
  },
  {
    id: "viabilidade", titulo: "Viabilidade", pose: "pensando",
    fala: "Quão longe o campo está da infraestrutura, e quanto custa o duto?",
    intro: "Em **Mais** › **Viabilidade**, o SIAPP mede o campo contra a infraestrutura. Ele usa as camadas e a " +
      "produção baixadas no Acervo.",
    passos: [
      "Em **Campo e infraestrutura**, escreva o campo e clique em **Medir as distâncias**: gasoduto, UPGN, projeto " +
        "de hidrogênio, fonte de CO₂ e porto mais próximos.",
      "Depois de medir, a **Viabilidade econômica** calcula o custo do duto ÷ capacidade. Clique em " +
        "**Calcular a viabilidade** e veja a conta em **Abrir a memória (HTML)**.",
      "Em **Blocos e campos × infraestrutura**, **Medir todas** mede todas as áreas de uma vez.",
    ],
    dica: "Antes, baixe as camadas em **1 Acervo** › **Mais** › **Camadas geográficas**.",
    ir: ["Ir a Viabilidade", "viab"],
  },
  {
    id: "comunidade", titulo: "Compartilhar", pose: "joinha",
    fala: "Sua correção poupa o trabalho do próximo colega.",
    intro: "Em **Mais** › **Comunidade**, suas correções, transcrições e interpretações viram um pacote para compartilhar.",
    passos: [
      "Em **Contribuir**, **Exportar pacote** junta o que você fez num arquivo.",
      "Envie o arquivo para quem quiser. Quem recebe usa **Escolher pacote…** e vê o que entra antes de confirmar. " +
        "Se uma correção do pacote discordar de uma sua, a sua continua valendo.",
      "**Atualizar pela internet** traz a base comunitária.",
      "**Painel de preenchimento** mostra quanto do acervo já foi preenchido e quem contribuiu. " +
        "**Biblioteca de interpretações** guarda avaliações de perfil para comparar.",
    ],
    dica: "Correções da comunidade nunca apagam o original e podem ser desfeitas.",
    ir: ["Ir a Comunidade", "comunidade"],
  },
  {
    id: "problemas", titulo: "Quando algo dá errado", pose: "ops",
    fala: "Calma, quase sempre tem jeito.",
    intro: "Se algo não saiu como esperado:",
    passos: [
      "As mensagens do programa ficam em **Início** › **Últimas mensagens** (**Ver todas** mostra a sessão inteira).",
      "O portal REATE às vezes fica lento ou fora do ar. Tente de novo mais tarde: os downloads continuam de onde pararam.",
      "**Ajuda** › **Diagnóstico** mostra o estado do programa. **Copiar para enviar** copia tudo para você mandar " +
        "junto com a dúvida.",
      "**Ajuda** › **Limites e confiabilidade** explica o que o OCR consegue e o que não consegue.",
      "**Ajuda** › **Atalhos de teclado** lista e deixa mudar os atalhos.",
    ],
    dica: "Ainda com dúvida? Escreva em github.com/SIAPP-Perfis/SIAPP (Discussions ou Issues).",
    ir: null,
  },
];

// "texto com **rótulo**" → nós de texto e <strong>, sem innerHTML
function comRotulos(texto) {
  const f = document.createDocumentFragment();
  texto.split(/\*\*(.+?)\*\*/).forEach((parte, i) => {
    if (!parte) return;
    f.appendChild(i % 2 ? el("strong", "", parte) : document.createTextNode(parte));
  });
  return f;
}

function paragrafo(classe, texto) {
  const p = el("p", classe);
  p.appendChild(comRotulos(texto));
  return p;
}

function desenharTema(caixa, t) {
  limpar(caixa);
  const cab = el("div", "cu-cab");
  const img = el("img", "cu-masc");
  img.src = `img/mascote/${t.pose}.png`;
  img.alt = "";
  img.dataset.pose = t.pose;
  cab.append(img, el("p", "cu-fala", t.fala));
  caixa.append(cab, el("h3", "cu-titulo", t.titulo), paragrafo("", t.intro));
  const ol = el("ol", "cu-passos");
  for (const passo of t.passos) {
    const li = el("li");
    li.appendChild(comRotulos(passo));
    ol.appendChild(li);
  }
  caixa.appendChild(ol);
  if (t.dica) caixa.appendChild(paragrafo("cu-dica", t.dica));
  if (t.ir) {
    const b = el("button", "btn secundario pequeno cu-ir", t.ir[0]);
    b.type = "button";
    b.onclick = () => { fecharDialogo(); trocarAba(t.ir[1]); };
    caixa.appendChild(b);
  }
  caixa.scrollTop = 0;
}

function abrirComoUsar(qual = "inicio") {
  const c = el("div", "cu");
  const nav = el("nav", "cu-temas");
  nav.setAttribute("aria-label", "Assuntos");
  const tema = el("article", "cu-tema");
  tema.id = "cu-tema";
  const escolher = (t) => {
    for (const b of nav.children) b.setAttribute("aria-current", String(b.dataset.tema === t.id));
    desenharTema(tema, t);
  };
  for (const t of COMO_USAR) {
    const b = el("button", "cu-tema-btn", t.titulo);
    b.type = "button";
    b.dataset.tema = t.id;
    b.onclick = () => escolher(t);
    nav.appendChild(b);
  }
  c.append(nav, tema);
  abrirDialogo("Como usar o SIAPP", c, [], "largo como-usar");
  escolher(COMO_USAR.find((t) => t.id === qual) || COMO_USAR[0]);
}
