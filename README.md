# Hub de agentes — Cercont

A abertura do programa apresenta um hub para escolher a ferramenta. **Recibo de Rescisão Avulsa** permite informar verbas e valores manualmente, conferir a prévia e gerar PDF ou Excel no modelo enviado pelo usuário; não calcula direitos rescisórios. O **Monitor de CCT — Alagoas** está disponível; **Conferência de Admissão** aguarda as regras que serão definidas pelo usuário e ainda não executa conferências.

## Monitor Diário de Convenções e Aditivos — Alagoas

**Regularização de Obras (SERO)** está disponível no hub como **A configurar**, com tela na mesma janela e botão de retorno. Seus documentos, regras e funcionalidades serão definidos posteriormente; ainda não realiza cálculos, consultas ou envios ao SERO.

Para acessar todos os módulos sem rolar a tela, use **Abrir módulo** no topo do hub. **Calculadoras** também tem um botão fixo no topo, à direita da lista de módulos. O cartão do SERO aparece mais abaixo na lista de cartões. Caso essas opções não apareçam, feche o programa e atualize `hub_agentes.py` na mesma pasta do `abrir_monitor.bat` que você utiliza; baixar outro ZIP não atualiza automaticamente uma instalação anterior.

**Calculadoras** reúne Afastamento; Seguro-Desemprego; Desoneração da Folha; Juros — FGTS em Atraso; e Custo Mensal / Anual do Funcionário. FGTS em atraso busca automaticamente os coeficientes oficiais da CAIXA e simula o recolhimento mensal **SEFIP/GRF**. As outras quatro opções continuam **A configurar**.

### FGTS em atraso — busca automática

1. No hub, clique **Calculadoras → Calculadora de Juros — FGTS em Atraso**.
2. Escolha trabalhadores, aprendizes ou ambos. Informe competência em MM/AAAA, data de pagamento em DD/MM/AAAA e os valores de remuneração separados. Razão social e e-mail são opcionais e não são enviados à internet.
3. Selecione o regime de recolhimento. A implementação atende **SEFIP/GRF mensal padrão**, não FGTS Digital ou eSocial doméstico. A partir de 03/2024, o SEFIP exige confirmação explícita de exceção legal (administração pública ou códigos 650/660); o aplicativo não determina esse enquadramento. Confirme também que não há suspensão ou prorrogação especial aplicável.
4. Para 10/2001 a 12/2006, selecione a regra histórica da contribuição social de 0,5%. O intervalo foi corrigido com base no edital oficial, inclusive outubro a dezembro de 2001. A categoria trabalhadores considera alíquota de 8%; aprendizes de 2%, com fator da tabela própria. Aprendizes anteriores a 2001 não são suportados.
5. Clique **Buscar coeficiente e calcular**. O programa consulta o catálogo oficial, baixa o ZIP do edital e lê a célula exata da Tabela 7 por competência e pagamento. Não exige anexos ou preparação de tabelas. A consulta ocorre em segundo plano e o resultado é descartado se o preenchimento mudar durante a busca.

A tela mostra FGTS principal, encargos agregados (atualização, juros, multa e contribuição social quando devida), total, coeficiente, fator aplicado, vigência, página, fonte e SHA-256. Os componentes dos encargos não são separados, pois a tabela fornece um coeficiente agregado. O PDF oficial fica em `saidas/coeficientes_fgts`, fora do Git. Nenhuma remuneração ou identificação é transmitida. Não há login, pagamento, emissão de guia, consulta à conta do FGTS ou agendamento.

O edital determina **truncamento em duas casas decimais, sem arredondamento**. A imagem da Econet contém arredondamento: no exemplo R$ 1.200 × 0,104665349 = R$ 125,5984188, o total truncado é R$ 125,59, com principal R$ 96,00 e encargos R$ 29,59; arredondado, R$ 125,60 e R$ 29,60, como na imagem. A tela mostra o valor arredondado apenas para comparação, distinguindo-o do total conforme o edital.

