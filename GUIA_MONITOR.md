# Monitor Diário de Convenções e Aditivos — Alagoas

O fluxo principal é online: abra a interface e clique em **Consultar novidades**. Não é necessário anexar PDFs, baixar documentos manualmente ou preparar `resultados.json`. A primeira preparação instala as bibliotecas e o navegador; depois, a consulta é manual por clique. Não há agendamento.

## Preparar e abrir no Windows

Instale Python 3.11 ou mais recente pelo site oficial, com Tcl/Tk e a opção **Add Python to PATH**. O Microsoft Edge também deve estar instalado.

1. Baixe o ZIP do projeto e use **Extrair tudo**.
2. Entre na pasta extraída e dê dois cliques em **abrir_monitor.bat**.
3. Na primeira abertura, aguarde a preparação automática. É necessária conexão com a internet para baixar as dependências fixadas em `requirements.txt`.
4. Nas próximas aberturas, o programa verifica os componentes e abre a janela sem reinstalar tudo. Uma mudança nos requisitos ou componentes ausentes aciona nova preparação.

Não é necessário digitar comandos no CMD. Uma janela de preparação aparece automaticamente e permanece aberta se houver erro. Não execute dentro do ZIP. A preparação usa `.venv` na pasta do projeto, não modifica planilhas e não requer instalação de pacotes globalmente. No Windows usa o Edge e não baixa Chromium. Se mover a pasta depois da preparação, o ambiente Python pode precisar ser recriado.

Para atualizar uma instalação existente, feche o monitor e copie **abrir_monitor.bat** e **preparar_monitor.py** da versão atual para a pasta existente. Preserve a pasta `.venv`, a configuração e os resultados. A preparação automática foi coberta por testes locais; o fluxo completo do arquivo BAT ainda precisa de validação no Windows.

No Windows, o Microsoft Edge precisa estar instalado. Ao clicar em **Consultar novidades**, o programa abre uma janela visível do Edge, em uma sessão separada do seu perfil pessoal. Aguarde sem fechar ou usar essa janela: o preenchimento dos filtros e a coleta continuam automáticos. No Linux, o coletor mantém o Chromium sem janela.

Essa mudança permite testar a compatibilidade com o navegador instalado depois do HTTP 403 relatado no Windows, onde a abertura manual do formulário funcionava. A causa exata do bloqueio não está confirmada; o Edge continua identificado como automatizado. Não são usados recursos para ocultar automação ou alterar as proteções do portal. Se o Edge também receber HTTP 403, a consulta é interrompida sem trocar de navegador ou repetir o acesso para contornar a recusa. O sucesso desta mudança no Windows ainda precisa de confirmação no computador do usuário; a validação anual anterior foi feita em Linux.

Na janela:

1. Se já houver controle, selecione a planilha `.xlsx` uma vez. Se houver várias abas, informe a aba. Sem controle, será criado um modelo novo.
2. Selecione **Ano de 2026** para obter os registros desde 01/01/2026 até hoje, ou **Últimos 7 dias** para acompanhamento recente. Clique em **Consultar novidades** e aguarde. A consulta roda em segundo plano, sem travar a interface.
3. Leia o resumo e clique em **Abrir resultados** para acessar os arquivos. Confira pendências antes de usar o resultado no DP.

O programa guarda a seleção localmente. Após cada execução com uma planilha de saída válida, a próxima consulta usa essa cópia cumulativa como controle, evitando perda de registros e duplicações. O arquivo original selecionado nunca é sobrescrito. Não deixe o Excel aberto sobre a planilha usada para leitura.

## O que é consultado

Fonte: `https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo`.

O navegador preenche os filtros e aciona o botão **Pesquisar** do próprio portal. São feitas quatro pesquisas: CCT por UF AL, CCT por todos os municípios de AL, aditivo de CCT por UF AL e aditivo de CCT por todos os municípios de AL. Acordos e aditivos de acordos não são selecionados e são recusados também na leitura dos documentos.

O campo **Período de registro** permite escolher:

