# Diagnóstico técnico do acesso ao Mediador

## Resultado final e limites

Foi implementada uma interface com **Consultar novidades** ligada a um coletor online com Playwright. O usuário não precisa fornecer PDFs, baixar documentos ou preparar `resultados.json`. A versão assistida foi preservada.

O fluxo de CCT foi testado com dados oficiais: **AL000242/2026**, solicitação **MR063147/2026**, registro em **07/10/2026**, abrangência territorial confirmada na cláusula como AL. A execução online baixou o original `.doc`, abriu a visualização protegida, produziu um PDF de impressão de 16 páginas, extraiu os campos e acrescentou uma linha à planilha de teste. A segunda execução usando essa planilha não duplicou o registro.

A pesquisa de aditivos retornou **HTTP 500**, cujo JSON oficial contém `message: "Nenhum registro encontrado."`. O JavaScript do portal trata essa resposta como erro e mostra sua mensagem. O programa registra o status e a mensagem literal; por cautela, não transforma esse erro em uma consulta completa com zero resultados. A causa observada é a aplicação do Mediador representando ausência de registros como exceção, não o 403 inicial do proxy.

Portanto: o caminho positivo de CCT foi validado na fonte real, mas **a consulta completa dos dois tipos permanece com pendência do portal**. Não houve documento real positivo de aditivo nem resposta com várias páginas na janela consultada. O programa possui controles de paginação, mas esse caminho ainda precisa de validação real quando houver vários resultados.

## Origem do 403 e solução de acesso

Inicialmente Python informou `Tunnel connection failed: 403 Forbidden`, e Chromium informou `net::ERR_TUNNEL_CONNECTION_FAILED`. O proxy recusava o túnel CONNECT antes de entregar a página: os domínios não estavam na lista de rede permitida. Não havia evidência de recusa pelo Mediador.

Foi salvo um rascunho acrescentando `mediador.trabalho.gov.br`, `www3.mte.gov.br`, `www.gov.br`, `www.google.com` e `www.gstatic.com`, preservando os presets. Os dois últimos são referenciados pelo reCAPTCHA original. O salvamento é confirmado, mas não comprova publicação do ambiente. Após a mudança, Python recebeu HTTP 200.

O Chromium então apresentou `net::ERR_CERT_AUTHORITY_INVALID`, referente à cadeia do proxy. A cadeia foi validada com OpenSSL e a CA pública fornecida pelo próprio ambiente; não foi lida nenhuma chave privada. A revisão automática inicialmente rejeitou a alteração no armazenamento efetivo de confiança. O usuário autorizou explicitamente a adição dessa CA. Após a autorização e os ajustes de confiança, o navegador executou a consulta real.

Não foram usados `ignore_https_errors`, `--ignore-certificate-errors`, TLS desativado, proxies externos, ocultação de automação nem soluções de CAPTCHA. A aplicação distribuída não altera certificados do Windows e não instala a CA da nuvem na máquina do usuário.

## Fonte oficial e serviços disponíveis

Respostas reais recebidas:

| Fonte | Resultado |
| --- | --- |
| `https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo` | HTTP 200; interface Mediador 3.3.1 |
| `https://www.gov.br/pt-br/servicos/consultar-instrumento-coletivo-de-trabalho` | HTTP 200; consulta disponível a qualquer pessoa mediante os filtros |
| `https://mediador.trabalho.gov.br/sistemas/mediador/Content/docs/CARTILHA_DO_MEDIADOR_v20.pdf` | HTTP 200; manual oficial, 45 páginas |
| `https://mediador.trabalho.gov.br/robots.txt` | HTTP 404; ausência de política nesse endereço não é autorização geral |
| Manual no antigo domínio `www3.mte.gov.br` | HTTP 503; obtido no domínio atualizado |

O serviço oficial e a seção 4 do manual descrevem consultas avançada, básica e por filiação. Não foi encontrada nesses documentos uma API pública documentada para integração independente. O manual é documentação, não instrumento coletivo nem comprovação de pesquisa de registros.

## Formulários, filtros e sessão

A página inicial usa JavaScript/jQuery e elementos `div`, sem depender de um formulário HTML tradicional para os filtros. A seleção da abrangência é mantida pelo servidor em sessão. O resultado contém um formulário POST e uma grade.

