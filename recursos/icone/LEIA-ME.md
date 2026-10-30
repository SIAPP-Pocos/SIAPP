# Ícone do SIAPP

Um "S" formado por duas curvas de perfil — raios gama (verde) e resistividade (vermelho) — com o amarelo do
*crossover* entre elas, sobre papel de perfil com grade logarítmica, cortado por um marcador de topo de formação.

Um ícone pequeno não é o desenho grande reduzido: a 16 px a serrilha e a grade viram borrão. Por isso há um
desenho por faixa de tamanho, e o `siapp.ico` guarda cada um já rasterizado (PNG de 32 bits):

| Arquivo          | Vai para            | O que muda                                                              |
|------------------|---------------------|-------------------------------------------------------------------------|
| `siapp.svg`      | 256, 64 e 48 px     | desenho completo: grade log, curvas serrilhadas, triângulo do topo      |
| `siapp-40.svg`, `siapp-32.svg`, `siapp-24.svg` | 40, 32 e 24 px | só três linhas da grade, cada uma ocupando uma coluna de pixel inteira; borda e topo encaixados em pixels; serrilha menor |
| `siapp-20.svg`, `siapp-16.svg` | 20 e 16 px | sem grade; borda de 1 px exato; topo numa linha de pixel; S maior, liso e com cores mais fortes |

`siapp-256.png` é a versão grande em PNG (para README, site, etc.). A interface usa `ui/img/siapp.svg`
(o desenho de 24 px).

Para refazer o `.ico` depois de mexer num SVG: rasterize cada tamanho a partir do SVG da sua faixa (um
navegador sem tela, como o Playwright, dá o resultado mais fiel) e junte os PNG num ICO com entradas PNG
(formato aceito desde o Windows Vista). `tests/test_icone.py` confere tamanhos e cabeçalhos.