- **Ano de 2026**: desde 01/01/2026 até a data atual em Alagoas. Como 2026 ainda está em andamento, não inclui datas futuras. É a opção inicial nas novas configurações.
- **Últimos 7 dias**: hoje e seis dias anteriores, em datas inclusivas.

A seleção é pela **data de registro**, não pela vigência nem apenas pelo ano impresso no número do instrumento. O período é recalculado a cada clique usando o fuso `America/Maceio`. O modo online não permite substituir a data atual por uma data fictícia.


A seleção territorial usa **Alagoas**, separada da UF de registro, e contempla os tipos de abrangência municipal, intermunicipal, estadual, interestadual e nacional. A pesquisa municipal aciona **Selecionar Município → Todos disponíveis** da UF AL; não usa apenas os municípios da inicial exibida. Não é necessário que o documento cubra o estado inteiro: qualquer município com abrangência confirmada em AL é aceito. As quatro pesquisas têm sessões separadas, e instrumentos repetidos são reunidos uma única vez. As contagens por pesquisa podem se sobrepor e não devem ser somadas. A presença de Alagoas é conferida novamente na cláusula do documento. Um registro de outra UF ou da SRT pode ser aceito se a cláusula confirmar abrangência em AL. A aplicação da convenção a cada cliente precisa de revisão do Departamento Pessoal.

A coleta acompanha a contagem de instrumentos e páginas informada pelo portal e tenta avançar pelos controles nativos de paginação. Controles desconhecidos, mudanças de contagem, duplicação de páginas ou mais de 200 páginas tornam a consulta incompleta, sem presumir ausência de registros.

## Documentos e relatórios

Cada execução cria uma pasta `saidas\online_DATA_HORA_IDENTIFICADOR`:

- `documentos`: arquivos oficiais obtidos pelo botão **Download** e PDFs de impressão, quando necessários;
- `coleta_automatica.json`: registro interno gerado pelo programa para auditoria; o usuário não prepara esse arquivo;
- `resultado\controle_convencoes_AL.xlsx`: nova cópia com registros novos acrescentados;
- `resultado\resumo_convencoes_AL.txt`: período, registros acrescentados e pendências;
- `resultado\log_convencoes_AL.txt`: operações, formatos dos documentos, hashes e erros de acesso;
- `resultado\instrumentos_consultados_AL.xlsx`: retorno de todos os registros consultados, inclusive os já existentes no controle, com abas **Instrumentos**, **Pendências** e **Consulta**;
- `resultado\instrumentos_consultados_AL.csv` e `.txt`: versões do retorno completo para leitura e exportação.

A lista completa também aparece na janela após a execução. Use a barra de rolagem para examiná-la. O resumo continua separando quantos registros são novos. Documentos indisponíveis aparecem como pendências, sem inventar data, tipo ou abrangência. A aba Consulta informa se a lista pôde ser confirmada como completa. O controle cumulativo recebe somente os documentos validados ainda não registrados nele.

O portal pode fornecer um original `.doc`, em vez de PDF. Nesse caso o programa preserva o original e abre a visualização oficial usando o fluxo de segurança do próprio site. Depois produz um PDF completo para leitura. O log identifica esse arquivo como **PDF de impressão**, sem chamá-lo de PDF original. Quando o portal oferece PDF original, esse PDF é usado. Os campos de registro, data, tipo e abrangência vêm do conteúdo original; registro/data/tipo também são conferidos no PDF processado.

A coluna `Documento` é um caminho relativo à pasta `online_...`, que contém `coleta_automatica.json`, não à subpasta `resultado`. Guarde a pasta inteira para manter rastreabilidade. O SHA256 identifica o PDF processado; o log também registra o hash do original baixado. Esses hashes verificam integridade, não a aplicabilidade jurídica do instrumento.

## Formato do controle e proteção do original

A primeira linha da aba precisa ter, uma vez cada, estes cabeçalhos, em qualquer ordem:

`Registro`, `Data de registro`, `Tipo`, `Abrangência territorial`, `Documento`, `Fonte`, `SHA256`.

