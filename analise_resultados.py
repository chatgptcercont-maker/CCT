"""Leitura documental conservadora para o painel; não interpreta obrigações."""
from datetime import date, datetime
import difflib
import hashlib
import json
from pathlib import Path
import re
import textwrap
from zoneinfo import ZoneInfo
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import monitor

ASSUNTOS = {
    'Salários e reajustes': r'SALARI|REAJUST|PISO|ABONO|RETROATIV|DIFERENCAS SALARIAIS',
    'Jornada e adicionais': r'JORNADA|ESCALA|HORA.EXTRA|NOTURNO|FERIADO|DOMINGO|BANCO DE HORAS|COMPENSACAO|ADICIONAL|INSALUBRIDADE',
    'Benefícios': r'ALIMENTACAO|REFEICAO|CESTA|TRANSPORTE|ASSISTENCIA|AUXILIO|BENEFICIO|ODONTO|SAUDE|MEDICA|HOSPITALAR',
    'Obrigações do DP': r'CONTRIBUI|ASSISTENCIAL|RECOLHIMENTO|MULTA|ESTABILIDADE|ATESTADO|AUSENCIA|FALTA|CTPS|PRAZO|PAGAMENTO|GUIAS|SINDIC|OBRIGAC',
}
CABECALHO = re.compile(r'^[ \t]*CL[ÁA]USULA\s+([^\n]+?)\s+[-–—]\s+([^\n]+)', re.M | re.I)
MESES = {nome:i+1 for i,nome in enumerate('janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro'.split())}


def data_documental(texto):
    n = monitor.normalizar(texto).lower().strip()
    try:
        if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', n):
            return datetime.strptime(n, '%d/%m/%Y').date().isoformat()
        m = re.fullmatch(r'(\d{1,2})[º°o]?\s+de\s+(\w+)\s+de\s+(\d{4})', n)
        if m:
            return date(int(m[3]),MESES[m[2]],int(m[1])).isoformat()
    except (ValueError, KeyError):
        pass
    return None


