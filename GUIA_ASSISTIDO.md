# Alternativa assistida — Monitor de Convenções e Aditivos

Esta primeira versão funciona **manualmente, em modo assistido**. Lê PDFs fornecidos pelo usuário e acrescenta instrumentos novos em uma **nova cópia** do controle. Não possui agendamento, envio de mensagens nem ligação com folha de pagamento.

## Fonte oficial

O domínio atualizado é `https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo`. A investigação atual e a consulta online estão documentadas em `DIAGNOSTICO_MEDIADOR.md` e `GUIA_MONITOR.md`.

Este guia descreve somente o modo assistido, com PDFs fornecidos pelo usuário. O parâmetro `--consultar` agora inicia a coleta online; para usar a alternativa assistida, informe `--manifesto` como nos exemplos abaixo.

## Preparação no Windows

Use Python 3.11 ou 3.12 instalado com o comando `py` disponível. Abra o Prompt de Comando na pasta deste projeto:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

As dependências são `openpyxl` (planilhas) e `pypdf` (leitura de PDF), com versões fixadas. Os testes usam a biblioteca padrão do Python, sem instalar pytest. A instalação acessa o repositório de pacotes; o processamento assistido é local e não envia PDFs ou planilhas para terceiros.

## Primeiro teste, exclusivamente fictício

```bat
.venv\Scripts\python.exe exemplos\criar_demo.py entrada\demo
.venv\Scripts\python.exe monitor.py --manifesto entrada\demo\resultados.json --hoje 2026-10-08
```

O gerador exige uma pasta nova e não sobrescreve arquivos. A data fixa faz o documento fictício entrar na janela de teste. O PDF e a URL da demonstração não são documentos nem resultados oficiais. Não misture esta planilha com o controle da Cercont.

O programa informa a pasta criada em `saidas`. Nela haverá:

- `controle_convencoes_AL.xlsx`: modelo preenchido com uma linha fictícia;
- `resumo_convencoes_AL.txt`: período, novos registros e estado do processamento;
- `log_convencoes_AL.txt`: inclusões, duplicatas, exclusões e pendências.

Para testar repetição, execute novamente usando a planilha gerada como `--controle`. O número de linhas deve permanecer igual. Os testes automatizados verificam também o arquivo original byte a byte, as fórmulas existentes e documentos de acordo coletivo excluídos.

## Consulta manual no Mediador

1. Acesse o serviço oficial pelo navegador e abra a consulta pública. Se os endereços mudarem, localize o serviço pelo portal oficial do Ministério do Trabalho e Emprego.
2. Pesquise **Convenção Coletiva de Trabalho** e **Termo Aditivo de Convenção Coletiva**. Não selecione Acordo Coletivo nem Aditivo de Acordo.
3. Use **data de registro**, não vigência ou data de solicitação. A janela são sete datas de calendário inclusivas: hoje e os seis dias anteriores. Por exemplo, de 02/10/2026 até 08/10/2026. O padrão do programa usa a data local do computador Windows.
4. Filtre pela **abrangência territorial em Alagoas** se a interface oferecer esse filtro. A UF do registro ou a sede do sindicato não comprovam a abrangência. Se só houver filtro por UF de registro, ele não garante localizar todos os documentos aplicáveis a Alagoas: confira resultados mais amplos e registre a limitação.
5. Examine todas as páginas. Confira a cláusula de abrangência de cada documento; convenções que incluam Alagoas e outros estados também podem ser pertinentes.
6. Abra cada documento original e salve o PDF completo, sem alterar seu conteúdo. Se houver impressão para PDF oferecida pelo navegador, preserve o documento integral. Copie o link original oficial correspondente.
7. CAPTCHA deve ser resolvido manualmente no navegador, quando permitido pelo serviço. Se um documento ou a consulta continuar indisponível, registre a pendência. Não declare consulta completa se não conseguiu examinar todo o resultado.

O programa não comprova autenticidade dos PDFs fornecidos, nem a completude dessa busca. A conferência de origem e a aplicação da convenção aos clientes são responsabilidade do Departamento Pessoal.

## Informar os resultados

Crie uma pasta `entrada\consulta` e coloque nela os PDFs e um arquivo `resultados.json` em UTF-8. Este é o formato; substitua os nomes e links por resultados reais da consulta manual:

```json
{
  "consulta_completa": false,
  "instrumentos": [
    {
      "arquivo": "documento_original.pdf",
      "registro": "AL000001/2026",
      "fonte": "https://www3.mte.gov.br/sistemas/mediador/LINK-ORIGINAL"
    },
    {"status": "captcha"},
    {"status": "bloqueio"},
    {"status": "documento_indisponivel"}
  ]
}
```