Outras colunas são preservadas e ficam vazias nas linhas novas. Linhas anteriores e fórmulas usuais são mantidas na cópia. O programa não adapta automaticamente controles com outro formato. Se a planilha oficial tiver outros cabeçalhos, será necessário mapear o formato em uma etapa separada com uma cópia autorizada. Nenhuma planilha oficial da Cercont foi fornecida ou alterada no desenvolvimento.

Macros `.xlsm` não são aceitas. O `openpyxl` não garante a preservação de todos os recursos avançados do Excel, como desenhos ou conexões. Tabelas e gráficos não têm suas faixas ampliadas automaticamente. Confira a cópia antes de adotá-la; o original permanece intacto.

## Bloqueios e falhas

O programa usa cookies de sessão e o reCAPTCHA gerado pelo código original do site, sem ler ou reutilizar tokens. Não usa técnicas de ocultação, serviços de solução de CAPTCHA, credenciais externas ou verificadores HTTPS desativados.

Se houver CAPTCHA interativo, autenticação, HTTP 403/500, falha de rede, documento indisponível ou formato não reconhecido, a execução registra a pendência. O programa pode guardar instrumentos válidos obtidos antes ou apesar de uma falha em outra pesquisa, mas **não chama essa consulta de completa**. Nenhum erro é interpretado como ausência de novidades.

Nos testes reais iniciais dos últimos sete dias, a pesquisa de aditivos retornou **HTTP 500 com a mensagem oficial “Nenhum registro encontrado.”**. O programa preserva tanto o erro HTTP quanto essa mensagem. Por cautela, não converte essa resposta de erro em uma pesquisa concluída com zero resultados. Outros HTTP 500 também permanecem como falhas, independentemente do conteúdo.

A interface distingue consulta concluída de consulta com pendências. Na linha de comando, código de saída `0` significa processamento concluído sem pendências; `2` significa pendência. Zero inclusões também pode significar que todos os registros já estavam no controle.

## Testar e conferir

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Foram executados **37 testes com dados fictícios**, abrangendo períodos anual e semanal, rejeição de ACTs, número de registro versus número de solicitação, registros da SRT com cinco ou seis dígitos, preservação do controle, retorno anual de registros já existentes, repetição sem duplicatas, classificação de falhas, retorno HTTP 500 e conexão do botão com a coleta online. Os testes fictícios não comprovam acesso à fonte oficial.

Também foi executado um teste real pela internet: CCT **AL000242/2026**, registrada em **07/10/2026**, com abrangência confirmada em AL. O programa baixou o original `.doc`, acessou a visualização oficial, gerou um PDF de impressão e acrescentou uma linha à planilha de teste. Uma segunda execução online com essa planilha acrescentou **zero linhas**, sem duplicar o registro. Na pesquisa de aditivos, o erro HTTP 500 foi registrado nas duas execuções.

A consulta anual real de **01/01/2026 a 09/10/2026** foi concluída: **22 CCTs em três páginas e 2 aditivos em uma página**. Os 24 documentos oficiais foram baixados e lidos, com abrangência em AL confirmada, sem pendências; uma planilha nova de teste recebeu 24 registros. Quatro são registros nacionais SRT, com cinco dígitos, também aceitos pelo programa. A leitura usa o registro do cabeçalho do documento, pois linhas de pesquisa podem mencionar instrumentos anteriores. Essa execução está em `saidas/online_20261009_042138_f937a507`. As saídas e os documentos ficam locais, fora do Git.

Confira cada nova linha com os documentos e o link oficial, além das linhas antigas. PDFs digitalizados sem texto ou protegidos geram pendência; não há OCR.

O backend foi executado em Linux com Chromium, HTTPS verificado e dados oficiais. O vínculo do botão com o backend foi testado, mas a aparência e a execução da janela em uma máquina Windows ainda não foram testadas. A consulta anual dos dois tipos e a paginação foram validadas com dados reais; isso não garante disponibilidade permanente do portal.

## Alternativas

A mesma consulta online pode ser executada sem a janela:

