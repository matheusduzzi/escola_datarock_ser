# Modelo contra baseline

Os programas da aula e a folha do exercício. Os programas leem a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `modelos.py` | Os modelos: as duas previsões simples (semana passada e mesmo dia, 4 semanas), o Holt-Winters no log com tendência amortecida e período 7, e a regressão do calendário com erro AR(1). Não imprime nada. |
| `comparar.py` | Faz as previsões de todas as origens, de 31/08/2025 em diante, com cada modelo ajustado só com a venda até a origem, e compara os quatro nos mesmos dias. |
| `minha_comparacao.py` | O exercício: você escreve a função `meu_modelo`, e o arquivo compara o seu modelo com a régua e roda o teste do futuro. |
| `minhas-respostas.md` | A folha de respostas do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. O statsmodels não é necessário: o `modelos.py` faz as contas com o NumPy, para você ver cada passo do ajuste.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 comparar.py
python3 comparar.py --horizonte 14
python3 comparar.py --salvar previsoes.csv
python3 minha_comparacao.py
```

O `comparar.py` termina em uns dois segundos. Ele e o `minha_comparacao.py` importam o `modelos.py` da mesma pasta: deixe os três juntos. Se aparecer `No module named 'modelos'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

O `minha_comparacao.py` para com `NotImplementedError` até você escrever a função `meu_modelo`. Se a função usar venda de depois da origem, o teste do futuro mostra o primeiro dia em que a previsão mudou e o programa sai com erro.

O `--salvar` grava uma linha por dia previsto, com a origem, a venda real e a previsão de cada modelo. Abra no pandas ou numa planilha.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
