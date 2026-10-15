"""Consulta pública ao catálogo e aos editais da CAIXA, com HTTPS verificado."""
from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from hashlib import sha256
from http.cookiejar import CookieJar
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler
from zipfile import ZipFile, BadZipFile

from pypdf import PdfReader

ORIGEM='https://www.caixa.gov.br'
CATALOGO=ORIGEM+"/_api/web/lists/getbytitle('Downloads')/Items?"+quote(
    "$select=Title,Modified,FileLeafRef,EncodedAbsUrl,Descricao&$filter=Categoria/ID eq 850 and FSObjType eq 0 and OData__ModerationStatus eq 0&$top=5000&$orderby=Modified desc",
    safe="$=,&/'()")
LIMITE=30*1024*1024


class CoeficienteIndisponivel(ValueError):
    pass


def url_oficial(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname!='www.caixa.gov.br' or p.port not in (None,443) or p.username or p.password:
        raise CoeficienteIndisponivel('A fonte não é um endereço HTTPS oficial permitido da CAIXA.')
    return url


class RedirecionamentoOficial(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        url_oficial(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def ler_pagina_tabela7(texto,competencia,pagamento):
    """Exige cabeçalho de colunas e linha completa; não desloca células ausentes."""
    if not re.search(r'GFIP\s*-\s*TABELA\.?\s*0?7\b',texto):return None
    vigencia=re.search(r'PERIODO DE\s+(\d{2}/\d{2}/\d{4})\s+A\s+(\d{2}/\d{2}/\d{4})',texto)
    if not vigencia:return None
    inicio,fim=(datetime.strptime(d,'%d/%m/%Y').date() for d in vigencia.groups())
    if not inicio<=pagamento<=fim:return None
    colunas=[];encontrados=[]
    for linha in texto.splitlines():
        if linha.strip().startswith('DATAS DE'):
            colunas=re.findall(r'(?<![\d/])\d{2}/\d{4}(?![\d/])',linha)
            continue
        if not linha.strip().startswith(pagamento.strftime('%d/%m/%Y')) or competencia not in colunas:continue
        resto=linha.strip()[10:].strip().removesuffix(' -')
        celulas=re.split(r'\s+-\s+',resto)
        # Um traço final é apenas separador da última célula, não um coeficiente.
        if celulas and celulas[-1].strip()=='-':celulas[-1]=''
        if celulas and not celulas[-1].strip():celulas.pop()
        if len(celulas)!=len(colunas):
            raise CoeficienteIndisponivel('A linha da tabela oficial tem formato inesperado; cálculo bloqueado.')
        valor=celulas[colunas.index(competencia)].strip()
        if not re.fullmatch(r'\d+,\d{9}',valor):
            raise CoeficienteIndisponivel('A célula oficial não contém coeficiente válido para a data e a competência.')
        coef=Decimal(valor.replace(',','.'))
        if coef<=0:raise CoeficienteIndisponivel('Coeficiente oficial inválido.')
        encontrados.append((coef,inicio,fim))
    if len(encontrados)>1:raise CoeficienteIndisponivel('Mais de uma célula corresponde ao cálculo; conferência necessária.')
    return encontrados[0] if encontrados else None


def extrair_coeficiente(pdf,competencia,pagamento):
    leitor=PdfReader(BytesIO(pdf));achou_tabela=False;encontrados=[]
    if len(leitor.pages)>5000:raise CoeficienteIndisponivel('Edital excede o tamanho de leitura permitido.')
    for indice,pagina in enumerate(leitor.pages):
        texto=pagina.extract_text() or ''
        tabela7=bool(re.search(r'GFIP\s*-\s*TABELA\.?\s*0?7\b',texto[:700]))
        if achou_tabela and not tabela7:break
        if not tabela7:continue
        achou_tabela=True
        resultado=ler_pagina_tabela7(texto,competencia,pagamento)
        if resultado:encontrados.append((*resultado,indice+1))
    if len(encontrados)!=1:
        raise CoeficienteIndisponivel('Não foi encontrada uma única célula da Tabela 7 para essa competência e data. Não foi usada outra data ou tabela.')
    coef,inicio,fim,pagina=encontrados[0]
    return {'coeficiente':coef,'inicio':inicio,'fim':fim,'pagina':pagina,'tabela':7,
            'competencia':competencia,'pagamento':pagamento}


class ClienteCaixa:
    def __init__(self,pasta=None):
        self.opener=build_opener(HTTPCookieProcessor(CookieJar()),RedirecionamentoOficial())
        self.pasta=Path(pasta) if pasta else Path(__file__).resolve().parent/'saidas'/'coeficientes_fgts'

    def baixar(self,url):
        url_oficial(url)
        try:
            with self.opener.open(Request(url,headers={'Accept':'application/json;odata=verbose'}),timeout=30) as resposta:
                url_oficial(resposta.geturl());dados=resposta.read(LIMITE+1)
        except HTTPError as exc:
            raise CoeficienteIndisponivel(f'CAIXA respondeu HTTP {exc.code}; sem contornar bloqueios ou autenticação.') from exc
        except (URLError,TimeoutError,OSError) as exc:
            raise CoeficienteIndisponivel('Não foi possível acessar a CAIXA com HTTPS verificado. Confira a conexão e tente novamente.') from exc
        if len(dados)>LIMITE:raise CoeficienteIndisponivel('Arquivo oficial excede o limite de download.')
        return dados

    def consultar(self,competencia,pagamento):
        # Editais mensais têm vigência de 21 do mês de referência a 20 do seguinte.
        # A vigência do próprio PDF também é obrigatoriamente verificada.
        referencia=pagamento.replace(day=1)
        if pagamento.day<=20:
            referencia=date(referencia.year-1,12,1) if referencia.month==1 else referencia.replace(month=referencia.month-1)
        documentos=[];url=CATALOGO
        for _ in range(10):
            try:d=json.loads(self.baixar(url))['d']
            except (KeyError,TypeError,json.JSONDecodeError) as exc:
                raise CoeficienteIndisponivel('O catálogo público da CAIXA mudou de formato.') from exc
            documentos.extend(d['results']);url=d.get('__next')
            if not url:break
            url_oficial(url)
        else:raise CoeficienteIndisponivel('Catálogo excedeu o limite de paginação; consulta incompleta.')
        documentos=[d for d in documentos if re.search(r'\b'+referencia.strftime('%m/%Y')+r'\b',str(d.get('Title','')))]
        if len(documentos)!=1:
            raise CoeficienteIndisponivel('Edital mensal '+referencia.strftime('%m/%Y')+' não disponível individualmente no catálogo. Tabelas anuais agrupadas e datas ainda não publicadas não são estimadas.')
        documento=documentos[0];url=documento['EncodedAbsUrl'].replace('http:','https:',1);url_oficial(url)
        caminho=urlsplit(url).path
        if not caminho.startswith('/Downloads/FGTS-coeficientes/') or not caminho.lower().endswith('.zip'):
            raise CoeficienteIndisponivel('O arquivo listado não é um edital mensal ZIP reconhecido.')
        # Mesmo serviço público SharePoint usado pelo site. Alguns links diretos
        # devolvem redirecionamento para si; $value entrega o arquivo publicado.
        arquivo_url=ORIGEM+"/_api/web/GetFileByServerRelativeUrl('"+quote(caminho,safe='/_-.')+"')/$value"
        pacote=self.baixar(arquivo_url)
        try:
            with ZipFile(BytesIO(pacote)) as z:
                pdfs=[i for i in z.infolist() if i.filename.lower().endswith('.pdf')]
                if len(pdfs)!=1 or pdfs[0].file_size>LIMITE:
                    raise CoeficienteIndisponivel('Conteúdo do edital ZIP não reconhecido ou grande demais.')
                # Leitura em memória: nunca extrai caminhos nem executa arquivos.
                pdf=z.read(pdfs[0])
        except (BadZipFile,RuntimeError) as exc:
            raise CoeficienteIndisponivel('O download não contém um edital ZIP público válido.') from exc
        try:resultado=extrair_coeficiente(pdf,competencia,pagamento)
        except CoeficienteIndisponivel:raise
        except Exception as exc:raise CoeficienteIndisponivel('Não foi possível ler com segurança a tabela do edital oficial.') from exc
        digest=sha256(pdf).hexdigest()
        self.pasta.mkdir(parents=True,exist_ok=True)
        destino=self.pasta/('edital_'+digest+'.pdf')
        if not destino.exists():
            with destino.open('xb') as f:f.write(pdf)
        resultado.update(fonte=url,download=arquivo_url,sha256=digest,arquivo=str(destino),titulo=documento['Title'])
        return resultado


def calcular_com_coeficiente(dados,consulta):
    competencia=dados['competencia'];regra=dados.get('regra','')
    if consulta['competencia']!=competencia.strftime('%m/%Y') or consulta['pagamento']!=dados['pagamento']:
        raise CoeficienteIndisponivel('O coeficiente não corresponde exatamente à competência e ao pagamento informados.')
    if not consulta['inicio']<=dados['pagamento']<=consulta['fim']:
        raise CoeficienteIndisponivel('Data fora da vigência do coeficiente oficial.')
    contribuicao=date(2001,10,1)<=competencia<=date(2006,12,1) and regra=='Nenhum'
    partes=[]
    for campo,base in dados['valores'].items():
        aprendiz=campo=='aprendiz'
        if aprendiz and competencia<date(2001,1,1):
            raise CoeficienteIndisponivel('Aprendizes antes de 2001 exigem conferência histórica não implementada.')
        aliquota=Decimal('0.02') if aprendiz else Decimal('0.08')
        fator=(Decimal('0.3125') if contribuicao else Decimal('0.25')) if aprendiz else (Decimal('1.0625') if contribuicao else Decimal('1'))
        principal=(base*aliquota).quantize(Decimal('0.01'),rounding=ROUND_DOWN)
        produto=base*consulta['coeficiente']*fator
        total=produto.quantize(Decimal('0.01'),rounding=ROUND_DOWN)
        if total<principal:raise CoeficienteIndisponivel('Coeficiente incompatível com o principal; cálculo bloqueado.')
        partes.append({'campo':campo,'base':base,'aliquota':aliquota,'fator':fator,'principal':principal,
                       'total':total,'encargos':total-principal,
                       'comparacao_arredondada':produto.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)})
    return {'partes':partes,'total':sum(p['total'] for p in partes),'consulta':consulta,
            'comparacao_arredondada':sum(p['comparacao_arredondada'] for p in partes)}
