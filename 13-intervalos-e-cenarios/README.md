# Intervalos e cenários

Os programas da aula e a folha do exercício. Os programas leem a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `modelo.py` | O modelo calendário + AR(1) da aula «Modelo contra baseline», a régua (mesmo dia da semana, 4 semanas) e as faixas: a da média, a do dia e a dos erros do passado. Não imprime nada. |
| `incerteza.py` | Refaz as previsões de 28/09 a 31/12/2025 com 7, 14, 21 e 28 dias de antecedência, cada uma ajustada só com a venda até a origem, e conta quantas vezes cada faixa pegou a venda. No fim, monta os dois cenários da semana de 12 a 18/01/2026. |
| `meu-plano.md` | A folha do exercício: o plano de avaliação da incerteza do pedido do estoque. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. O statsmodels não é necessário: o `modelo.py` faz as contas com o NumPy, para você ver de onde sai cada faixa.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 incerteza.py
python3 incerteza.py --nivel 90
python3 incerteza.py --salvar faixas.csv
```

O `incerteza.py` termina em uns dois segundos. O `--nivel` aceita 50, 80, 90 e 95. Ele importa o `modelo.py` da mesma pasta: deixe os dois juntos. Se aparecer `No module named 'modelo'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

O `--salvar` grava uma linha por dia previsto e horizonte, com a origem, a venda real, a previsão do modelo, a da régua e o piso e o teto de cada faixa. Abra no pandas ou numa planilha.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
