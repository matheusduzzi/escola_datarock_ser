# 05. Estacionariedade e Dickey-Fuller

Os programas da aula «Estacionariedade e Dickey-Fuller». Eles leem a venda e o calendário da loja em `../dados/loja/`, que vêm com o kit desde a apresentação, e a venda do quiosque em `dados/`, nessa pasta.

| Arquivo | O que faz |
|---|---|
| `dickey_fuller.py` | O teste de Dickey-Fuller aumentado, escrito com NumPy, com a receita do `adfuller` do statsmodels 0.15.0. |
| `testar.py` | Roda o teste numa versão da venda (log, sem o dia da semana, diferença, um trecho) e mostra os outros sinais da série. |
| `estacionariedade.py` | A saída da aula: o teste na venda da loja e em séries sorteadas com o mecanismo escrito. |
| `dados/quiosque.csv` | A venda do quiosque do shopping, de 03/06/2024 a 30/11/2025, para o exercício. |
| `dados/gerar_quiosque.py` | Como a venda do quiosque nasce. Abra depois de fazer o exercício. |
| `parecer.md` | A folha do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas. O NumPy vem junto com o pandas. É o mesmo ambiente da apresentação: o `requirements.txt` da raiz do kit já instala o que essa aula usa.

O statsmodels não é preciso aqui. O `dickey_fuller.py` faz a conta linha a linha, para você ver cada passo. Se você tiver o statsmodels instalado, compare com `adfuller(x, regression="c", autolag="AIC")`: a estatística, o p-valor, as defasagens e os valores críticos precisam dar iguais.

## Como rodar

Na pasta dessa aula:

```bash
python3 estacionariedade.py
python3 testar.py loja --log --regressao ct
python3 testar.py loja --log --sem-dia-da-semana --dif 1
python3 testar.py dados/quiosque.csv --log --sem-dia-da-semana
```

O `estacionariedade.py` leva alguns segundos: a parte 5 roda o teste 3.500 vezes. Com `--repeticoes 100` ele fica mais rápido, e os números da parte 5 mudam um pouco.

O `testar.py` aceita `--de` e `--ate` para um trecho, `--log`, `--sem-dia-da-semana` (junto com `--log`), `--dif 1` ou `--dif 7` e `--regressao c` ou `ct`. Para a loja, `--corte` muda a noite até onde a venda entra; o padrão é 01/12/2025. Se o trecho tiver menos de 60 dias que servem, ele para com `PAROU:` e código 1.

Para gerar a venda do quiosque de novo: `python3 dados/gerar_quiosque.py`. A saída é `quiosque=542 linhas dias_no_calendario=546 sem_linha=4 fechado=2`, e o arquivo sai igual toda vez.

Os programas também rodam da raiz do kit, por exemplo `python3 05-estacionariedade-e-dickey-fuller/estacionariedade.py`: eles acham `dados/loja` pelo próprio caminho. O caminho do quiosque no `testar.py` é a partir da pasta em que você está.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
