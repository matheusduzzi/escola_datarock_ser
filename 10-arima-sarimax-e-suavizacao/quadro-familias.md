# O quadro das famílias

Da aula «ARIMA, SARIMAX e suavização». Cada linha é um componente que a venda diária da loja física tem, com o número que o `python3 hipoteses.py` mostrou no histórico até 31/08/2025. Cada coluna é uma família e o jeito dela de cobrir o componente.

| O que a venda tem | Número que mostra | Suavização (Holt-Winters, ETS) | ARIMA sem sazonalidade | SARIMA | SARIMAX |
|---|---|---|---|---|---|
| semana | 0,741 com 7 dias antes; sábado 1,44 vez a média | ajuste por dia da semana, período 7 | só com 7 termos AR ou mais | parte sazonal de período 7 | parte sazonal de 7 ou colunas do dia da semana |
| tendência | +14,2% por ano | inclinação, de preferência amortecida | diferença | diferença | coluna de tendência ou diferença |
| vaivém proporcional | sábado − domingo cresceu 14%, como a média | sazonalidade multiplicativa | log da venda | log da venda | log da venda |
| onda do ano | de 0,88 em junho a 1,12 em dezembro | não cabe: seria um período de 365 com 1,7 ciclo | não tem | não cabe, pelo mesmo motivo | seno e cosseno do ano como colunas |
| eventos | Black Friday +161%, Natal +41%, feriado −23% | não recebe calendário | não recebe | não recebe | colunas do calendário |
| memória que sobra | resíduo entre −0,08 e +0,08 | não precisa | termos AR e MA | termos AR e MA | termos AR e MA de ordem baixa, se precisar |
| o que precisa saber dos dias previstos | | nada | nada | nada | o calendário desses dias |

## O que cada família supõe, em uma frase

- **Suavização exponencial (simples, Holt, Holt-Winters; ETS):** a venda é um nível, uma inclinação e um ajuste por posição da estação, que mudam devagar. Um período de estação só. Não recebe colunas de fora.
- **ARIMA:** depois das diferenças, a mudança de hoje depende de um jeito linear das mudanças e dos erros anteriores.
- **SARIMA:** o mesmo, com diferença e termos que olham um período atrás, como 7 dias.
- **SARIMAX:** uma regressão com as colunas que você escolhe e um SARIMA sobre o que a regressão não explicou. Para prever, precisa das colunas dos dias previstos.

## Como usar o quadro

Para outra série, ou para a mesma série em outra frequência, rode o diagnóstico e troque a coluna "Número que mostra". Uma linha que some (como a semana, numa soma semanal) tira um motivo de escolha. Uma linha que cresce muda a família que cobre melhor. Cada família que entra na comparação leva o motivo e o resultado que a tira da disputa.