```bat
.venv\Scripts\python.exe monitor.py --consultar --ano 2026 --controle caminho\controle_convencoes_AL.xlsx
```

Use `--ano 2026` para a consulta anual; sem `--ano`, a linha de comando mantém a consulta dos últimos sete dias. Sem `--controle`, cria um modelo novo. Com várias abas, use `--aba "Nome da aba"`. `--saida` seleciona a raiz das pastas de execução; cada execução cria uma pasta nova dentro dela.

A versão assistida foi preservada como alternativa em **`GUIA_ASSISTIDO.md`**, com o comando `--manifesto`. Ela não é o fluxo principal. `diagnosticar_mediador.py` continua disponível para investigação técnica. O diagnóstico da rede e os detalhes da fonte estão em `DIAGNOSTICO_MEDIADOR.md`.

## Validação do ajuste para todos os municípios

O HTML e os scripts oficiais confirmaram controles distintos para adicionar a UF, selecionar todos os municípios disponíveis e selecionar apenas os municípios da inicial exibida. O seletor de municípios foi aberto na fonte oficial e confirmou UF AL. O teste completo do botão Todos disponíveis e da pesquisa municipal foi interrompido; a presença de **AL000030/2026** ainda não foi confirmada na consulta corrigida. Os 37 testes locais validam o fluxo, a união das quatro pesquisas sem duplicação e documentos fictícios municipais. A validação real anterior dos 24 documentos corresponde ao filtro antigo por UF e não comprova completude da busca ampliada. No Windows, atualize `consulta_online.py`, execute Ano de 2026 e confira esse registro no retorno completo e as pendências no log.

## Interface visual

A janela usa a paleta aproximada da marca enviada: verde-petróleo, cinza, branco e fundo claro. O cabeçalho lê a logo de `assets/cercont.png` localmente; enquanto esse arquivo não estiver presente, exibe o nome Cercont em texto. Os filtros ficam em painel branco e os resultados têm rolagem. Pode ser redimensionada para ampliar a leitura. Não há dependências novas. Para atualizar o visual em uma instalação existente, feche o monitor e substitua somente `interface.py` pelo arquivo atualizado do repositório; abra novamente `abrir_monitor.bat`. Os 37 testes existentes passaram após a mudança. O ambiente de desenvolvimento não dispõe de tela gráfica; a aparência final, incluindo a escala de fontes do Windows, precisa ser conferida no computador do usuário.

A logo original ainda precisa ser recebida como arquivo PNG para inclusão no projeto. Ela não foi recriada. Para atualizar as cores, substitua `interface.py`; para exibir a logo, mantenha também a pasta `assets` com `cercont.png` ao lado desse arquivo. O carregamento da imagem não exige dependências novas ou acesso à internet.

## Consultar somente ontem

No campo **Período de registro**, selecione **Ontem** e clique em **Consultar novidades**. O período inclui apenas a data anterior à data atual no fuso `America/Maceio`. Não é uma janela móvel de 24 horas. A seleção usa a data de registro, preserva as quatro pesquisas territoriais, exclui ACTs e mantém o controle sem duplicação. O resumo informa a mesma data inicial e final. Por exemplo, em 12/10/2026, consulta somente 11/10/2026. A escolha é salva localmente.

Para atualizar, substitua `interface.py`, `consulta_online.py` e `monitor.py` na instalação existente. Não precisa reinstalar componentes. A linha de comando também aceita `monitor.py --consultar --ontem`. `--ontem` e `--ano` não podem ser usados juntos. Os 42 testes locais passaram; o novo filtro não foi validado em uma consulta real do portal nesta alteração.

## Painel inicial reformulado

A interface mantém Tkinter e a execução em segundo plano. O cabeçalho e o menu lateral usam verde institucional; a logo original é carregada de `assets/cercont.png` em um painel branco para preservar suas cores. O arquivo da logo não está incluído no repositório: sem ele, a janela avisa **Logo local não encontrada**, sem recriar a marca.