Datas não publicadas, fins de semana/feriados sem célula, competência ausente, mais de uma célula correspondente, formato alterado, falha de rede ou bloqueio impedem o cálculo. Não há interpolação nem uso de outra data. A busca atende editais mensais individualmente publicados no catálogo; arquivos anuais agrupados não são processados nesta versão. Não calcula recolhimento rescisório nem suspensões especiais. As alíquotas padrão não cobrem categorias contratuais especiais.

**Atualização no Windows:** feche o hub, substitua `hub_agentes.py` e `calculadora_fgts.py`, acrescente `coeficientes_fgts.py` na mesma pasta de `abrir_monitor.bat` e reabra o programa. Não há novas dependências. O preenchimento permanece na sessão ao alternar calculadoras, mas não é salvo ao fechar. **Conferir dados** apenas valida as entradas; **Limpar** apaga o formulário.

A consulta real à CAIXA foi validada com o edital 09/2026 e o caso da imagem. Veja [DIAGNOSTICO_FGTS.md](DIAGNOSTICO_FGTS.md), que distingue essa evidência dos testes fictícios. Foram executados 99 testes locais. A interface no Windows ainda precisa de conferência visual nesse sistema.

O hub também inclui **Conferência de Folhas de Pagamentos (Auditor)**, com status **A configurar**. A entrada abre uma tela na mesma janela com retorno ao hub; os documentos, regras de auditoria e relatórios serão definidos posteriormente. Ainda não processa folhas de pagamento.

Ferramenta Python para o Departamento Pessoal da Cercont. A interface permite clicar em **Consultar novidades** para pesquisar o Mediador, obter documentos e atualizar uma nova cópia do controle, sem anexos ou arquivo de resultados preparado pelo usuário.

Com Python instalado, extraia o ZIP e dê dois cliques em `abrir_monitor.bat` no Windows. A primeira abertura prepara as dependências automaticamente; nas próximas, abre o monitor sem comandos no CMD. Veja o [GUIA_MONITOR.md](GUIA_MONITOR.md). Na janela, selecione **Ano de 2026** para o retorno anual ou **Últimos 7 dias** para o acompanhamento recente. O relatório lista todos os instrumentos encontrados, mesmo os já existentes no controle; só os novos são acrescentados à cópia cumulativa. Não há agendamento automático.

A consulta anual anterior, com o filtro por UF, de 01/01/2026 a 09/10/2026 foi concluída: 22 CCTs e 2 aditivos, com os 24 documentos lidos, abrangência em Alagoas confirmada e nenhuma pendência. Inclui quatro registros nacionais SRT. No teste inicial dos últimos sete dias, a pesquisa de aditivos respondeu HTTP 500, registrado como pendência. Consulte o [diagnóstico técnico](DIAGNOSTICO_MEDIADOR.md).

A [alternativa assistida](GUIA_ASSISTIDO.md) permanece disponível. As regras de trabalho e proteção de dados estão em [AGENTS.md](AGENTS.md).

A versão atual reúne quatro pesquisas: CCT e aditivo por UF AL e pelos municípios de AL, usando Todos disponíveis do seletor oficial. Qualquer município de Alagoas é aceito quando confirmado no documento, sem exigir abrangência no estado inteiro. A busca ampliada ainda precisa de validação real, incluindo o exemplo AL000030/2026; os resultados anteriores não comprovam sua completude.

Após a consulta, o painel documental permite pesquisar os resultados, conferir cláusulas completas com páginas, examinar os dois assuntos do resumo executivo e exportar um PDF. A opção **Consultas** no menu lateral também abre uma consulta salva. A análise é textual e conservadora, com pendências explícitas; não confirma vigência jurídica nem substitui a leitura integral pelo DP. Veja os limites e a atualização em [GUIA_MONITOR.md](GUIA_MONITOR.md).
