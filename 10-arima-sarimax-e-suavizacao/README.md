# ARIMA, SARIMAX e suavização

Os programas e o quadro da aula, e a folha do exercício. Os programas leem a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `hipoteses.py` | Mede os componentes da venda até 31/08/2025: memória, semana, tendência, onda do ano, eventos do calendário e o que sobra. Com `--semanal`, faz o mesmo com a venda somada por semana, até 28/12/2025. |
| `a_mao.py` | Faz à mão as contas da suavização simples, do Holt-Winters e de um ARIMA(1,1,1), com parâmetros fixos, e mostra a previsão de cada um para a semana de 01/09/2025, ao lado da regressão do calendário. |
| `quadro-familias.md` | O quadro da aula: o que cada família supõe e como cobre cada componente da venda. |
| `minha-escolha.md` | A folha de respostas do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. Não precisa do statsmodels nessa aula: ele entra na aula 11, para ajustar os modelos.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 hipoteses.py
python3 a_mao.py
python3 hipoteses.py --semanal
```

Os três terminam em menos de dois segundos. O `a_mao.py` importa o `hipoteses.py` da mesma pasta: deixe os dois juntos. Se aparecer `No module named 'hipoteses'`, você está rodando uma cópia do `a_mao.py` fora da pasta da aula. No Windows, troque `python3` por `py`.

A opção `--ate` muda o último dia do histórico, por exemplo `python3 hipoteses.py --ate 2025-06-30`. A aula e o exercício usam o padrão.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
