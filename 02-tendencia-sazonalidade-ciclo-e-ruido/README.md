# 02. Tendência, sazonalidade, ciclo e ruído

Os arquivos da aula «Tendência, sazonalidade, ciclo e ruído» do curso Séries temporais. Rode os comandos de dentro dessa pasta.

| Arquivo | Para que serve |
|---|---|
| `componentes.py` | As contas da aula: a venda em três frequências, a tendência, o peso de cada dia da semana, a onda do ano, o ruído, os casos em que a soma conta outra história e um sábado montado pelas partes. |
| `hipoteses-serie.md` | A folha de hipóteses sobre a série. A aula preenche uma para a venda por dia; o exercício pede uma para a venda por semana. |

O `componentes.py` usa a venda da loja física e o calendário que vêm com o kit, em `dados/loja` na raiz do kit. Ele acha essa pasta sozinho; não precisa copiar nada.

## Como rodar

Você precisa do Python com o pandas, como no README do kit do curso. O NumPy vem junto com o pandas. Não precisa de internet.

```bash
python3 componentes.py
```

A saída é a mesma da seção 4 da aula e sai igual toda vez. O começo do programa conta o que cada parte calcula.

O exercício usa a mesma venda e o mesmo calendário. Você escreve o seu próprio código no pandas, lendo os arquivos em `../dados/loja/`; as dicas do exercício mostram por onde começar.

No Windows, troque `python3` por `py`.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
