"""Recibo local de valores informados; não calcula direitos rescisórios."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import textwrap
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def valor_monetario(texto):
    texto=str(texto).strip().removeprefix('R$').strip()
    if not re.fullmatch(r'(?:\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[,.]\d{1,2})?)',texto):
        raise ValueError('Informe um valor positivo em reais, por exemplo 1.250,50.')
    numero=texto.replace('.','').replace(',','.') if ',' in texto or re.fullmatch(r'\d{1,3}(?:\.\d{3})+',texto) else texto
    try:valor=Decimal(numero).quantize(Decimal('0.01'))
    except InvalidOperation as exc:raise ValueError('Valor monetário inválido') from exc
    if valor>Decimal('999999999.99'):raise ValueError('Valor acima do limite suportado')
    return valor


def reais(valor):
    return 'R$ '+f'{valor:,.2f}'.replace(',','X').replace('.',',').replace('X','.')


def data_valida(texto,obrigatoria=False):
    texto=str(texto).strip()
    if not texto and not obrigatoria:return None
    try:return datetime.strptime(texto,'%d/%m/%Y').date()
    except ValueError as exc:raise ValueError('Informe a data em DD/MM/AAAA.') from exc


def preparar_recibo(dados,itens):
    d={k:str(v).strip() for k,v in dados.items()}
    for campo,nome in [('empresa','Empresa ou contratante'),('trabalhador','Trabalhador'),('local','Local')]:
        if not d.get(campo):raise ValueError(nome+' deve ser informado.')
    for campo,tamanho in [('cpf',11),('documento_empresa',None)]:
        informado=d.get(campo,'')
        if informado and not re.fullmatch(r'[\d./\-\s]+',informado):
            raise ValueError('Informe CPF/CNPJ com números e os separadores usuais.')
        valor=re.sub(r'\D','',informado)
        if informado and not valor:raise ValueError('CPF/CNPJ informado está vazio ou inválido.')
        if valor and (len(valor)!=tamanho if tamanho else len(valor) not in (11,14)):
            raise ValueError('Confira o CPF/CNPJ informado. Use 11 ou 14 dígitos conforme o documento.')
    dia=data_valida(d.get('data_recibo',''),True)
    admissao=data_valida(d.get('admissao',''));desligamento=data_valida(d.get('desligamento',''))
    if admissao and desligamento and admissao>desligamento:raise ValueError('Admissão não pode ser posterior ao desligamento.')
    linhas=[];proventos=Decimal('0.00');descontos=Decimal('0.00')
    for item in itens:
        descricao=str(item.get('descricao','')).strip()
        if not descricao:raise ValueError('Todas as verbas precisam de descrição.')
        tipo=item.get('tipo')
        if tipo not in ('Provento','Desconto'):raise ValueError('Escolha Provento ou Desconto.')
        valor=valor_monetario(item.get('valor',''))
        if valor<=0:raise ValueError('As verbas devem ter valor maior que zero.')
        linhas.append({'descricao':descricao,'tipo':tipo,'valor':valor})
        if tipo=='Provento':proventos+=valor
        else:descontos+=valor
    if not linhas:raise ValueError('Adicione ao menos uma verba.')
    if descontos>proventos:raise ValueError('Os descontos superam os proventos. Confira os valores antes de emitir.')
    return {'dados':d,'itens':linhas,'proventos':proventos,'descontos':descontos,
            'liquido':proventos-descontos,'data':dia,'admissao':admissao,'desligamento':desligamento}


def texto_recibo(recibo):
    d=recibo['dados']
    linhas=['RECIBO DE RESCISÃO AVULSA','',
        'Empresa/contratante: '+d['empresa'],'CPF/CNPJ: '+(d.get('documento_empresa') or 'Não informado'),
        'Trabalhador: '+d['trabalhador'],'CPF: '+(d.get('cpf') or 'Não informado'),
        'Admissão: '+(d.get('admissao') or 'Não informada'),'Desligamento: '+(d.get('desligamento') or 'Não informado'),
        '','VALORES DISCRIMINADOS']
    for i,item in enumerate(recibo['itens'],1):
        linhas.append(f"{i}. {item['tipo']} — {item['descricao']}: {reais(item['valor'])}")
    linhas+=['','Total de proventos: '+reais(recibo['proventos']),'Total de descontos: '+reais(recibo['descontos']),
        'Valor líquido: '+reais(recibo['liquido']),'',
        'Os valores acima foram informados manualmente pelo responsável pela elaboração.']
    if d.get('observacoes'):linhas+=['','Observações: '+d['observacoes']]
    linhas+=['',d['local']+', '+recibo['data'].strftime('%d/%m/%Y'),'',
        'Recebimento: a assinatura abaixo confirma exclusivamente o recebimento dos valores discriminados neste documento.',
        '', '________________________________________________________',
        'Assinatura do trabalhador/recebedor','',
        '________________________________________________________','Assinatura do responsável pelo pagamento','',
        'Documento sem assinatura não comprova pagamento. Não é TRCT e não declara quitação geral do contrato.']
    return '\n'.join(linhas)


def exportar_recibo(recibo,destino):
    destino=Path(destino)
    if destino.suffix.lower()!='.pdf':raise ValueError('Escolha um arquivo com extensão .pdf.')
    if destino.exists():raise ValueError('O arquivo já existe. Escolha outro nome para preservar o anterior.')
    linhas=[]
    for linha in texto_recibo(recibo).splitlines():linhas.extend(textwrap.wrap(linha,86) or [''])
    writer=PdfWriter()
    for inicio in range(0,len(linhas),53):
        page=writer.add_blank_page(width=595,height=842)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica'),NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        comandos=[b'BT /F1 10 Tf 14 TL 40 800 Td']
        for linha in linhas[inicio:inicio+53]:
            try:raw=linha.encode('cp1252')
            except UnicodeEncodeError as exc:raise ValueError('O texto contém caracteres não suportados pelo PDF. Confira a prévia.') from exc
            raw=raw.replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')
            comandos.append(b'('+raw+b') Tj T*')
        comandos.append(b'ET');stream=DecodedStreamObject();stream.set_data(b'\n'.join(comandos))
        page[NameObject('/Contents')]=writer._add_object(stream)
    with destino.open('xb') as arquivo:writer.write(arquivo)
    return destino
