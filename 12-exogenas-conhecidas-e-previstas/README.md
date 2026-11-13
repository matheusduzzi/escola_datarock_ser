# Exógenas conhecidas e previstas

Os programas da aula, os dados das entregas do bairro e a folha do exercício. Os programas leem o calendário da loja em `dados/loja`, na raiz do kit do curso, e as entregas, a chuva e a previsão do tempo na pasta `dados/` dessa aula.

| Arquivo | O que faz |
|---|---|
| `dados/entregas.csv` | As entregas do bairro por dia, de 01/01/2024 a 31/12/2025. |
| `dados/chuva.csv` | A chuva de cada dia, em milímetros, no mesmo período. Chuva forte é 5 mm ou mais. |
| `dados/previsao_chuva.csv` | A previsão do tempo publicada em cada dia de 2025, com a chance de chuva forte para cada um dos 14 dias seguintes. |
| `dados/gerar.py` | Gera os três arquivos e conta, no começo, como cada número nasce. |
| `exogenas.py` | O modelo: a regressão do calendário no log das entregas, com a coluna da chuva forte. Não imprime nada. |
| `comparar.py` | Compara, nas mesmas origens, o modelo sem chuva, com a chuva que caiu e com a previsão do tempo da noite da origem. |
| `cenarios.py` | Os cenários seco e com chuva de uma semana de escala, em entregas e entregadores. |
| `minha_chuva.py` | O exercício: você escreve a função `chuva_na_noite`, e o arquivo compara e roda o teste do futuro. |
| `minhas-respostas.md` | A folha de respostas do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 comparar.py
python3 comparar.py --horizonte 1
python3 comparar.py --salvar previsoes.csv
python3 cenarios.py --origem 2025-12-01 --semana 2025-12-08
python3 cenarios.py
python3 minha_chuva.py
```

O `comparar.py` termina em cerca de um segundo. Os programas importam o `exogenas.py` da mesma pasta: deixe todos juntos. Se aparecer `No module named 'exogenas'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

O `comparar.py` aceita `--horizonte` de 1 a 14, porque a previsão do tempo vai até 14 dias. O `cenarios.py` aceita uma origem até 31/12/2025, a última noite com entregas e chuva, e uma semana que termine até 31/01/2026, onde o calendário acaba. Sem opções, ele monta a semana de 05/01/2026 na noite de 31/12/2025.

O `minha_chuva.py` para com `NotImplementedError` até você escrever a função `chuva_na_noite`. Se a função usar a chuva ou uma previsão de depois da origem, o teste do futuro mostra o primeiro dia em que a chance mudou e o programa sai com erro.

Para gerar de novo os dados:

```bash
python3 dados/gerar.py
```

A saída é `entregas=731 dias_de_chuva_forte=193 previsoes=5110`. O gerador só usa a biblioteca padrão e sai igual toda vez.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
