# Revisão rápida para o diagnóstico

Um exemplo curto de cada ideia que o diagnóstico usa. Os números daqui são outros, para você treinar sem ver a resposta. Se uma seção inteira for novidade, a apresentação diz qual aula estudar antes.

## 1. Datas e dias que faltam no pandas

Um arquivo de venda diária só tem linha nos dias em que o sistema gravou alguma coisa. Para ver os dias que faltam, eu crio o calendário completo e encaixo a venda nele:

```python
import pandas as pd

vendas = pd.DataFrame({
    "data": pd.to_datetime(["2025-08-01", "2025-08-02", "2025-08-04"]),
    "unidades": [150, 0, 140],
})
dias = pd.date_range("2025-08-01", "2025-08-04", freq="D")
serie = vendas.set_index("data")["unidades"].reindex(dias)
print(serie)
print(serie.isna().sum(), (serie == 0).sum())
```

A saída mostra 4 dias. O dia 3 aparece como `NaN`: ninguém sabe quanto vendeu. O dia 2 aparece como `0`: o sistema gravou e a venda foi zero. `serie.isna().sum()` conta os vazios (1) e `(serie == 0).sum()` conta os zeros (1). O `mean()` do pandas pula o `NaN` sozinho; `fillna(0)` antes do `mean()` transforma o dia vazio em zero e muda a média.

## 2. Filtrar um intervalo de datas dentro de uma função

Para pegar os 3 dias antes de 4 de agosto, sem o dia 4:

```python
def antes_de(vendas, corte, dias):
    corte = pd.Timestamp(corte)
    inicio = corte - pd.Timedelta(days=dias)
    return vendas[(vendas["data"] >= inicio) & (vendas["data"] < corte)]

print(antes_de(vendas, "2025-08-04", 3))
```

O `<` deixa o dia do corte de fora; `<=` traria o dia 4 para dentro. A janela é de dias do calendário: se um dia não tem linha, a tabela filtrada fica com menos linhas, e `len()` mostra quantas. `vendas[vendas["data"] < corte].tail(3)` faz outra conta: pega as 3 últimas linhas, que podem estar mais longe no passado quando falta um dia.

## 3. Distribuição normal e quantis

Se uma venda segue uma normal com média 100 e desvio 10:

- cerca de 95% dos dias ficam entre 100 − 1,96 × 10 e 100 + 1,96 × 10, isto é, de 80,4 a 119,6;
- metade dos dias fica acima da média;
- só 5% dos dias passam de 100 + 1,645 × 10 = 116,45.

O desvio mede o quanto os dias variam em torno de uma média fixa. Se a venda sobe ao longo do ano, parte dessa variação é a subida, e não sorte do dia.

## 4. Intervalo da média e faixa de um valor novo

Com 25 dias, média 100 e desvio 10:

- o intervalo de 95% para a média é 100 ± 1,96 × 10 / √25 = 100 ± 3,9;
- a faixa de 95% para um dia novo é 100 ± 1,96 × 10 × √(1 + 1/25) = 100 ± 20,0.

O primeiro diz onde está a média de longo prazo. Ele encolhe quando você junta mais dias. O segundo diz onde cai um dia que ainda não aconteceu. Ele nunca fica mais estreito que a variação de um dia para o outro.

## 5. Hipótese nula e p-valor

Um teste parte de uma hipótese nula e calcula o p-valor: a chance de ver um resultado tão extremo quanto o seu se a hipótese nula fosse verdadeira.

- p-valor alto quer dizer que os dados não deram motivo para rejeitar a hipótese nula. Isso não prova que ela é verdadeira. Com pouco dado, o teste tem pouco poder e quase nunca rejeita.
- p-valor baixo quer dizer que a hipótese nula ficou difícil de aceitar com esses dados e com as suposições do teste. Ele não diz nada sobre o período que ainda não aconteceu.
- Com limite de 5%, cada teste em que a hipótese nula é verdadeira tem 5% de chance de dar um falso alarme.