| Campo | Identificador/valor oficial observado |
| --- | --- |
| Tipo | `#cboTPRequerimento` |
| CCT | `convencao` |
| Aditivo de CCT | `termoAditivoConvecao` — grafia do próprio portal |
| ACT/aditivo de ACT | opções distintas, não selecionadas pelo programa |
| Ativar período de registro | `#chkPeriodoRegistro` |
| Datas de registro | `#txtDTInicioRegistro`, `#txtDTFimRegistro` |
| UF de registro | `#cboUFRegistro`, mantida vazia |
| UF abrangida | `#cboUFAbrangenciaTerritorial`, selecionada como AL |
| Acrescentar UF à seleção | `#btnAdicionarUF` |
| Pesquisar | `#btnPesquisar` |
| Região dos resultados | `#divConsultaDetalhada` |

A UF de registro não comprova abrangência. O coletor usa todos os tipos de abrangência previstos pelo portal e confirma AL no documento original. Cada tipo de instrumento é consultado em um contexto separado de navegador, para evitar contaminação entre sessões/filtros.

A página usa reCAPTCHA v3: o botão chama `grecaptcha.execute` com ação `pesquisar`, e então executa a requisição com `recaptchaToken`. O coletor clica nesse botão e deixa o código original funcionar. Não lê, fabrica, reaproveita ou envia tokens por outros meios. CAPTCHA interativo, autenticação, bloqueio HTTP 401/403 e falha TLS interrompem a coleta, sem tentativa de contorno.

## Requisições e documentos

Endpoints observados no código oficial e/ou durante a navegação:

- `/sistemas/mediador/ConsultarInstColetivo/getPartAbrangenciaSelecionarUF`
- `/sistemas/mediador/ConsultarInstColetivo/getPartAbrangenciaAddUF`
- `/sistemas/mediador/ConsultarInstColetivo/getPartMunicipiosPelaUF`
- `/sistemas/mediador/ConsultarInstColetivo/getConsultaAvancada`
- `/sistemas/mediador/ConsultarInstColetivo/getConsultaAvancadaClausula`
- `/sistemas/mediador/ConsultarInstColetivo/GenerateSecurityToken`
- `/sistemas/mediador/Resumo/ResumoVisualizar`
- `/sistemas/mediador/Resumo/resumoVisualizarSalvarMsWordDoc`

Esses endpoints são internos à interface; não são apresentados como API documentada para uso independente. O programa não envia a pesquisa diretamente a eles sem a validação do portal.

A pesquisa envia os filtros, `pagina`, `qtdTotalRegistro` e o token original. O resultado real informou `Resultado: 1 Instrumento(s) Coletivo(s) Encontrado(s) - Página 1 de 1`. A grade é `#grdInstrumentos`, com linhas `tr[indice]` identificadas pelo número de solicitação. O coletor confere contagens e usa o controle numérico da próxima página no rodapé; controles desconhecidos ou totais inconsistentes geram pendência.

A visualização não é obtida ignorando a proteção do link: o código nativo gera um token de segurança por POST e abre o documento usando o fluxo original. O programa clica em **Visualizar Instrumento Coletivo**. O link estável do registro é guardado como fonte, mas tokens e cookies não são registrados.

No instrumento testado, **Download** forneceu `ICRegistrado2147444958.doc`, um HTML de exportação Word com 140.493 bytes. O coletor preservou o original e criou um PDF de impressão da visualização oficial. Esse PDF é identificado como cópia de impressão, não como PDF original do portal. A extração confirmou registro, data, tipo e abrangência no conteúdo recebido.

## Evidências e validação

As pastas locais de teste real são:

- `saidas/online_20261009_024130_7d9b9413`: inclusão de um instrumento real;
- `saidas/online_20261009_024502_9e8a2564`: repetição, zero instrumentos novos e registro do HTTP 500 com a mensagem oficial.

O período usado pelo coletor foi de **02/10/2026 a 08/10/2026**, sete datas inclusivas no fuso `America/Maceio`. A data é recalculada em cada execução, não fixada nesses valores no programa.

Os documentos e resultados locais estão ignorados pelo Git. Nenhuma planilha oficial foi fornecida ou alterada. Nenhum commit, push, publicação de aplicação, envio de mensagens ou agendamento foi realizado.

A suíte de testes com dados fictícios valida falhas, filtros, deduplicação, controle preservado, registros da SRT e ligação do botão ao backend. Esses testes complementam, mas não substituem, as requisições e os documentos reais descritos acima. A interface gráfica não foi executada em Windows; instruções de instalação e abertura estão em `GUIA_MONITOR.md`.

A ferramenta `diagnosticar_mediador.py` permanece disponível para inspeção técnica. Ela não é o fluxo principal. O guia do modo assistido é `GUIA_ASSISTIDO.md`.