def ler_documento(caminho, fonte='', hoje=None):
    caminho = Path(caminho).resolve()
    if caminho.suffix.lower() != '.pdf' or caminho.stat().st_size > 30*1024*1024:
        raise ValueError('Formato ou tamanho de documento não suportado')
    pdf = PdfReader(caminho)
    if pdf.is_encrypted:
        raise ValueError('PDF protegido: leitura não confirmada')
    paginas = [p.extract_text() or '' for p in pdf.pages]
    texto = '\n'.join(paginas)
    if not texto.strip():
        raise ValueError('PDF sem texto extraível; não há OCR')
    hoje = hoje or datetime.now(ZoneInfo('America/Maceio')).date()
    dados = monitor.extrair(texto, hoje, date(1900,1,1))
    # Registra offsets para referenciar a página física do PDF lido.
    limites, offset = [], 0
    for pagina in paginas:
        limites.append(offset); offset += len(pagina)+1
    def pagina_de(posicao):
        return sum(l <= posicao for l in limites)
    matches = list(CABECALHO.finditer(texto))
    clausulas = []
    for i,m in enumerate(matches):
        fim = matches[i+1].start() if i+1<len(matches) else len(texto)
        corpo = texto[m.end():fim].strip()
        clausulas.append({'numero':m[1].strip(), 'titulo':m[2].strip(), 'texto':corpo,
            'pagina':pagina_de(m.start()), 'pagina_final':pagina_de(max(m.start(),fim-1)),
            'arquivo':caminho.name, 'registro':dados['Registro']})
    alertas = ['Classificação por palavras-chave; a leitura integral e a validação pelo DP são necessárias.',
               'Aditivos e instrumentos posteriores podem alterar as regras; a análise não confirma qual regra é a mais atual.']
    if not clausulas:
        alertas.append('Não foi possível segmentar as cláusulas com segurança; consulte o documento completo.')
    if any(not p.strip() for p in paginas):
        alertas.append('Há páginas sem texto extraível. O PDF pode conter imagens; confira o original.')
    abrangencia = next((c for c in clausulas if 'ABRANGENCIA' in monitor.normalizar(c['titulo'])), None)
    categoria = None
    if abrangencia:
        m = re.search(r'categoria\(s\)\s+(.+?)(?:,?\s+com abrang[eê]ncia territorial|\Z)', abrangencia['texto'], re.I|re.S)
        if m: categoria = re.sub(r'\s+',' ',m[1]).strip(' ,.')
    vigencia = next((c for c in clausulas if 'VIGENCIA' in monitor.normalizar(c['titulo'])), None)
    inicio = fim = database = None
    if vigencia:
        t = re.sub(r'\s+',' ',vigencia['texto'])
        m = re.search(r'per[ií]odo de (.+?) a (.+?)(?=\s+e a data|[.;]|$)',t,re.I)
        if m: inicio,fim = data_documental(m[1]),data_documental(m[2])
        m = re.search(r'data-base(?: da categoria)?(?: em|:| de)?\s+([^.;]+)',t,re.I)
        if m: database=m[1].strip()
    if not inicio or not fim: alertas.append('Datas de vigência não confirmadas na extração.')
    if not database: alertas.append('Data-base não localizada com segurança na cláusula de vigência.')
    if not categoria: alertas.append('Categoria não localizada com segurança na cláusula de abrangência.')
    header = texto[:matches[0].start()] if matches else texto[:3000]
    header = re.sub(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-)\s+(\d{2})',r'\1\2',header)
    partes = []
    for m in re.finditer(r'(?:^|\n)((?:SIND(?:ICATO)?\b|FEDERA[ÇC][ÃA]O|CONFEDERA[ÇC][ÃA]O|SECOVI\b)[^\n]*(?:\n(?!\s*CNPJ)[^\n]*){0,3}?)\s*,?\s*\n?CNPJ\s+n\.?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',header,re.I):
        nome = re.sub(r'\s+',' ',m[1]).strip(' ,')
        partes.append({'nome':nome,'cnpj':m[2]})
    # O papel não é deduzido pela ordem das entidades no cabeçalho.
    patronal=[p for p in partes if re.search(r'PATRONAL|SINDICATO (?:DAS|DOS) (?:EMPRESAS|INDUSTRIAS|INSTITUICOES|LOJISTAS)',monitor.normalizar(p['nome']))]
    profissional=[p for p in partes if re.search(r'SINDICATO (?:DAS|DOS|DE) (?:TRABALHADORES|EMPREGADOS)|PROFISSIONAL',monitor.normalizar(p['nome']))]
    if len(patronal)!=1:alertas.append('Sindicato patronal: papel não confirmado automaticamente; confira as entidades signatárias.')
    if len(profissional)!=1:alertas.append('Sindicato profissional: papel não confirmado automaticamente; confira as entidades signatárias.')
    principal = re.search(r'(?:N[ÚU]MERO DE REGISTRO (?:DA |DE )?(?:CONVEN[ÇC][ÃA]O COLETIVA PRINCIPAL|INSTRUMENTO PRINCIPAL)|REGISTRO (?:DA |DE )?CONVEN[ÇC][ÃA]O PRINCIPAL)\s*:?\s*('+monitor.REGEX_REGISTRO+')',texto,re.I)
    processo = re.search(r'N[ÚU]MERO DO PROCESSO\s*:\s*([\d./-]+)',header,re.I)
    processo_principal = re.search(r'N[ÚU]MERO DO PROCESSO DA CONVEN[ÇC][ÃA]O COLETIVA PRINCIPAL\s*:\s*([\d./-]+)',header,re.I)
    cnpjs = re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',header)
    if len(partes)!=len(set(cnpjs)):
        alertas.append('Identificação das entidades signatárias pode estar incompleta; confira o cabeçalho original.')
    return {**dados,'caminho':str(caminho),'fonte':fonte,'sha256':hashlib.sha256(caminho.read_bytes()).hexdigest(),
        'categoria':categoria,'vigencia_inicio':inicio,'vigencia_fim':fim,'data_base':database,
        'referencia_identificacao': {'vigencia':vigencia,'categoria':abrangencia},
        'patronal':patronal[0] if len(patronal)==1 else None,'profissional':profissional[0] if len(profissional)==1 else None,
        'partes':partes,'cnpjs':cnpjs,
        'processo':processo[1] if processo else None,'processo_principal':processo_principal[1] if processo_principal else None,
        'principal':principal[1] if principal else None,'clausulas':clausulas,'alertas':alertas,
        'situacao':'Não confirmada — verificar vigência, aditivos e instrumentos posteriores',
        'pagina_tipo':'Página do PDF lido; pode ser PDF de impressão da visualização oficial',
        'ultima_atualizacao':None}


def por_assunto(documento, assunto):
    regra=ASSUNTOS.get(assunto)
    return [c for c in documento['clausulas'] if regra and re.search(regra,monitor.normalizar(c['titulo']))]


