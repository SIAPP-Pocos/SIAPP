# Sísmica de poço — checkshot (tempo × profundidade)

*SIAPP 0.42 — bloco 9, item 6.* Código: `motor/checkshot.py`.

Na pasta "Sismica de Poco" do REATE vêm o SEG-Y empilhado (`<poço>_asr-3_stack.sgy`, um traço por componente
em cada nível), o registro de campo tiro a tiro (`_raw.sgy`) e o relatório da empresa (PDF). O SIAPP lê **só o
cabeçalho de cada traço** — não o sinal: profundidade do receptor, posição e profundidade da fonte, tempo de chegada.

## Onde estão os campos

A sísmica de poço usa posições fora do padrão SEG-Y, e o próprio cabeçalho textual as declara (Halliburton):

```
C35 SeismicDatumElev@57,Microseconds@205
C36 Receiver:MD@173,TVD@181,RefElev@185,RCX@81,RCY@85
C37 Source:SCX@73,SCY@77,SD@193,RefElev@189,S2Monitor@197
C38 Times(us):pick@209,ref@213,DatumCorr@225,ExtDelay@221,1stSamp@217
```

O SIAPP lê esse mapa (ASCII ou EBCDIC) e cada campo como inteiro de 4 bytes; elevações e profundidades com o
escalar de elevação, coordenadas com o de coordenadas, tempos em microssegundos. Um SEG-Y sem o mapa é recusado com
o motivo. Só entram os SEG-Y da pasta "Sismica de Poco" ou com checkshot/VSP no nome (um cubo sísmico 3D, com
milhões de traços, não é varrido).

## O cálculo

Por nível (o mesmo do "FULL PROFILE DATA" do relatório):

| Grandeza | Como |
|---|---|
| distância vertical fonte → receptor (dz) | TVD − (elevação da mesa − elevação da fonte); elevação da fonte = referência − profundidade da fonte |
| afastamento (SGO) | distância horizontal entre fonte e receptor |
| tempo vertical Tv | Tt × dz / √(dz² + SGO²), com Tt = pick + atraso externo (raio reto) |
| Tcorr | Tv + Ts (correção da fonte ao datum sísmico, campo DatumCorr) |
| TWT | 2 × Tcorr |
| TVDSD | TVD abaixo do datum sísmico |
| Vméd, Vint | TVDSD / Tcorr; diferença de TVDSD / diferença de Tcorr entre níveis vizinhos |

No 1-BRSA-1304-BA (23 níveis de 90,6 a 1.944 m), a tabela confere com a do relatório da Halliburton: a 1.944 m,
Tcorr 0,6385 s, TWT 1.277 ms, Vméd 3.032 m/s, Vint 4.263 m/s (relatório: 4.264). O registro tiro a tiro aparece na
lista de documentos, mas a tabela vem do empilhado: os tempos do bruto não têm as mesmas correções.

## Onde é usado

- **Ficha do poço**: tabela, gráficos TWT × profundidade e velocidade intervalar × profundidade, e "Exportar a
  tabela (CSV)" (`exportacoes/<poço>/checkshot_tempo_profundidade.csv`, com MD, TVD, TVDSD, Tcorr, TWT, Vméd e
  Vint — para levar à sísmica de superfície);
- **Perfis**: a leitura do mouse mostra o TWT de cada profundidade (interpolado entre os níveis);
- a sigla do poço na operadora, do cabeçalho textual, vira apelido.
