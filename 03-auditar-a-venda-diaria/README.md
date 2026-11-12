# 03. Auditar a venda diária

Os arquivos da aula «Auditar a venda diária» do curso Séries temporais. Rode os comandos de dentro dessa pasta.

| Arquivo | Para que serve |
|---|---|
| `auditar.py` | As contas da aula: põe a venda no calendário, dá a situação de cada dia (completo, sem registro, loja fechada, incompleto), mostra a cobertura de cada mês e o que muda quando o vazio vira zero. Grava `serie_auditada.csv`. |
| `dados/venda_jan26.csv` | A venda de janeiro de 2026 que o Nando exportou em 20/01, às 15h10. É o arquivo do exercício. |
| `minhas-respostas.md` | A folha do exercício. |

O `auditar.py` usa a venda da loja física e o calendário que vêm com o kit, em `dados/loja` na raiz do kit. Ele acha essa pasta sozinho; não precisa copiar nada.

## Como rodar

Você precisa do Python com o pandas, como no README do kit do curso. Não precisa de internet.

```bash
python3 auditar.py
```

A saída é a mesma da seção 5 da aula e sai igual toda vez. O programa grava `serie_auditada.csv` nessa pasta, com 731 linhas, uma por dia de 2024 e 2025. Rodar de novo escreve o mesmo arquivo por cima.

Se o programa parar com a frase "pare aqui", a venda tem uma data repetida ou fora do calendário. Ele diz quais datas são, sai com código 1 e não grava uma série nova.

O exercício usa `dados/venda_jan26.csv`, o calendário em `../dados/loja/calendario.csv` e a venda de 2025 em `../dados/loja/venda_diaria.csv`. Você escreve o seu próprio código no pandas; pode partir do `auditar.py`.

No Windows, troque `python3` por `py`.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
