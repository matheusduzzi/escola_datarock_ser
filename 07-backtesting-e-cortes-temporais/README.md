# 07. Backtesting e cortes temporais

Os programas da aula «Backtesting e cortes temporais». Eles leem a venda e o calendário da loja em `../dados/loja/`, que vêm com o kit desde a apresentação.

| Arquivo | O que faz |
|---|---|
| `cortes.py` | Monta o plano do ajuste da semana, testa as seis regras do plano sem vazamento e roda as três previsões da aula 06 em cada noite. Com `--plano`, testa e roda um plano seu. |
| `plano_rafael.py` | O plano do Rafael, da prática guiada. |
| `meu_plano.py` | Onde você escreve o plano da escala do mês, no exercício. |
| `minhas-respostas.md` | A folha do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas. É o mesmo ambiente da apresentação: o `requirements.txt` da raiz do kit já instala o que essa aula usa.

## Como rodar

Na pasta dessa aula:

```bash
python3 cortes.py
python3 cortes.py --plano plano_rafael.py --contrato semana
python3 cortes.py --plano meu_plano.py --contrato mes
```

O primeiro comando mostra as cinco partes da aula, em uns 2 segundos. O segundo é o pedido 1 da prática guiada: ele termina com `FALHOU` e código 1, de propósito, porque o plano do Rafael tem vazamento.

O terceiro é do exercício. Antes de você escrever o plano, ele termina com `regra 1. o plano tem cortes: o plano está vazio`, `FALHOU` e código 1. Depois, ele precisa mostrar `plano sem vazamento: as seis regras passam` e os erros de cada parte.

O `--contrato` diz qual decisão o plano testa: `semana` (cada dia previsto 7 dias antes) ou `mes` (na noite do dia 1, o mês seguinte inteiro).

Os programas também rodam da raiz do kit, por exemplo `python3 07-backtesting-e-cortes-temporais/cortes.py`: eles acham `dados/loja` pelo próprio caminho. O `--plano` procura o arquivo primeiro na pasta de onde você rodou e depois na pasta da aula.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
