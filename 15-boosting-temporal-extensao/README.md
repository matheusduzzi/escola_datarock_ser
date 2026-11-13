# Boosting temporal (extensão)

Os programas da aula e a folha do exercício. Os programas leem a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `modelos.py` | O mesmo arquivo da aula 11: a régua (mesmo dia, 4 semanas) e o calendário + AR(1), que é o modelo do ajuste da semana. Não imprime nada. |
| `boosting.py` | As colunas do boosting, feitas só com a venda até a noite da decisão; o boosting de árvores escrito com NumPy; e o mesmo ajuste no LightGBM e no XGBoost. Não imprime nada. |
| `comparar_boosting.py` | Põe o boosting na comparação da aula 11: mesmas origens, mesmos dias, cada ajuste só com a venda até aquela noite. |
| `meu_boosting.py` | O exercício: você escreve a função `minha_coluna`, e o arquivo roda o teste do futuro e a comparação com e sem ela. |
| `minhas-respostas.md` | A folha de respostas do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. Com isso, tudo roda com o boosting do kit, que é o padrão.

O LightGBM e o XGBoost são opcionais. Eles fazem o mesmo ajuste com a opção `--motor`. Em 12/11/2026, as versões mais novas no PyPI eram o LightGBM 4.7.0, que pede Python 3.10 ou mais novo, e o XGBoost 3.4.1, que pede Python 3.12 ou mais novo. Para instalar:

```bash
python3 -m pip install lightgbm
python3 -m pip install xgboost
```

Se a instalação falhar, siga com o motor do kit: a aula inteira funciona com ele.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 comparar_boosting.py
python3 comparar_boosting.py --horizonte 14
python3 comparar_boosting.py --salvar previsoes.csv
python3 comparar_boosting.py --motor lightgbm
python3 comparar_boosting.py --motor xgboost
python3 meu_boosting.py
```

O `comparar_boosting.py` leva cerca de um minuto com o motor do kit: ele faz 17 ajustes do boosting, cada um testando 4 folhas mínimas, e mais as comparações da parte 4. O `meu_boosting.py` leva uns 40 segundos. Os três programas importam o `modelos.py` e o `boosting.py` da mesma pasta: deixe os quatro arquivos juntos. Se aparecer `No module named 'boosting'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

Se você pedir `--motor lightgbm` sem o LightGBM instalado, o programa avisa, mostra o comando de instalação e sai com o código 2. Com o LightGBM ou o XGBoost, os números ficam perto dos da aula, mas não iguais: as bibliotecas fazem as faixas do histograma e o crescimento da árvore de outro jeito.

O `meu_boosting.py` para com `NotImplementedError` até você escrever a função `minha_coluna`. Se a função usar venda de depois da noite da decisão, o teste do futuro mostra o primeiro dia em que ela mudou e o programa sai com erro, sem rodar a comparação.

O `--salvar` grava uma linha por dia previsto, com a origem, a venda real e a previsão de cada modelo. Abra no pandas ou numa planilha.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
