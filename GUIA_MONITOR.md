# Monitor Diário de Convenções e Aditivos — Alagoas

O fluxo principal é online: abra a interface e clique em **Consultar novidades**. Não é necessário anexar PDFs, baixar documentos manualmente ou preparar `resultados.json`. A primeira preparação instala as bibliotecas e o navegador; depois, a consulta é manual por clique. Não há agendamento.

## Preparar e abrir no Windows

Instale Python 3.11 ou 3.12 pelo distribuidor oficial, com Tcl/Tk e o comando `py` disponíveis. Na pasta do projeto, abra o Prompt de Comando:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Depois dê dois cliques em **`abrir_monitor.bat`**. Também é possível abrir com:

```bat
.venv\Scripts\python.exe interface.py
```

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
