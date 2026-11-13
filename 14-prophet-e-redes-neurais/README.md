# Prophet e redes neurais

O programa da aula e a folha do exercício. O programa lê a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `modelo.py` | O modelo calendário + AR(1) da aula «Modelo contra baseline», com duas opções a mais: a onda do ano com mais pares de seno e cosseno e um histórico mais curto. Não imprime nada. |
| `criterio.py` | Mede o que a decisão precisa saber: quanto histórico a loja tem, quantos números cada tipo de modelo estima, o que sobra no resíduo, quanto vale ganhar e quantos ajustes o teste pede. Refaz as previsões de 31/08 a 24/12/2025, 7 dias antes, cada uma só com a venda até a origem. |
| `meu-criterio.md` | A folha do exercício: o critério da compra do e-commerce. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. O `criterio.py` não usa o Prophet nem uma biblioteca de redes neurais, e o exercício também não.

Se você quiser rodar o Prophet por conta própria, a versão 1.5.0 pede Python 3.10 ou mais novo. Instale com `python3 -m pip install prophet`, num ambiente separado do kit. Para redes, a versão 2.15.0 do PyTorch pede Python 3.11 ou mais novo. As versões são as do PyPI em 12/11/2026.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 criterio.py
```

O `criterio.py` termina em uns três segundos. A última linha mostra quanto tempo os 116 ajustes do modelo levaram na sua máquina, e esse número muda de uma rodada para outra. Todo o resto sai igual. Ele importa o `modelo.py` da mesma pasta: deixe os dois juntos. Se aparecer `No module named 'modelo'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