O painel apresenta cartões de fonte, abrangência e controle, campos responsivos, botões de consulta e resultados e abas **Etapas da execução** e **Resultados e pendências**. O menu tem ações reais: **Início** volta ao topo, **Consultas** vai ao acompanhamento, **Configurações** vai aos campos já existentes e **Ajuda** explica o fluxo. Não foram criadas novas regras de consulta nem configurações de negócio. A página tem rolagem para manter as informações acessíveis em janelas pequenas. A altura inicial considera a resolução da tela.

A barra mostra o percentual de **registros examinados na pesquisa atual**, calculado como examinados / total oficial. Ela reinicia a cada uma das quatro pesquisas, não representa o percentual global nem o sucesso da consulta. Antes de receber o total, mostra **aguardando contagem oficial**, sem animação. Um documento rejeitado conta como examinado e continua sendo pendência; somente o relatório informa se a consulta ficou completa. As mensagens reais são exibidas com data e horário locais do computador. A aba de etapas mantém as mensagens da sessão ao finalizar e ao iniciar novas consultas; os relatórios e logs de auditoria continuam sendo salvos pelo coletor.

Para atualizar, feche o monitor e substitua **interface.py** e **consulta_online.py**. Preserve `assets/cercont.png`, a configuração local, `.venv` e todas as saídas. Abra **abrir_monitor.bat**, sem novos comandos ou dependências.

Foram executados **45 testes locais**, incluindo fluxo do botão, seleção de planilha, abertura dos resultados no Windows simulada, filtro Ontem, estados de erro, mensagens com horário, contagem real e ausência de duplicação. Compilação e verificação do diff passaram. O ambiente não possui tela gráfica e não é Windows: a aparência final, o redimensionamento visual e o fluxo completo no Windows ainda precisam de validação no computador do usuário. Esta mudança não valida novamente o acesso ao Mediador nem a busca territorial ampliada.

## Tipografia e alinhamento

A interface usa **Garamond**, incluindo títulos, campos, menus e logs, com tamanhos ajustados para leitura. A fonte precisa estar instalada no Windows. Se estiver ausente, o programa informa essa condição e usa Times New Roman; não instala fontes nem altera a logo original. Os três cartões informativos compartilham a mesma altura, calculada pelo maior conteúdo, e colunas de largura igual. A altura é recalculada ao redimensionar para evitar cortar os textos. Os campos de período e aba usam colunas iguais, margens correspondentes e preenchimento vertical padronizado. Para atualizar, substitua somente `interface.py`. Os 45 testes passaram; a conferência visual final no Windows permanece necessária.

## Estilo da referência visual atual

A fonte Garamond foi substituída por **Segoe UI**, com Arial como alternativa quando necessário. A interface segue a referência com cabeçalho e menu verde-escuros, fundo cinza-claro, cartões informativos simétricos, faixas verdes discretas e ícones desenhados localmente em círculos. Mantém o arquivo original da logo e suas cores; não redesenha a marca. Os campos continuam com seus significados reais: a aba da planilha não virou um filtro de categoria. A barra de progresso continua baseada na pesquisa atual, sem animação fictícia.

Atualize somente `interface.py` e abra `abrir_monitor.bat`; não é necessário instalar fontes ou dependências adicionais no Windows. Os 45 testes e a compilação passaram. O ambiente sem tela gráfica não permite afirmar que a aparência final está visualmente validada no Windows ou que é uma reprodução exata da imagem.

## Tela pós-consulta: painel documental

Após a consulta, abre-se uma janela separada com identificação do instrumento, pesquisa nos documentos da execução, resumo executivo, alertas e seis seções detalhadas. A tela inicial, seus filtros, a abertura do Edge e o controle cumulativo permanecem disponíveis. **Nova consulta** retorna à tela inicial e não apaga execuções anteriores.

O botão **Ver painel** reabre os dados da execução atual. Se ainda não houver dados em memória, permite selecionar a pasta **resultado** de uma execução salva em `saidas/online_.../resultado`, sem fazer nova pesquisa na internet ou exigir PDFs preparados manualmente. A leitura histórica não troca o controle cumulativo selecionado. A pasta precisa manter os documentos e o manifesto interno original ao lado dos relatórios.

