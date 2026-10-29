# Dados consolidados: de onde vem, onde fica, onde é usado

*SIAPP 0.44.* Código: `motor/consolidado.py` (o catálogo `TEMAS` abaixo sai dele); tela em **Dados › Dados
consolidados** e no botão "Dados consolidados" da ficha do poço.

Depois do bloco 9, o mesmo tipo de dado chega por vários caminhos. A tela junta, por tema, cada fonte, a tabela do
banco do projeto onde ela fica e os módulos que a usam — no projeto (quantos poços e registros de cada fonte) e num
poço (os valores de cada fonte lado a lado, pelo nome do poço em qualquer grafia). É só leitura: nada ali decide
qual fonte vale; a regra de cada módulo está na coluna "Onde é usado".

| Tema | Fonte | Onde fica | Onde é usado |
|---|---|---|---|
| Topos de formação | AGP da ANP | `agp_unidades` | Seção estratigráfica e bloco 3D: só os topos do AGP<br>Perfis: AGP (verde tracejado), RFP (marrom pontilhado), transcritos (roxo)<br>Ficha do poço: todos; os topos sem nome do RFP ganham o nome da calha a até 10 m<br>Avaliação: as unidades do AGP como intervalos candidatos |
|  | RFP (topos constatados) | `dados_poco · topo` |  |
|  | Descrição de calha (PAG) | `dados_poco · topo_calha` |  |
|  | Transcritos (você e a comunidade) | `fatos · topo_formacao` |  |
| Intervalos de interesse | Intervalos-alvo marcados | `fatos · intervalo_alvo` | Avaliação de formação: candidatos (marcados, AGP, formulários, TFR, gás na lama)<br>Perfis: canhoneados na borda direita; intervalos-alvo em amarelo<br>Ficha do poço: todos, com os indícios |
|  | Zonas-reservatório do AGP | `agp · dados.zonas` |  |
|  | Análise de perfis (RFP) | `dados_poco · analise_perfil` |  |
|  | Canhoneados (RFCP) | `dados_poco · canhoneado` |  |
|  | Teste de formação (TFR) | `dados_poco · teste_tfr` |  |
|  | Gás na lama (PAG) | `dados_poco · gas_lama` |  |
|  | Indícios (RFP) | `dados_poco · indicio` |  |
| Temperatura | AGP — corridas de perfilagem (BHT) | `agp · dados.corridas` | Avaliação: nota de referência para o Rw (o SIAPP não converte sozinho)<br>Ficha do poço |
|  | AGP — temperatura extrapolada e gradiente | `agp · dados.temperaturas` |  |
|  | RFP, teste a cabo e TFR | `dados_poco · temperatura` |  |
| Pressão | Teste a cabo (estações do DLIS) | `dados_poco · pressao_formacao` | Ficha › Pressões × profundidade: gradiente por grupo, fluido compatível e contato<br>Ficha › relatório do TFR (k, skin, IP, estática) |
|  | Testes do RFP | `dados_poco · teste_formacao` |  |
|  | Relatório do TFR | `dados_poco · teste_tfr` |  |
|  | Manômetros do TFR | `dados_poco · manometro` |  |
| Fluidos (PVT, °API, gás) | Análise PVT (liberação diferencial) | `dados_poco · pvt` | Viabilidade: °API, densidade do gás, Bo, Rs e Bg do PVT antes das correlações; depois o transcrito e a leitura automática dos documentos<br>Ficha do poço: PVT, composição, geoquímica |
|  | Composição (liberação flash) | `dados_poco · composicao` |  |
|  | Transcritos | `fatos · propriedade_fluido` |  |
|  | Isótopos do gás | `dados_poco · isotopo_gas` |  |
| Lama e filtrado | AGP — Rm, Rmf, Rmc por corrida | `agp · dados.corridas` | Avaliação: nota de referência para o Rw e o Rmf<br>Ficha do poço |
|  | Perfuração — fluido e peso por fase | `dados_poco · fase` |  |
|  | PAG — salinidade | `dados_poco · salinidade_lama` |  |
| Litologia | AGP — litologia das amostras | `agp · dados.litologia` | Perfis: trilha de litologia (a do AGP; sem ela, a da calha)<br>Ficha do poço |
|  | Descrição de calha (PAG) | `dados_poco · litologia_calha` |  |
|  | Fluorescência e corte (PAG) | `dados_poco · indicio_calha` |  |
| Curvas de perfil | Perfis abertos (DLIS, LIS, LAS) | `perfis, curvas` | Perfis e avaliação de formação<br>Avaliação × operadora (com o perfil processado aberto)<br>Levantamento e mapa: quais poços têm cada curva no portal, sem baixar |
|  | Interpretação da operadora (Vsh, φ, Sw, k) | `curvas · família VSH/PHIE/PHIT/SW/PERM` |  |
| Interpretações de perfil | Biblioteca de interpretações | `interpretacoes` | Comunidade › Biblioteca: comparar e refazer; pacotes de contribuição |
| Tempo × profundidade | Checkshot (SEG-Y da sísmica de poço) | `dados_poco · checkshot` | Ficha: tabela, gráficos e CSV para a sísmica<br>Perfis: TWT na leitura do mouse |
| Trajetória do poço | Dados direcionais | `direcionais` | Bloco 3D: poços desviados na posição real |
| Produção | Produção da ANP por poço | `producao_poco` | Ficha do poço<br>Viabilidade: depleção do campo |
| Outros nomes do poço | Apelidos (cadastro, formulários, PVT, TFR, SEG-Y, geoquímica) | `apelidos` | Busca do poço por qualquer grafia (mapa, destaque, ficha, pastas do portal) |

## Lacunas que a tabela deixa à vista

- **Seção estratigráfica e bloco 3D usam só os topos do AGP.** Num poço sem AGP (caso do 1-BRSA-1304-BA), os topos
  do RFP, nomeados pela calha do PAG, e os transcritos aparecem na ficha e nos perfis, mas não entram na seção nem no
  bloco. Levá-los para lá pede uma regra de precedência (AGP > transcrito > RFP > calha?) — para decidir.
- **Temperatura e lama não viram Rw sozinhas**: a avaliação mostra as referências (AGP, RFP, teste a cabo, TFR,
  fluido por fase, salinidade do PAG) e o Rw continua sendo escolha do usuário.
- **Pressões** ficam na ficha (gradiente, fluido compatível, contato); a viabilidade usa a pressão do reservatório
  que o usuário informa ou a hidrostática pela profundidade.
- Dados de documentos lidos (`leituras`, `dados_poco`) **não entram nos pacotes de contribuição**: quem baixa o
  mesmo arquivo obtém a mesma leitura.
