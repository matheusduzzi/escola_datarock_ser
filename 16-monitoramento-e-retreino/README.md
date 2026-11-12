# Monitoramento e retreino

O painel de monitoramento da aula, a venda de 2026 e a folha do exercício. Os programas leem a venda de 2024 e 2025 e o calendário em `dados/loja`, na raiz do kit do curso, e a venda de 2026 na pasta `dados/` dessa aula.

| Arquivo | O que faz |
|---|---|
| `monitor.py` | Refaz as revisões de segunda-feira de 09/02 a 27/04/2026. Cada previsão usa só a venda que tinha fechado na noite da origem, e cada revisão só vê o que existia naquela manhã. Mostra o fechamento da venda, cada semana em duas leituras, o erro por distância e por mês, a venda por tipo de dia e três jeitos de manter os pesos. |
| `modelo.py` | O modelo calendário + AR(1) da aula «Modelo contra baseline», a régua e a faixa de 80% da aula «Intervalos e cenários», com a venda separada entre o número da noite e o número fechado. Não imprime nada. |
| `dados/venda_2026.csv` | A venda de 01/01 a 26/04/2026, lida na manhã de 27/04: `unidades_noite` (o número lido às 22h), `unidades` (o número fechado, vazio se ainda não fechou) e `fechada_em` (o dia em que fechou). |
| `dados/calendario_2026.csv` | Feriados e dias fechados de 01/01 a 31/05/2026, com as mesmas colunas do calendário de `dados/loja`. |
| `dados/gerar_2026.py` | Gera os dois arquivos de 2026. Abra depois da aula. |
| `minha-politica.md` | A folha do exercício: a política do pedido de camisetas. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. O statsmodels não é necessário.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 monitor.py
python3 monitor.py --horizonte 14
python3 monitor.py --revisao 2026-03-16
python3 monitor.py --salvar previsoes.csv
```

O `monitor.py` termina em uns quatro segundos. O `--horizonte` aceita 7, 14, 21 e 28. O `--revisao` aceita uma segunda-feira de 2026-02-09 a 2026-04-27 e mostra o painel como estava naquela manhã. Ele importa o `modelo.py` da mesma pasta: deixe os dois juntos. Se aparecer `No module named 'modelo'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

O `--salvar` grava uma linha por dia previsto e distância, com a origem, o número da noite, a venda fechada, a data em que fechou, a régua e a previsão, o piso e o teto de cada jeito de manter os pesos.

Para gerar de novo a venda de 2026:

```bash
cd dados
python3 gerar_2026.py
```

A saída é `venda_2026=116 fechados=114 abertos=2 calendario=151`. O gerador só usa a biblioteca padrão e sai igual toda vez.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