O exemplo não contém um link válido de instrumento. `consulta_completa` só deve ser `true` depois da conferência manual de todas as páginas e documentos. Uma lista vazia deve refletir a busca realizada, nunca um bloqueio. O campo `registro` é opcional e serve apenas para conferir se o resultado corresponde ao PDF; ele não substitui o número lido no documento. Nenhum campo de tipo, data ou abrangência é aceito do manifesto: esses campos vêm do PDF.

Os PDFs devem ficar dentro da pasta do manifesto ou suas subpastas. URLs de fonte devem ser HTTPS de `mediador.trabalho.gov.br`, `www3.mte.gov.br`, `www.mte.gov.br` ou `mediador.mte.gov.br`. A URL é registrada, mas não acessada nem validada remotamente no modo assistido. Outra origem oficial exigirá revisão explícita da lista de domínios, após confirmação.

## Executar com o controle existente

Feche o Excel. Mantenha uma cópia de segurança. O arquivo fornecido em `--controle` é somente lido:

```bat
.venv\Scripts\python.exe monitor.py --manifesto entrada\consulta\resultados.json --controle entrada\controle_convencoes_AL.xlsx
```

Ou use o facilitador:

```bat
executar_manual.bat --manifesto entrada\consulta\resultados.json --controle entrada\controle_convencoes_AL.xlsx
```

Para várias abas, acrescente `--aba "Nome da aba"`. Opcionalmente informe `--saida saidas\revisao_01`, que precisa ser uma pasta **ainda inexistente**. Cada execução padrão cria uma pasta própria; nunca sobrescreve resultados anteriores nem o controle de entrada.

### Formato da planilha

Na primeira linha da aba escolhida, precisam existir exatamente uma vez estes cabeçalhos, em qualquer ordem:

`Registro`, `Data de registro`, `Tipo`, `Abrangência territorial`, `Documento`, `Fonte`, `SHA256`.

Outras colunas são mantidas e ficam vazias nas linhas novas. Registros existentes devem ter formato como `AL000001/2026`; espaços e letras minúsculas são normalizados apenas para comparação. Células de registro inválidas ou fórmulas nessa coluna impedem processamento para evitar duplicação.

**Nenhuma planilha oficial foi fornecida ou examinada nesta implementação.** Se seus cabeçalhos forem diferentes, o programa interrompe sem adaptar o original. É preciso mapear seu formato em uma etapa específica, usando uma cópia autorizada. Não renomeie colunas oficiais apenas para fazer o programa passar. Sem `--controle`, o programa cria um modelo novo.

O SHA256 identifica o arquivo PDF processado e ajuda a conferir sua integridade; não atesta autenticidade. `Documento` é o caminho relativo à pasta do manifesto, que deve ser guardada junto dos resultados para rastreabilidade.

O `openpyxl` preserva valores e fórmulas usuais na cópia, mas não garante todos os recursos avançados do Excel, como desenhos, conexões ou objetos incorporados. Macros `.xlsm` não são aceitas. Confira a cópia antes de adotá-la; a planilha de origem não é sobrescrita. Tabelas e gráficos existentes não têm sua faixa automaticamente ampliada.

## Conferência e limitações

Execute a suíte de testes automatizados com o comando acima. Também confira manualmente a cópia: linhas antigas, registros únicos, tipo, data de registro e abrangência, comparando cada nova linha com seu PDF original. Faça o teste de repetição antes de incorporar resultados ao trabalho do DP.

Código de saída `0`: processamento local concluído sem pendências detectadas. Código `2`: há pendência ou a consulta não foi concluída; consulte os dois relatórios. Instrumentos fora da janela e acordos são exclusões esperadas, registradas no log. PDFs ausentes, ilegíveis, protegidos, com campos ambíguos, formato diferente ou abrangência não confirmada são pendências. Instrumentos válidos podem ser gravados na cópia mesmo que outros itens tenham pendências; o resumo deixa isso explícito. Uma falha geral de leitura/escrita não confirma a criação da planilha.

A extração é conservadora e depende de rótulos de registro/data e de uma cláusula de abrangência legíveis. PDFs digitalizados precisam de OCR e revisão em etapa futura; este programa não realiza OCR. PDF acima de 30 MB é recusado. A extração foi posteriormente verificada com o PDF de impressão da CCT oficial AL000242/2026; outros formatos podem exigir ajustes. O código foi executado em Linux com Python 3.12; os comandos para Windows estão documentados, mas não houve execução em uma máquina Windows nesta entrega.

**Não interpretar zero inclusões como prova de que não existem novidades.** A consulta online é o fluxo principal descrito em GUIA_MONITOR.md; este guia preserva a alternativa assistida. Não há agendamento automático.
