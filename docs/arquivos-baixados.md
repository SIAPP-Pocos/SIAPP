# Arquivos baixados (0.54)

Dados › **Arquivos baixados**. Para achar e abrir o que já foi baixado sem fuçar as pastas do projeto. Código:
`motor/arquivos_baixados.py`, `ponte/arquivos.py`, `ui/js/arquivos_baixados.js`.

## O que lista

Tudo o que está em `ambiente_teste\bruto\<bacia>\<poço>\<pastas do portal>\<arquivo>`, de **qualquer formato**. Vem do **disco**
(o que de fato está lá), cruzado com o banco do projeto. Só o `registro_downloads.json` (procedência dos downloads) fica de fora.

Por arquivo:

| Coluna | De onde vem |
|---|---|
| Formato | extensão; para perfis, o formato real inventariado (ex.: "LIS (em .tif)"); `.tif` que o banco não conhece é olhado em 1 KB |
| Tamanho, data | disco e data do download (banco); sem registro, a data do arquivo |
| O que o SIAPP fez | `leituras` (leitor e quantos dados), `perfis` (inventário), texto extraído (Documentos), e as leituras do levantamento (AGP, direcionais, esquemas) |
| Onde aparece | o destino de cada leitor: ficha do poço (Petrofísica, PVT, PAG, Pressões, Geoquímica, Sísmica de poço), Perfis, Avaliação, Seção, Bloco 3D, Documentos |

Situações: **lido**, **texto extraído**, **perfil**, **não lido** (o SIAPP sabe ler, falta abrir o projeto/processar), **sem leitor** (o
SIAPP ainda não lê; dá para abrir e usar fora), **erro** (com a mensagem) e **incompleto** (`.part`, download interrompido).

## Botões

- **Abrir**: programa padrão do Windows. **Nunca** abre programas e scripts (`.exe`, `.bat`, `.cmd`, `.msi`, `.vbs`, `.js`, `.ps1`,
  `.lnk`, `.dll`, `.iso`…): para esses, só "Mostrar na pasta". Só abre arquivos dentro de `bruto/`.
- **Mostrar na pasta**: Explorer com o arquivo selecionado.
- **Ver na ficha**: abre a ficha do poço no Mapa.
- **Apagar**: ver abaixo.

## Apagar

1. Confirmação mostra o nome, o tamanho, **o que sai do SIAPP** e **o que fica**.
2. O arquivo vai para a **Lixeira do Windows** (restaurável). Se a Lixeira falhar, o SIAPP **não** apaga de vez.
3. Sai do banco o que foi *derivado* do arquivo: dados do poço lidos dele, a leitura, o perfil inventariado e suas curvas, o texto
   extraído, o índice de busca, o registro em `arquivos` e a linha de procedência. Assim o arquivo pode ser baixado de novo.
4. **Fica** o trabalho do usuário: transcrições (`fatos`) e páginas corrigidas (`paginas_revisadas`) continuam no banco, citando o
   arquivo de origem. O cache de curvas em `pocos/` não é limpo.
5. Se restaurar da Lixeira, reabra o projeto para o SIAPP ler de novo.

## Limites

- Apagar é arquivo a arquivo (não há "apagar pasta" nem "apagar o poço").
- A lista lê a pasta toda a cada abertura da aba (milhares de arquivos continuam rápidos; a lista mostra 200 por vez).
- "Onde aparece" diz *onde o SIAPP usa* o dado, não que o dado está completo ou correto.
