# Monitor Diário de Convenções e Aditivos — Alagoas

Ferramenta Python para o Departamento Pessoal da Cercont. A interface permite clicar em **Consultar novidades** para pesquisar o Mediador, obter documentos e atualizar uma nova cópia do controle, sem anexos ou arquivo de resultados preparado pelo usuário.

Com Python instalado, extraia o ZIP e dê dois cliques em `abrir_monitor.bat` no Windows. A primeira abertura prepara as dependências automaticamente; nas próximas, abre o monitor sem comandos no CMD. Veja o [GUIA_MONITOR.md](GUIA_MONITOR.md). Na janela, selecione **Ano de 2026** para o retorno anual ou **Últimos 7 dias** para o acompanhamento recente. O relatório lista todos os instrumentos encontrados, mesmo os já existentes no controle; só os novos são acrescentados à cópia cumulativa. Não há agendamento automático.

A consulta anual anterior, com o filtro por UF, de 01/01/2026 a 09/10/2026 foi concluída: 22 CCTs e 2 aditivos, com os 24 documentos lidos, abrangência em Alagoas confirmada e nenhuma pendência. Inclui quatro registros nacionais SRT. No teste inicial dos últimos sete dias, a pesquisa de aditivos respondeu HTTP 500, registrado como pendência. Consulte o [diagnóstico técnico](DIAGNOSTICO_MEDIADOR.md).

A [alternativa assistida](GUIA_ASSISTIDO.md) permanece disponível. As regras de trabalho e proteção de dados estão em [AGENTS.md](AGENTS.md).

A versão atual reúne quatro pesquisas: CCT e aditivo por UF AL e pelos municípios de AL, usando Todos disponíveis do seletor oficial. Qualquer município de Alagoas é aceito quando confirmado no documento, sem exigir abrangência no estado inteiro. A busca ampliada ainda precisa de validação real, incluindo o exemplo AL000030/2026; os resultados anteriores não comprovam sua completude.

Após a consulta, o painel documental permite pesquisar os resultados, conferir cláusulas completas com páginas, examinar os dois assuntos do resumo executivo e exportar um PDF. A opção **Consultas** no menu lateral também abre uma consulta salva. A análise é textual e conservadora, com pendências explícitas; não confirma vigência jurídica nem substitui a leitura integral pelo DP. Veja os limites e a atualização em [GUIA_MONITOR.md](GUIA_MONITOR.md).
