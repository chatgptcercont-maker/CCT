# Consulta automática de coeficientes do FGTS

Verificação realizada em 15/10/2026. Escopo: simulação mensal SEFIP/GRF, Tabela 7; sem envio de dados pessoais ou financeiros para serviços externos.

## Fonte e mecanismo público

- Downloads FGTS: https://www.fgts.gov.br/Paginas/empregador/downloads-empregador.aspx
- Downloads CAIXA: https://www.caixa.gov.br/site/paginas/downloads.aspx
- JavaScript público do catálogo: https://www.caixa.gov.br/Style%20Library/js/downloads.js
- Categoria oficial 850: FGTS — Coeficientes. O catálogo público SharePoint fornece título, descrição, URL e data de modificação dos editais.
- Endpoint de listagem: `/_api/web/lists/getbytitle('Downloads')/Items`, filtrando `Categoria/ID eq 850`, arquivos publicados, com paginação `d.__next` quando presente.
- Os links diretos de alguns editais devolveram redirecionamentos para si mesmos. O endpoint público padrão SharePoint `/_api/web/GetFileByServerRelativeUrl('/Downloads/FGTS-coeficientes/…zip')/$value` entregou o mesmo arquivo publicado com HTTP 200. Não houve uso de credenciais, cookies de terceiros, alteração de certificados ou desativação de HTTPS.
- Não se usa a API privada de cálculo da Econet. Apenas seu formulário e a imagem enviados pelo usuário serviram de referência de campos e caso de comparação.

## Evidência de acesso real

O fluxo completo de `calcular_online`, sem mocks, consultou o catálogo e baixou o edital:

- Título: Edital 09/2026.
- Fonte: https://www.caixa.gov.br/Downloads/FGTS-coeficientes/ED_202609_Rec_atraso.zip
- Conteúdo: `ED_202609-Rec.atraso.pdf`, 1.548 páginas; PDF de 10.774.687 bytes.
- SHA-256 do PDF: `72f3f2beccde9e62dbfbabb805b068521c90b54a20382d7c0a6e7be28e2bdff4`.
- Vigência: 21/09/2026 a 20/10/2026.
- Página 104, Tabela 7: competência 02/2024, pagamento 20/10/2026, coeficiente **0,104665349**.
- Remuneração de conferência: R$ 1.200,00; principal 8%: R$ 96,00.
- Produto: R$ 125,5984188.
- Total truncado conforme edital: **R$ 125,59**, encargos agregados R$ 29,59.
- Comparação arredondada: **R$ 125,60**, encargos R$ 29,60, reproduzindo os centavos da imagem da Econet.

O coeficiente real coincide com o da imagem. A diferença de centavos decorre do critério de arredondamento: a página 4, item 1.4.2.3 do edital, orienta duas casas decimais **sem arredondamento**. A aplicação mantém esse critério e exibe a comparação arredondada separadamente.

## Regras lidas no documento original

Páginas 3 e 4, itens 1.1, 1.2 e 1.4:

- Tabelas 1 a 7 contêm 8% de depósito e encargos legais; multiplicar o coeficiente pela remuneração, não pelo FGTS principal.
- Aprendizes, sem contribuição social: fator 0,25 sobre esse produto.
- Contribuição social de 0,5%: competências 10/2001 a 12/2006, observadas as isenções do quadro 1.
- Trabalhadores padrão com contribuição social devida: fator 1,0625; aprendizes com contribuição social devida: fator 0,3125.
- A partir de 03/2024 o recolhimento regular migra ao FGTS Digital, observadas as exceções descritas no edital. A aplicação bloqueia esse regime e exige confirmação explícita para exceções SEFIP.

Não estão implementados enquadramentos especiais por categoria, cálculo rescisório ou suspensões de vencimento. Não se infere automaticamente a situação jurídica do empregador.

## Verificações e limites

`python -m unittest discover -s tests -q`: 99 testes passaram. Incluem seleção exata de coluna/bloco/data, ausência de célula, vigência, duplicidade, fatores de aprendiz/contribuição social, truncamento, comparação arredondada, proteção contra URLs externas, HTTP 403 sem tentativas de contorno, validação de regime e cópia local do edital.

Esses testes usam dados sintéticos e mocks onde indicado. A comprovação de acesso real é a consulta descrita acima, distinta da suíte. A aparência e os cliques completos no Windows ainda não foram testados neste ambiente.

A busca automática é limitada aos editais mensais individualmente listados. Datas cobertas somente por ZIPs anuais agrupados ou ainda não publicadas são recusadas. Nunca se substitui uma célula ausente por data próxima, coeficiente da imagem ou extrapolação. Falhas da CAIXA e alterações de formato são informadas; a ferramenta não emite guias nem confirma pagamento.
