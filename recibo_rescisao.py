"""Recibo local de valores informados; não calcula direitos rescisórios."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re


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
    emitir_quitacao=dados.get('emitir_quitacao') is True
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
    for campo in ('nascimento','aviso'):
        if d.get(campo):data_valida(d[campo])
    data_pagamento=data_valida(d.get('data_pagamento',''),emitir_quitacao)
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
            'liquido':proventos-descontos,'data':dia,'admissao':admissao,'desligamento':desligamento,
            'emitir_quitacao':emitir_quitacao,'data_pagamento':data_pagamento}


def texto_recibo(recibo):
    from modelo_rescisao import folhas
    linhas=[]
    for aba,valores,_ in folhas(recibo):
        linhas.extend(['',aba['nome'],''])
        for r in range(aba['linhas']):
            itens=[str(valores.get((r,c),'')) for c in range(6) if str(valores.get((r,c),''))]
            if itens:linhas.append(' | '.join(itens))
    if not recibo.get('emitir_quitacao'):
        linhas.append('Termo de quitação não incluído: pagamento não confirmado.')
    return '\n'.join(linhas)


def exportar_recibo(recibo,destino):
    from modelo_rescisao import exportar_pdf
    return exportar_pdf(recibo,destino)