def resumo_executivo(documento):
    reajustes=[c for c in documento['clausulas'] if re.search(r'REAJUST|CORRECOES SALARIAIS',monitor.normalizar(c['titulo']))]
    assistenciais=[c for c in documento['clausulas'] if re.search(r'ASSISTENCIAL',monitor.normalizar(c['titulo']))
                   and re.search(r'CONTRIBUI|TAXA',monitor.normalizar(c['titulo']))]
    grupos={'Reajuste salarial':reajustes,'Empregados':[],'Patronal':[],'Destinação não confirmada':[]}
    for c in assistenciais:
        titulo=monitor.normalizar(c['titulo'])
        empregado=bool(re.search(r'LABORAL|EMPREGAD[OA]S|TRABALHADORES|PROFISSIONAL',titulo))
        patronal=bool(re.search(r'PATRONAL|EMPREGADORES|EMPRESARIAL',titulo))
        grupos['Empregados' if empregado and not patronal else 'Patronal' if patronal and not empregado else 'Destinação não confirmada'].append(c)
    return grupos


def previa(clausula, reajuste=False):
    t=re.sub(r'\s+',' ',clausula['texto']).strip()
    frases=re.split(r'(?<=[.;])\s+(?=[A-ZÁÀÉÍÓÚ])',t)
    if reajuste:
        # Não leva pisos, benefícios ou outros assuntos ao resumo executivo.
        frases=[f for f in frases if re.search(r'REAJUST|CORRECAO SALARIAL',monitor.normalizar(f))]
    trechos=frases[:2]
    trecho=' '.join(trechos)
    return trecho[:480]+('…' if len(trecho)>480 else '') if trecho else 'Prévia não confirmada; leia a cláusula integral.'


def pontos_resumo(clausula, reajuste=False):
    """Recortes literais por assunto; não transforma citações em regra aplicável."""
    texto=re.sub(r'\s+',' ',clausula['texto']).strip()
    frases=re.split(r'(?<=[.;])\s+(?=[A-ZÁÀÉÍÓÚ])',texto)
    regras = {
        'Regra e percentuais citados':r'REAJUST|CORRECAO SALARIAL',
        'Proporcionalidade':r'PROPORCION|ADMITID',
        'Limites e exceções':r'FAIXA|LIMITE|RESSALV|EXCET|EXCECAO|COMPENSAD',
    } if reajuste else {
        'Valor, percentual e cobrança citados':r'R\$|\d[,.\d]*\s*%|DESCONT|COBRAN',
        'Periodicidade e pagamento':r'MENSAL|ANUAL|PERIODIC|VENCIM|PAGAMENTO|RECOLH|PRAZO',
        'Oposição':r'OPOSICAO|OPOR',
        'Condições e exceções':r'RESSALV|EXCET|EXCECAO|ISENT|CONDIC',
    }
    pontos=[]
    for titulo,regra in regras.items():
        candidatas=[f for f in frases if re.search(regra,monitor.normalizar(f))]
        if reajuste:
            candidatas=[f for f in candidatas if not re.search(r'R\$|PISOS (?:SALARIAIS )?PARA',monitor.normalizar(f))]
        if candidatas:
            frase=candidatas[0]
            pontos.append({'titulo':titulo,'trecho':frase[:360]+('…' if len(frase)>360 else ''),'referencia':referencia(clausula)})
    return pontos


def localizar_consulta(pasta):
    """Aceita resultado, pasta da execução ou raiz de saídas, sem recursão ampla."""
    pasta=Path(pasta).resolve()
    if pasta.name=='resultado' and (pasta.parent/'coleta_automatica.json').is_file():
        return pasta
    if (pasta/'coleta_automatica.json').is_file() and (pasta/'resultado').is_dir():
        return pasta/'resultado'
    if pasta.is_dir():
        candidatas=sorted((p/'resultado' for p in pasta.glob('online_*')
                           if p.is_dir() and (p/'coleta_automatica.json').is_file() and (p/'resultado').is_dir()),
                          key=lambda p:p.parent.name,reverse=True)
        if candidatas:return candidatas[0]
    raise ValueError('Nenhuma consulta salva encontrada. Selecione saidas, a pasta online_DATA_HORA ou sua pasta resultado. '
                     'Mantenha o arquivo coleta_automatica.json e a pasta documentos da execução.')


