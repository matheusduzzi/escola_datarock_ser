# 08. MAE, RMSE, MAPE e WMAPE

Os arquivos da aula «MAE, RMSE, MAPE e WMAPE» do curso Séries temporais. Rode os comandos de dentro dessa pasta.

| Arquivo | Para que serve |
|---|---|
| `metricas.py` | As contas da aula: as três previsões de 2025 feitas 7 dias antes, as quatro métricas com e sem os dias de loja fechada, os maiores erros, o número fixo que cada métrica prefere e o custo do erro. |
| `dados/guarda_chuva.csv` | 56 dias de venda de guarda-chuva do exercício: `data`, `vendidos`, `prev_media` e `prev_mediana`. O exercício explica cada coluna. |
| `minha_analise.py` | Onde você escreve o código do exercício. |
| `minhas-respostas.md` | Onde você escreve as respostas do exercício. |

O `metricas.py` usa a venda da loja física que vem com o kit, em `dados/loja` na raiz do kit. Ele acha essa pasta sozinho; não precisa copiar nada.

## Como rodar

Você precisa do Python com o pandas, como no README do kit do curso. O NumPy vem junto com o pandas.

```bash
python3 metricas.py
```

A saída é a mesma da seção 4 da aula e sai igual toda vez.

```bash
python3 minha_analise.py
```

Antes de você escrever qualquer coisa, ele só mostra `56 dias, de 06/10/2025 a 30/11/2025; colunas: data, vendidos, prev_media, prev_mediana`. As tarefas ficam embaixo, nos comentários.

Se o `minha_analise.py` mostrar `FileNotFoundError`, você está rodando de outra pasta. Entre na pasta dessa aula e rode de novo.

O CSV vem pronto e não muda. Não edite à mão: as respostas do exercício dependem desses números.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
