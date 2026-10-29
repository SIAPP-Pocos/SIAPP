# Geoquímica e outros nomes do poço

*SIAPP 0.43 — bloco 9, item 7.* Código: `motor/geoquimica.py`; apelidos em `motor/dados_poco.py:gravar`.

## Geoquímica

Pasta "Dados De Rochas e Fluidos/GEOQUIMICADEFLUIDO" do REATE: uma planilha (no 1-BRSA-1304-BA, "XML
Spreadsheet 2003" do Excel, `.xml`) e a nota técnica (PDF). O SIAPP lê a planilha — `.xml`, `.xls` ou `.xlsx` —
procurando as tabelas pelo título das colunas:

- **informações da amostra** (Poço ANP, Registro, Poço, Prof., Tipo de Amostra, Bacia): a coluna "Poço" é a sigla da
  operadora e vira apelido;
- **isótopos de carbono** (δ¹³C metano, etano, propano, em ‰): por intervalo ("1680/1684");
- **geoquímica de rocha** (COT, S1, S2, S3, Tmax, IH, IO, Ro): reconhecida pelos títulos; ainda não conferida em um
  arquivo real do acervo.

**Sinal**: δ¹³C de hidrocarboneto é negativo. Na planilha do 1-BRSA-1304-BA, o metano está como `=--47.39` (sinal
duplo, resultado +47,39); a nota técnica dá −47,39 ‰. Com sinal duplo, o SIAPP usa o negativo e avisa; positivo sem
essa evidência fica como está, com aviso para conferir na nota.

**Leitura** (indício, não prova): δ¹³C₁ mais pesado que −50 ‰ → gás termogênico; mais leve que −60 ‰ → biogênico;
entre os dois, misto ou de transição (Schoell, 1983; Whiticar, 1999). δ¹³C₁ < δ¹³C₂ < δ¹³C₃ é a ordem normal; a
inversão (rollover) aponta mistura ou gás muito maturo. No 1-BRSA-1304-BA (1.680–1.684 m): −47,39 / −31,61 / −27,38 ‰,
gás termogênico em ordem normal — coerente com o gás associado ao óleo de 36,6 °API do TFR.

## Outros nomes do poço (apelidos)

O mesmo poço tem nomes diferentes conforme quem escreveu: 1-BRSA-1304-BA (ANP) e 1-FPA-1-BA na base da operadora, às vezes escrito
1-FPA-0001-BA ou 1FPA1BA (para o SIAPP, as três são a mesma grafia). Todo leitor do bloco 9 tira do documento a sigla da operadora e grava como apelido do poço da
pasta — desde que o documento confira com o poço e o nome não seja de outro poço do cadastro:

| De onde | Campo |
|---|---|
| RFCP | "Sigla do Poço na base do E&P" |
| Perfuração | "Nome Poço para o Operador" |
| Relatório do TFR e manômetros (.TPR) | sigla Petrobras / "POÇO" |
| PVT | "Nome do Poço Petrobras" |
| SEG-Y da sísmica de poço | "POCO (SIGLA OPERADORA)" no cabeçalho textual |
| Geoquímica | coluna "Poço" das informações da amostra |

A ficha do poço mostra cada grafia com a origem ("Também escrito como: 1-FPA-1-BA (formulários da ANP)…"), e a busca
por qualquer uma delas cai no poço certo (mapa, destaque, ficha).