def carregar_consulta(pasta_resultado):
    pasta=localizar_consulta(pasta_resultado)
    raiz=pasta.parent
    manifest=json.loads((raiz/'coleta_automatica.json').read_text(encoding='utf-8'))
    documentos,pendencias=[],[]
    for item in manifest.get('instrumentos',[]):
        try:
            relativo=Path(item['arquivo']);arquivo=(raiz/relativo).resolve()
            if relativo.is_absolute() or not arquivo.is_relative_to(raiz/'documentos'):
                raise ValueError('Arquivo fora da pasta de documentos da consulta')
            doc=ler_documento(arquivo,item.get('fonte',''))
            if doc['Registro'] != item.get('registro'):
                raise ValueError('Registro do PDF diverge do manifesto')
            prefixo=arquivo.stem.removesuffix('_impressao').removesuffix('_original')
            originais=[p for p in arquivo.parent.glob(prefixo+'_original.*') if p.suffix.lower() in ('.doc','.docx','.pdf') and p.resolve().is_relative_to(raiz/'documentos')]
            doc['original']=str(originais[0]) if len(originais)==1 else None
            if not doc['original']:
                doc['alertas'].append('Download original não identificado; o PDF consultado permanece acessível para conferência.')
            documentos.append(doc)
        except Exception as exc:
            pendencias.append(f"{item.get('registro','Sem registro')}: leitura para o painel não confirmada ({type(exc).__name__}: {exc})")
    log=(pasta/'log_convencoes_AL.txt').read_text(encoding='utf-8') if (pasta/'log_convencoes_AL.txt').is_file() else ''
    pendencias.extend(l for l in log.splitlines() if l.startswith('PENDÊNCIA:'))
    for doc in documentos:
        doc['aditivos_relacionados']=[d['Registro'] for d in documentos if 'Aditivo' in d['Tipo'] and
            (d.get('principal')==doc['Registro'] or (doc.get('processo') and d.get('processo_principal')==doc['processo']))]
    iniciada=re.search(r'Consulta iniciada em ([^\n]+)',log)
    return {'documentos':documentos,'pendencias':pendencias,'completa':bool(manifest.get('consulta_completa')),
            'pasta':str(pasta),'consultada_em':iniciada[1] if iniciada else 'Não confirmado',
            'periodo':next((l for l in log.splitlines() if l.startswith('Período de registro:')),'Período não confirmado')}


def pesquisar(documentos, termo):
    n=monitor.normalizar(termo).strip();digitos=re.sub(r'\D','',termo)
    return [d for d in documentos if not n or n in monitor.normalizar(' '.join([d['Registro'],d.get('categoria') or '',d['Abrangência territorial'],*(p['nome'] for p in d['partes']),*d['cnpjs']]))
            or (len(digitos)>=8 and any(digitos in re.sub(r'\D','',c) for c in d['cnpjs']))]


def ordenar_por_categoria(documentos):
    def chave(doc):
        categoria=re.sub(r'\s+',' ',doc.get('categoria') or '').strip()
        return (not bool(categoria),monitor.normalizar(categoria),doc['Registro'])
    return sorted(documentos,key=chave)


def ordenar_por_registro(documentos):
    def chave(doc):
        m=re.fullmatch(r'([A-Z]+)(\d+)/(\d{4})',doc['Registro'])
        return (m[1],int(m[2]),int(m[3])) if m else (doc['Registro'],0,0)
    return sorted(documentos,key=chave)


def comparar(atual, anterior):
    if atual['Registro']==anterior['Registro']:raise ValueError('Selecione um instrumento anterior diferente')
    if atual['Tipo']!='Convenção Coletiva de Trabalho' or anterior['Tipo']!='Convenção Coletiva de Trabalho':
        raise ValueError('Comparativo exige duas convenções; aditivos precisam de análise complementar')
    if datetime.strptime(anterior['Data de registro'],'%d/%m/%Y') >= datetime.strptime(atual['Data de registro'],'%d/%m/%Y'):
        raise ValueError('O registro selecionado não é anterior ao documento atual')
    ca,cb=atual.get('categoria'),anterior.get('categoria')
    if not ca or not cb or monitor.normalizar(ca)!=monitor.normalizar(cb):
        raise ValueError('Categoria das duas convenções não confirmada como igual')
    if not atual['cnpjs'] or set(atual['cnpjs'])!=set(anterior['cnpjs']):
        raise ValueError('Entidades signatárias não confirmadas como iguais; comparação automática indisponível')
    a={monitor.normalizar(c['titulo']):c for c in anterior['clausulas']}
    b={monitor.normalizar(c['titulo']):c for c in atual['clausulas']}
    if len(a)!=len(anterior['clausulas']) or len(b)!=len(atual['clausulas']):
        raise ValueError('Títulos de cláusula repetidos: correspondência entre documentos não confirmada')
    saida=[]
    for titulo in sorted(set(a)|set(b)):
        velho,novo=a.get(titulo),b.get(titulo)
        if velho and novo and re.sub(r'\s+',' ',velho['texto'])==re.sub(r'\s+',' ',novo['texto']):continue
        diff='\n'.join(difflib.unified_diff(textwrap.wrap(velho['texto'],90) if velho else [],textwrap.wrap(novo['texto'],90) if novo else [],fromfile=anterior['Registro'],tofile=atual['Registro'],lineterm=''))
        saida.append({'titulo':(novo or velho)['titulo'],'anterior':velho,'atual':novo,'diferencas':diff})
    return saida


