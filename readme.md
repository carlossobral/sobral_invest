📌 API Sobral Invest

Bem-vindo à documentação da API Sobral Invest. Esta API fornece indicadores fundamentalistas, dividendos, payout e rankings de ações listadas na B3.

🚀 Endpoints Disponíveis

Ações

/acao/{ticker} → Retorna indicadores gerais da ação, incluindo preço atual.

/acao/{ticker}/dividendos → Histórico de dividendos e DY.

/acao/{ticker}/payout → Histórico de payout.

/acao/{ticker}/agenda_dividendos → Agenda de dividendos futuros.

Rankings (Top 30)

/ranking/dy → Ranking por Dividend Yield.

/ranking/roe → Ranking por ROE.

/ranking/graham → Ranking pelo valor intrínseco de Graham.

/ranking/bazin → Ranking pelo critério de Bazin.

/ranking/peterlynch → Ranking pelo critério de Peter Lynch.

/ranking/ebitda → Ranking por EBITDA.

/ranking/valor_mercado → Ranking por valor de mercado.

/ranking/margem_liquida → Ranking por margem líquida.

/ranking/receita_liquida → Ranking por receita líquida.

/ranking/divida_liquida → Ranking por dívida líquida.

/ranking/liquidez → Ranking por liquidez.

/ranking/dy_consistente?periodo=3 → Ranking por DY consistente em 3 ou 5 anos.

/ranking/payout_consistente?periodo=3 → Ranking por payout consistente em 3 ou 5 anos.

/ranking/consistente?periodo=3 → Ranking combinado de DY e payout consistentes.

📊 Estrutura de Resposta

Exemplo de resposta com dados válidos

{
  "Ticker": "PETR4",
  "PrecoAtual": 38.75,
  "DY_12M": 12.5,
  "Div_12M": 4.85,
  "ROE": 18.2,
  "P/L": 5.3
}

Exemplo de resposta sem dados válidos

{
  "Ticker": "CVCB3",
  "msg": "Sem dados válidos para payout."
}

⚙️ Observações

Os endpoints /atualizar e /health são internos e não aparecem na página inicial.

Todos os rankings retornam Top 30 ordenados.

Quando não há dados válidos, a API retorna uma mensagem clara em vez de zeros.

📌 Como usar

Acesse a API em: https://sobral-invest-b5ua.onrender.com/

Consulte os endpoints listados acima.

Use o parâmetro {ticker} com o código da ação (ex.: PETR4, VALE3).

📝 Licença

Este projeto é de uso livre para fins educacionais e de estudo.
