# Base comunitária

O SIAPP é a ferramenta; o repositório [Comunidade](https://github.com/SIAPP-Pocos/Comunidade)
é a base. O que uma pessoa corrige ou transcreve vira um **pacote de contribuição**; os
pacotes aceitos são compilados numa **base** que todo mundo baixa.

```
  SIAPP (você)                    Comunidade (GitHub)                 SIAPP (outra pessoa)
  ─────────────                   ────────────────────                 ────────────────────
  corrige o OCR,                  pull request com o pacote            aviso de base nova →
  transcreve dados   ──exporta──▶ validação automática  ──aceite───▶  Atualizar pela internet
  (origem local)                  revisão humana          vAAAA.MM.N    (origem base)
                                  compilação → Release (sozinha, logo depois do aceite)
```

A aba Comunidade tem três partes: **Contribuir** (autoria, exportar, importar, base),
**Painel de preenchimento** e **Biblioteca de interpretações** (as duas desde a 0.35).

## O pacote (formato v3)

Arquivo JSON em `ambiente_teste/contribuicoes/AAAA-MM-DD_sobrenome_siapp.json`:

| Campo | Conteúdo |
|---|---|
| `id`, `criado_em`, `siapp_versao`, `licenca` | identificação; licença sempre CC-BY-4.0 |
| `autor` | nome (obrigatório), instituição, ORCID |
| `vocabulario.correcoes` | `{de, para}`: forma lida pelo OCR → forma escrita no papel |
| `vocabulario.palavras` | termos técnicos (atalhos de busca e referência para a correção) |
| `vocabulario.manter_original` | palavras que a correção automática não deve mexer |
| `fatos` | dado transcrito: poço, tipo, nome, profundidades, valor e **fonte** (desde a 0.29, também o tipo `propriedade_fluido`: grau API, densidade do gás…) |
| `apelidos` | outras grafias do nome de um poço |
| `interpretacoes` | interpretações de perfil da biblioteca (desde a 0.35, formato v3): ver abaixo |

A fonte de um fato tem tudo o que um revisor precisa para conferir sem o pacote trazer
o documento: `sha256` e `caminho_remoto` do arquivo no REATE, `pagina` e `caixa`
(`[x0, y0, x1, y1]`, frações da largura e da altura da imagem da página).

**Nada do REATE vai no pacote.** O acervo continua sendo baixado do portal público.

O SIAPP 0.35 exporta o formato **3** e importa o 1, o 2 e o 3. Pacote de formato 1 ou 2 com
interpretações é recusado. O esquema está em `esquema/contribuicao-v3.schema.json` no repositório Comunidade.

## Regras que o SIAPP e o validador do repositório Comunidade aplicam

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

No repositório Comunidade, cada pacote aceito (pull request juntado à `main`) dispara o workflow `publicar base`: ele
valida, compila e publica uma Release nova, `vAAAA.MM.N` (N começa em 0 a cada mês), com três arquivos:
`siapp-dados.sqlite` (a base), `vocabulario.json` e `resumo.json` (contagens e a lista de pacotes, com autor e poços de
cada um). Enquanto nenhum pacote foi aceito, nada é publicado (`contribuicoes/exemplo.json` só mostra o formato).

**Atualizar pela internet** baixa a Release mais recente (`siapp-dados.sqlite`) e substitui tudo o que tinha origem
`base`. **Importar de arquivo…** aplica um `.sqlite` gerado por `python ferramentas/compilar.py`.

### Enviar pelo SIAPP (1.4)

**Comunidade › Contribuir › Enviar para a comunidade** manda o pacote sem sair do SIAPP (`motor/envio.py`,
`ponte/envio.py`, `ui/js/envio.js`):

1. **Conta do GitHub, uma vez.** O aplicativo do GitHub "SIAPP Comunidade" (Client ID `Iv23li7rXpFQ6QDmTudr`, da
   organização SIAPP-Pocos, instalado só no repositório Comunidade, com permissão de abrir issues e ler pull requests)
   entra pelo "device flow": o SIAPP mostra um código, a pessoa abre `github.com/login/device`, cola e autoriza. O
   acesso vale 8 horas e se renova sozinho por 6 meses; fica cifrado com a proteção de dados do Windows (DPAPI) em
   `%LOCALAPPDATA%\SIAPP\github.dat` (`motor/cofre.py`) e sai com "Sair". Não há segredo do aplicativo no código.
2. **Confirmação.** A janela mostra o autor, o que vai (correções, dados, interpretações) e os poços, e avisa que fica
   público (CC-BY 4.0) com a conta da pessoa.
3. **Envio.** O SIAPP abre uma issue no repositório Comunidade com um resumo legível e a marca
   `<!-- siapp-pacote id=… partes=n sha256=… -->`, e põe o pacote (JSON → gzip → base64, em partes de até 60 mil
   caracteres) em comentários `<!-- siapp-parte i/n -->`. Se o envio para no meio, a issue é fechada e nada vai para a
   base. Uma cópia fica em `contribuicoes/` do projeto e o que foi enviado não vai de novo no próximo pacote.
4. **Robô do repositório.** O workflow `receber pacote` (`ferramentas/receber_pacote.py`) junta as partes (só as do
   autor da issue), confere o SHA-256, valida e abre o pull request no nome de quem enviou, que o mantenedor revisa.
   Se não serve, comenta o motivo e fecha a issue. Aceito o pull request, a base nova sai sozinha.
5. **Seus envios.** O cartão mostra cada envio e onde ele está: "Recebido, sendo conferido", "Em revisão", "O revisor
   pediu uma mudança", "Aceito" ou "Não passou na conferência" (com o motivo). O SIAPP pergunta ao GitHub ao abrir a
   aba e ao abrir o projeto (no máximo a cada 2 minutos por envio) e avisa quando muda.

Sem conta no GitHub, **Exportar pacote** continua gravando o arquivo para mandar a um mantenedor.

### Aviso de base nova (1.3)

Ao abrir o projeto, o SIAPP pergunta ao GitHub qual é a última Release (`motor.comunidade.consultar_base`): no máximo
uma vez por dia (a resposta fica no banco do projeto, `meta.comunidade_consulta`) e sem baixar a base, só o
`resumo.json`. Sem internet, nada aparece. Se a versão publicada é outra que a aplicada, a aba **Comunidade** ganha um
ponto azul e o cartão "Base comunitária" mostra quem mandou o quê desde a sua (`novidades`: os pacotes do `resumo.json`
que não estavam na base aplicada, guardados em `meta.base_contribuicoes`). **Procurar base nova** consulta na hora; a
caixa "Procurar sozinho ao abrir o projeto" desliga a consulta automática (`config.comunidade_auto`).

### O dado da comunidade na página do documento (1.3)

Quem recebe um fato pela base ou por pacote não tem o caminho local de quem transcreveu: o fato traz o SHA-256 e o
caminho do documento no REATE. `Banco.fatos(documento=rel)` casa por qualquer um dos três (caminho local, SHA-256,
caminho no REATE), então a página aberta em Documentos mostra também o que a comunidade transcreveu nela, assim que o
mesmo documento for baixado. Na ficha do poço, a fonte ("pág. 3") vira link para a página quando o documento está no
projeto (`Banco.anotar_documentos`); sem ele, a dica diz o caminho no REATE.

O mapa (anel azul e o filtro "da comunidade" na legenda), a lista ao lado do mapa e a lista de poços do catálogo
(selo "C") marcam os poços com dados da comunidade (`Banco.comunidade_por_poco`). A prévia da importação de um pacote
lista os poços e os documentos citados que o projeto ainda não tem, sem marcar nada para baixar.

O formato da base (`versao_formato_base` 1) está descrito em `ferramentas/compilar.py`
do repositório Comunidade; o SIAPP recusa base de versão mais nova que a que conhece. A tabela
`interpretacoes` é opcional: base compilada antes dela continua sendo aplicada (sem interpretações),
e o SIAPP anterior à 0.35 a ignora.

## Painel de preenchimento (0.35)

Comunidade › **Painel de preenchimento** responde, sobre o banco do projeto (o que você fez
mais o que veio de pacotes e da base comunitária):

- **Quanto está preenchido.** A base são os poços com pasta no REATE (levantamento do acervo
  ou catálogo); sem levantamento, os poços que aparecem em algum dado do projeto. Para cada
  indicador, quantos poços e a porcentagem: documentos baixados, perfil digital (baixado ou
  visto no portal pelo levantamento), topos de formação (AGP ou transcritos), topos
  transcritos, dados transcritos, páginas revisadas, interpretações de perfil e produção.
  Também por bacia (clique na bacia para filtrar).
- **Quem contribuiu.** Cada autor com dados transcritos, topos, correções do OCR, palavras,
  páginas revisadas e interpretações; em quantos poços; de onde veio (sua, pacote, base) e
  quando. O autor é o nome gravado em cada item (o seu, da aba Contribuir, para o que é local).
- **Atividade por mês**, pela data de criação de cada item.
- **Onde ajudar**: poços com perfil e nenhum topo; poços com documentos baixados e nenhum dado
  transcrito. Clicar no poço abre a ficha no mapa.

As correções do OCR valem para todos os documentos (não têm poço): entram no total do autor,
mas não no filtro por bacia.

## Biblioteca de interpretações de perfil (0.35)

Uma **interpretação** é uma avaliação de formação (aba Perfis) que alguém compartilhou. Vão:

| Campo | Conteúdo |
|---|---|
| `poco`, `titulo`, `comentario` | o poço; um título curto (até 120 caracteres) e o comentário (até 2000) |
| `arquivo` | `sha256`, `caminho_remoto`, `bacia` e `nome` do arquivo de perfil |
| `curvas_usadas` | a curva de cada papel (GR, RHOB, NPHI, DT, RT, CALI, BS, DRHO): quadro, mnemônico e unidade |
| `metodos`, `parametros`, `parametros_automaticos` | Vsh, φ e Sw; todos os parâmetros, e quais foram estimados pelo SIAPP e como |
| `intervalos` | nome, topo, base e o resumo: bruto, reservatório, net pay, N/G, φ e Sw no pay, Vsh, HPV, QC |

**As curvas calculadas não vão**: quem tem o mesmo arquivo (o hash confere) refaz o cálculo com os
mesmos parâmetros e chega no mesmo número. É isso que torna a interpretação conferível.

Na tela:

- **Compartilhar**: aba Perfis, depois de **Calcular**, "Compartilhar na biblioteca…" (título e
  comentário). Precisa do seu nome (Contribuir). Compartilhar de novo a mesma avaliação só muda o
  título e o comentário. Ela vai no próximo pacote exportado. As avaliações ainda não
  compartilhadas também aparecem na biblioteca, para compartilhar ou comparar.
- **Buscar**: por poço, título, autor, comentário ou campo; por bacia e por origem (suas, de
  pacotes, da base). A lista agrupa por poço; "sem o arquivo" avisa quando você não tem o perfil.
- **Ver**: parâmetros (os automáticos marcados "auto"), curvas, intervalos e comentário.
- **Comparar** (2 a 6 marcadas, de preferência do mesmo poço): os intervalos de autores diferentes
  são casados pela profundidade (metade ou mais em comum) e cada linha mostra net pay, φ e Sw de
  cada um, com a diferença no net pay; depois os totais, os métodos, as curvas e os parâmetros —
  o que difere fica destacado e é listado no alto ("Diferem em: Rw, Vsh…"). Avisa se os poços ou
  os arquivos não são os mesmos.
- **Refazer nos Perfis**: abre o arquivo (achado pelo hash, pelo caminho no REATE ou pelo nome)
  com os intervalos da interpretação já marcados, as mesmas curvas e os mesmos parâmetros. Depois
  de **Calcular**, "Comparar com a da biblioteca" põe as duas lado a lado. Sem o arquivo, o SIAPP
  diz qual baixar e leva ao Catálogo.
- **Tirar da biblioteca**: só as suas. Se ela já foi num pacote, o SIAPP avisa (a remoção no
  Comunidade é pedida lá). As da comunidade saem desfazendo o pacote.

Na aba Perfis, uma nota avisa quando a biblioteca tem interpretações do poço aberto.