def texto_resumo(doc, consulta):
    linhas=['CERCONT — Departamento Pessoal','Consulta de Convenções Coletivas de Trabalho (CCT)',doc['Registro'],doc['Tipo'],
            doc.get('categoria') or 'Categoria não localizada',doc['Abrangência territorial'],
            'Data-base: '+(doc['data_base'] or 'Não confirmado'),
            'Vigência documental: '+(doc['vigencia_inicio'] or 'Não confirmado')+' a '+(doc['vigencia_fim'] or 'Não confirmado'),
            'Sindicato patronal: '+(doc['patronal']['nome'] if doc['patronal'] else 'Não confirmado'),
            'Sindicato profissional: '+(doc['profissional']['nome'] if doc['profissional'] else 'Não confirmado'),
            'Consulta: '+consulta['consultada_em'],'Situação: '+doc['situacao'],
            'Resumo de identificação; não substitui a leitura integral e dos aditivos.']
    grupos=resumo_executivo(doc)
    for titulo,itens in grupos.items():
        linhas+=['',titulo if titulo=='Reajuste salarial' else 'Contribuições assistenciais — '+titulo]
        if not itens:linhas.append('Não localizado com segurança; ausência na extração não comprova ausência no documento.')
        for c in itens:
            linhas += [referencia(c),previa(c,titulo=='Reajuste salarial')]
            linhas.extend(p['titulo']+': '+p['trecho'] for p in pontos_resumo(c,titulo=='Reajuste salarial'))
    linhas+=['','Pendências e limites',*doc['alertas'],*consulta['pendencias'],'','Fonte: '+doc['fonte'],
             'Arquivo: '+Path(doc['caminho']).name,'SHA256: '+doc['sha256']]
    return '\n'.join(linhas)


def referencia(c):
    return f"Cláusula {c['numero']} — {c['titulo']} | páginas {c['pagina']}–{c['pagina_final']} | {c['arquivo']} | {c['registro']}"


def exportar_pdf(doc, consulta, destino):
    destino=Path(destino).resolve()
    if destino.suffix.lower()!='.pdf':
        raise ValueError('A exportação deve usar um arquivo .pdf; planilhas e outros arquivos são preservados')
    protegidos={Path(d['caminho']).resolve() for d in consulta['documentos']}
    protegidos.update(Path(d['original']).resolve() for d in consulta['documentos'] if d.get('original'))
    if destino in protegidos:raise ValueError('Não é permitido substituir um documento de origem')
    linhas=[]
    for linha in texto_resumo(doc,consulta).splitlines():
        linhas.extend(textwrap.wrap(linha,90) or [''])
    writer=PdfWriter()
    for inicio in range(0,len(linhas),55):
        pagina=writer.add_blank_page(width=595,height=842)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica'),NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})
        pagina[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        comandos=[b'BT /F1 10 Tf 13 TL 38 800 Td']
        for linha in linhas[inicio:inicio+55]:
            try:
                texto=linha.encode('cp1252').replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')
            except UnicodeEncodeError as exc:
                raise ValueError('O resumo contém caracteres não suportados pelo exportador PDF; use o texto original') from exc
            comandos.append(b'('+texto+b') Tj T*')
        comandos.append(b'ET');stream=DecodedStreamObject();stream.set_data(b'\n'.join(comandos))
        pagina[NameObject('/Contents')]=writer._add_object(stream)
    with destino.open('wb') as f:writer.write(f)
    return destino