A pesquisa por categoria, sindicato, município, CNPJ ou registro filtra somente os documentos efetivamente obtidos nessa execução. Não é um novo filtro enviado ao Mediador. Para pesquisar novamente a fonte oficial, use **Nova consulta** e os filtros reais da tela inicial. Documentos já existentes no controle também podem aparecer no painel.

### Fontes, identificação e referências

`analise_resultados.py` lê os PDFs da consulta, sem modificar os arquivos, segmenta as cláusulas e registra número literal, título, texto completo, páginas físicas, arquivo, registro e SHA256. Identifica categoria e datas em formatos documentais reconhecidos. Se não houver confirmação suficiente, informa Não localizado ou Não confirmado. O papel dos sindicatos não é deduzido pela ordem das assinaturas. Entidades signatárias e CNPJs identificados aparecem para conferência; siglas ou formatos não reconhecidos geram pendência.

O documento nunca é marcado como vigente apenas porque foi localizado. Aditivos são relacionados somente por referência explícita ao registro ou processo da convenção principal e quando essa convenção também está disponível. O programa não consolida efeitos de aditivos, não confirma sucessão jurídica e não aplica regras automaticamente.

### Resumo e detalhes

O resumo executivo contém apenas **Reajuste salarial** e **Contribuições assistenciais**, com separação de empregados e patronal. A destinação ambígua é marcada como não confirmada. Contribuição sindical ou social não é automaticamente tratada como assistencial. Prévia e pontos de condições são recortes literais por palavras-chave, não interpretação jurídica ou afirmação de regra aplicável. A prévia pode estar incompleta; tabelas, faixas, proporcionalidades, oposições e exceções exigem a leitura integral pelo DP. A ausência de um item na classificação não comprova que a regra não existe.

As seis seções (salários, jornada, benefícios, obrigações do DP, atenção e comparativo) expandem e recolhem. Há filtro por assunto. **Ver cláusula** abre o texto integral segmentado, inclusive continuação em outras páginas, e sua referência. É possível abrir o PDF no navegador com a página indicada; o leitor PDF instalado pode ignorar a indicação, caso em que a referência textual continua disponível. O download original DOC/DOCX/PDF também tem acesso próprio quando identificado. PDFs de impressão permanecem identificados como tal nas referências.

### Comparativo, exportação e impressão

O comparativo permite selecionar um PDF anterior para leitura local. Só é realizado quando ambos são CCTs, o registro é anterior e categoria e CNPJs signatários são compatíveis. Títulos repetidos ou documentação insuficiente impedem comparação automática. O resultado é um **diff textual** com referências dos dois documentos, não uma análise jurídica nem confirmação de que o documento escolhido é o predecessor aplicável. Não gera percentuais comparados ou conclusões sem evidência. O PDF anterior não é modificado.

**Exportar resumo em PDF** gera o resumo de identificação com os dois assuntos, referências e limites. Não pode substituir os documentos de origem, o PDF anterior selecionado ou uma planilha. Não usa serviços externos ou dependências novas. O exportador usa fonte padrão PDF com caracteres WinAnsi; caracteres não suportados interrompem a exportação em vez de serem substituídos silenciosamente. **Imprimir resumo**, no Windows, exporta e solicita a impressão ao aplicativo PDF associado. O aplicativo pode não oferecer essa ação; nesse caso, o erro é informado e o PDF exportado continua disponível.

### Atualizar e verificar

Na instalação existente, feche o programa e copie os arquivos novos **analise_resultados.py** e **painel_resultados.py**, além de substituir **interface.py**. Preserve a logo local, a configuração, `.venv`, planilhas e pastas de resultados. Abra **abrir_monitor.bat**; não há nova preparação por CMD ou dependência adicional.

