# Venda diária da loja física da Loja Exemplo

Dois anos de venda da loja física e o calendário que a loja conhece antes de prever. Os números são inventados e saem do `gerar.py` dessa pasta.

| Arquivo | Linhas | Colunas | O que tem |
|---|---|---|---|
| `venda_diaria.csv` | 722 dias | `data`, `pedidos`, `unidades`, `ultimo_registro` (hora do último pedido gravado) | a venda de 01/01/2024 a 31/12/2025 |
| `calendario.csv` | 762 dias | `data`, `feriado` (nome, vazio se não é feriado), `loja_fechada` (1 se fechou), `promocao` (nome, vazio se não há) | de 01/01/2024 a 31/01/2026 |

Uma linha da venda é um dia. O arquivo não tem linha para todo dia do calendário, e nem toda linha é um dia completo. A aula 03 mostra como separar cada caso. A loja vende das 10h às 22h.

O calendário vai um mês além da venda de propósito: feriados, dias fechados e promoções planejadas já são conhecidos antes do dia. A aula 12 usa essa diferença entre o que se sabe antes e o que só se sabe depois.

## Como os dados nascem

O começo do `gerar.py` conta o mecanismo: o nível da venda, quanto ele sobe por ano, o peso de cada dia da semana, a onda do ano, as promoções, os feriados, o ruído e as falhas do sistema. Faça as análises das aulas antes de abrir o gerador. Depois abra e compare o que você encontrou com o que foi sorteado. Numa loja de verdade ninguém conhece o mecanismo; é por isso que o curso mede o erro e a incerteza.

O gerador também diz o que ele supõe e uma loja de verdade não garante: tendência em linha reta, efeito do dia da semana igual o ano todo, ruído sem memória de um dia para o outro e nenhuma ruptura. Várias aulas do curso tratam do que acontece quando uma dessas coisas falha.

## Gerar de novo

```bash
python3 gerar.py
```

A saída é `venda_diaria=722 dias_no_calendario=731 sem_registro=9 calendario=762`. O gerador só usa a biblioteca padrão do Python e sai igual toda vez. Não edite os CSVs à mão: aula que precisar de outro caso cria os próprios arquivos na pasta dela.
