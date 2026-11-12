# 01. O que prever, frequência e horizonte

Os arquivos da aula «O que prever, frequência e horizonte» do curso Séries temporais. Rode os comandos de dentro dessa pasta.

| Arquivo | Para que serve |
|---|---|
| `contrato.py` | As contas da aula: o que existe na noite de 01/12/2025, a ordem dos dias, a venda média por dia da semana, a mesma regra simples feita 7, 14, 35 e 63 dias antes e a regra aplicada à primeira semana de janeiro. |
| `contrato-previsao.md` | A folha do contrato da previsão. A aula preenche uma para a escala de janeiro; o exercício pede uma para cada pedido novo. |

O `contrato.py` usa a venda da loja física e o calendário que vêm com o kit, em `dados/loja` na raiz do kit. Ele acha essa pasta sozinho; não precisa copiar nada.

## Como rodar

Você precisa do Python com o pandas, como no README do kit do curso. O NumPy vem junto com o pandas. Não precisa de internet.

```bash
python3 contrato.py
```

A saída é a mesma da seção 4 da aula e sai igual toda vez. O embaralhamento da parte 2 também é sempre o mesmo. O começo do programa conta o que cada parte calcula.

O exercício usa a mesma venda e o mesmo calendário. Você escreve o seu próprio código no pandas, lendo os arquivos em `../dados/loja/`; as dicas do exercício mostram por onde começar.

No Windows, troque `python3` por `py`.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
