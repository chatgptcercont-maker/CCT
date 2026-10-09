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

Na janela:

1. Se já houver controle, selecione a planilha `.xlsx` uma vez. Se houver várias abas, informe a aba. Sem controle, será criado um modelo novo.
2. Clique em **Consultar novidades** e aguarde. A consulta roda em segundo plano, sem travar a interface.
3. Leia o resumo e clique em **Abrir resultados** para acessar os arquivos. Confira pendências antes de usar o resultado no DP.

O programa guarda a seleção localmente. Após cada execução com uma planilha de saída válida, a próxima consulta usa essa cópia cumulativa como controle, evitando perda de registros e duplicações. O arquivo original selecionado nunca é sobrescrito. Não deixe o Excel aberto sobre a planilha usada para leitura.

## O que é consultado

Fonte: `https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo`.

O navegador preenche os filtros e aciona o botão **Pesquisar** do próprio portal. São feitas duas pesquisas: Convenção Coletiva e Termo Aditivo de Convenção Coletiva. Acordos e aditivos de acordos não são selecionados e são recusados também na leitura dos documentos.

A janela são sete datas inclusivas: hoje e seis dias anteriores, considerando a **data de registro** e o fuso `America/Maceio`. Por exemplo, uma consulta feita em 08/10/2026 cobre 02/10/2026 a 08/10/2026. A data é calculada a cada clique; o modo online não permite substituir a data por uma data de teste.

A seleção territorial usa **Alagoas**, separada da UF de registro, e contempla os tipos de abrangência municipal, intermunicipal, estadual, interestadual e nacional. A presença de Alagoas é conferida novamente na cláusula do documento. Um registro de outra UF ou da SRT pode ser aceito se a cláusula confirmar abrangência em AL. A aplicação da convenção a cada cliente precisa de revisão do Departamento Pessoal.

A coleta acompanha a contagem de instrumentos e páginas informada pelo portal e tenta avançar pelos controles nativos de paginação. Controles desconhecidos, mudanças de contagem, duplicação de páginas ou mais de 200 páginas tornam a consulta incompleta, sem presumir ausência de registros.

## Documentos e relatórios

Cada execução cria uma pasta `saidas\online_DATA_HORA_IDENTIFICADOR`:

- `documentos`: arquivos oficiais obtidos pelo botão **Download** e PDFs de impressão, quando necessários;
- `coleta_automatica.json`: registro interno gerado pelo programa para auditoria; o usuário não prepara esse arquivo;
- `resultado\controle_convencoes_AL.xlsx`: nova cópia com registros novos acrescentados;
- `resultado\resumo_convencoes_AL.txt`: período, registros acrescentados e pendências;
- `resultado\log_convencoes_AL.txt`: operações, formatos dos documentos, hashes e erros de acesso.

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

No teste real, a pesquisa de aditivos retornou **HTTP 500 com a mensagem oficial “Nenhum registro encontrado.”**. O programa preserva tanto o erro HTTP quanto essa mensagem. Por cautela, não converte essa resposta de erro em uma pesquisa concluída com zero resultados. Outros HTTP 500 também permanecem como falhas, independentemente do conteúdo.

A interface distingue consulta concluída de consulta com pendências. Na linha de comando, código de saída `0` significa processamento concluído sem pendências; `2` significa pendência. Zero inclusões também pode significar que todos os registros já estavam no controle.

## Testar e conferir

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Foram executados **22 testes com dados fictícios**, abrangendo filtros e datas, rejeição de ACTs, número de registro versus número de solicitação, registros da SRT, preservação do controle, repetição sem duplicatas, classificação de falhas, retorno HTTP 500 e conexão do botão com a coleta online. Os testes fictícios não comprovam acesso à fonte oficial.

Também foi executado um teste real pela internet: CCT **AL000242/2026**, registrada em **07/10/2026**, com abrangência confirmada em AL. O programa baixou o original `.doc`, acessou a visualização oficial, gerou um PDF de impressão e acrescentou uma linha à planilha de teste. Uma segunda execução online com essa planilha acrescentou **zero linhas**, sem duplicar o registro. Na pesquisa de aditivos, o erro HTTP 500 foi registrado nas duas execuções.

Confira cada nova linha com os documentos e o link oficial, além das linhas antigas. O caminho positivo de aditivos e a paginação com mais de uma página ainda não foram validados com documentos reais; a consulta real retornou uma única página de CCTs. PDFs digitalizados sem texto ou protegidos geram pendência; não há OCR.

O backend foi executado em Linux com Chromium, HTTPS verificado e dados oficiais. O vínculo do botão com o backend foi testado, mas a aparência e a execução da janela em uma máquina Windows ainda não foram testadas. A consulta completa dos dois tipos não está validada devido à resposta de erro do portal para aditivos.

## Alternativas

A mesma consulta online pode ser executada sem a janela:

```bat
.venv\Scripts\python.exe monitor.py --consultar --controle caminho\controle_convencoes_AL.xlsx
```

Sem `--controle`, cria um modelo novo. Com várias abas, use `--aba "Nome da aba"`. `--saida` seleciona a raiz das pastas de execução; cada execução cria uma pasta nova dentro dela.

A versão assistida foi preservada como alternativa em **`GUIA_ASSISTIDO.md`**, com o comando `--manifesto`. Ela não é o fluxo principal. `diagnosticar_mediador.py` continua disponível para investigação técnica. O diagnóstico da rede e os detalhes da fonte estão em `DIAGNOSTICO_MEDIADOR.md`.