Para verificar no Windows: abra **Ver painel**, selecione `resultado` de uma consulta salva, pesquise um registro, escolha o documento, expanda uma seção e abra sua cláusula e o PDF. Exporte o resumo para um arquivo novo. Confira os trechos e páginas com o PDF original. Teste **Nova consulta** e observe que o histórico e a planilha selecionada permanecem. Se não houver documentos disponíveis por bloqueio ou erro, o painel mostrará as pendências, sem simular resultados.

### Validação efetivamente realizada

Foram executados **57 testes locais**, incluindo metadados, contribuições não confundidas com outros tipos, destinação ambígua, pesquisa por CNPJ/município, limites da comparação, referências de cláusulas que continuam em outra página, expansão/recolhimento, acesso ao PDF com página e proteção de fontes e planilhas durante exportação. Os cliques de navegação e abertura foram testados com controles simulados, sem tela gráfica.

Foi feita validação **offline com os 24 documentos oficiais já obtidos** na execução `online_20261009_042138_f937a507`: leitura, pesquisa e exportação. Na AL000242/2026 foram conferidas vigência documental de 01/01/2026 a 31/12/2027, cláusula TERCEIRA de reajuste (página 1, 4,11%) e cláusula TRIGÉSIMA NONA de taxa assistencial laboral (página 13). O PDF de resumo foi exportado e relido; hashes de todos os arquivos da execução original permaneceram iguais.

Não houve nova consulta ao Mediador nesta alteração. O ambiente não possui tela gráfica e não é Windows; aparência, seleção visual, abertura pelo leitor PDF e impressão real precisam ser verificadas no computador do usuário. A leitura dos documentos anteriores não comprova a completude da busca ampliada por municípios nem resolve bloqueios HTTP 403.

## Abertura sem console durante o uso

No Windows, `preparar_monitor.py` abre a interface pelo `pythonw.exe` em processo independente. O CMD fica visível apenas durante a verificação ou preparação inicial e fecha ao iniciar o monitor. Não feche essa janela enquanto as dependências estiverem sendo instaladas. Se a preparação falhar, ela permanece aberta com a mensagem de erro. Erros do processo gráfico são registrados em um arquivo novo `saidas/inicializacao_DATA_HORA_ID.log`; as consultas mantêm seus logs próprios.

Para atualizar, substitua somente **preparar_monitor.py** e continue abrindo **abrir_monitor.bat**. Os 59 testes passaram, incluindo abertura sem aguardar a interface e erro explícito quando pythonw não está disponível. O comportamento visual do console ainda precisa ser conferido no Windows real.

## Ordem dos resultados no acompanhamento

A aba **Resultados e pendências** apresenta os instrumentos por data de registro, do mais antigo ao mais recente, tanto no bloco de inclusões quanto no retorno completo. Títulos, totais e pendências permanecem nas suas posições. A aba de etapas mantém a ordem real da execução. A ordenação é apenas visual e não reorganiza as linhas da planilha de controle. Atualize somente `interface.py`. Os 60 testes passaram, incluindo datas de meses e anos diferentes.

## Reabrir o painel depois de fechar o programa

A última consulta passa a ser guardada na configuração local. Ao clicar em **Ver painel**, o programa procura essa consulta; para instalações anteriores, também reconhece o resultado pela planilha de controle selecionada e, como alternativa, pela execução mais recente em `saidas`. Se não encontrar, permite selecionar `saidas`, a pasta `online_DATA_HORA_ID` ou a subpasta `resultado`. Os três caminhos são normalizados antes de ler o manifesto e os PDFs. A reabertura não troca a planilha de controle nem executa nova consulta na internet.

Mantenha a pasta da execução completa, com `coleta_automatica.json`, `documentos` e `resultado`. Nenhuma consulta ou resumo é inventado quando esses arquivos estiverem indisponíveis. Para atualizar, substitua **interface.py** e **analise_resultados.py**, preservando a configuração e todas as saídas. Foram executados **62 testes**, incluindo reabertura e recuperação dos resumos pelos três caminhos. Também foi validada offline a recuperação dos 24 documentos oficiais anteriores e do reajuste de 4,11% da AL000242/2026 pelos três caminhos. A conferência gráfica no Windows permanece necessária.
