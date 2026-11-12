# Kit do curso Séries temporais

Os arquivos que você usa nas aulas: o diagnóstico, a revisão rápida, a venda diária da loja física da Loja Exemplo e o calendário de feriados e promoções. Cada aula traz a sua pasta com os dados e programas dela.

## Como o kit está organizado

| Pasta | O que tem |
|---|---|
| `00-apresentacao/` | O [diagnóstico](00-apresentacao/diagnostico.md), a [revisão rápida](00-apresentacao/revisao-rapida.md), os dados e os programas das tarefas 1 e 2, a [folha de respostas](00-apresentacao/minhas-respostas.md), a [folha da ordem de estudo](00-apresentacao/minha-ordem.md) e a `primeira_olhada.py` da apresentação. |
| `dados/loja/` | A venda diária de 2024 e 2025 e o calendário até janeiro de 2026. Ver [dados/loja/LEIA-ME.md](dados/loja/LEIA-ME.md). |
| `NN-titulo/` | Uma pasta por aula, com o número e o título da aula. Elas entram no kit junto com as aulas. |

Os comandos das aulas rodam de dentro da pasta da aula. Quando uma aula usa a venda da loja, ela diz o caminho, por exemplo `../dados/loja/venda_diaria.csv`.

## Do que você precisa

- Python 3.9 ou mais novo, com o pandas. É o ambiente de Python para dados.
- Um editor de código e um terminal.

O NumPy vem junto com o pandas. O matplotlib, o statsmodels e as outras bibliotecas entram nas aulas que usam cada uma, com a versão e o comando de instalação.

Na pasta do kit, instale o que o diagnóstico usa:

```bash
python3 -m pip install -r requirements.txt
```

E veja se funcionou:

```bash
cd 00-apresentacao
python3 tarefa1.py
```

A saída mostra os cinco primeiros dias de maio, com as colunas `data` e `unidades`, a linha `linhas no arquivo: 18` e `None`, porque a resposta ainda está em branco. Se aparecer `No module named 'pandas'`, o `pip` instalou em outro Python. Rode `python3 -m pip install pandas` com o mesmo `python3` que você usa para rodar o programa. No Windows, troque `python3` por `py`.

Para gerar de novo a venda da loja:

```bash
cd ../dados/loja
python3 gerar.py
```

A saída é `venda_diaria=722 dias_no_calendario=731 sem_registro=9 calendario=762`. O gerador só usa a biblioteca padrão e sai igual toda vez.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.

## Licença

A licença de uso e redistribuição do kit ainda vai ser definida pela Escola Datarock. Até lá, use os arquivos para estudar o curso. Os dados da Loja Exemplo são inventados e foram gerados pelos programas do próprio kit.

## Aulas com arquivos neste kit

| Pasta | Aula |
|---|---|
| [00-apresentacao/](00-apresentacao/) | Apresentação |
| [01-unidade-frequencia-e-horizonte/](01-unidade-frequencia-e-horizonte/) | Unidade, frequência e horizonte |
| [02-tendencia-sazonalidade-ciclo-e-ruido/](02-tendencia-sazonalidade-ciclo-e-ruido/) | Tendência, sazonalidade, ciclo e ruído |
| [03-auditar-a-venda-diaria/](03-auditar-a-venda-diaria/) | Auditar a venda diária |
| [04-decompor-sem-antecipar-o-futuro/](04-decompor-sem-antecipar-o-futuro/) | Decompor sem antecipar o futuro |
| [05-estacionariedade-e-dickey-fuller/](05-estacionariedade-e-dickey-fuller/) | Estacionariedade e Dickey-Fuller |
| [06-naive-e-naive-sazonal/](06-naive-e-naive-sazonal/) | Naive e naive sazonal |
| [07-backtesting-e-cortes-temporais/](07-backtesting-e-cortes-temporais/) | Backtesting e cortes temporais |
| [08-mae-rmse-mape-e-wmape/](08-mae-rmse-mape-e-wmape/) | MAE, RMSE, MAPE e WMAPE |
| [10-arima-sarimax-e-suavizacao/](10-arima-sarimax-e-suavizacao/) | ARIMA, SARIMAX e suavização |
| [16-monitoramento-e-retreino/](16-monitoramento-e-retreino/) | Monitoramento e retreino |
