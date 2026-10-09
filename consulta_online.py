"""Coleta pela navegação pública normal do Mediador, sem contornar proteções."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urljoin, urlsplit
import uuid
from zoneinfo import ZoneInfo

from diagnosticar_mediador import URL, proxy_do_ambiente, classificar_erro
import monitor

TIPOS = ('convencao', 'termoAditivoConvecao')


class ConsultaIncompleta(RuntimeError):
    pass


def captcha_interativo(page):
    desafios = page.locator('iframe[src*="bframe"], iframe[src*="hcaptcha"]')
    return any(desafios.nth(i).is_visible() for i in range(desafios.count()))


def hoje_alagoas():
    return datetime.now(ZoneInfo('America/Maceio')).date()


def paginacao(texto):
    n = monitor.normalizar(texto)
    m = re.search(r'RESULTADO:\s*(\d+)\s+INSTRUMENTO\(S\).*?PAGINA\s+(\d+)\s+DE\s+(\d+)', n, re.S)
    if m:
        total, atual, paginas = map(int, m.groups())
        if total < 0 or atual < 1 or paginas < atual or (total and not paginas):
            raise ConsultaIncompleta('Contagem de resultados inconsistente')
        return total, atual, paginas
    # Somente mensagem explicitamente observável; página vazia nunca significa zero.
    if re.fullmatch(r'\s*RESULTADO:\s*(?:NENHUM INSTRUMENTO COLETIVO ENCONTRADO|0 INSTRUMENTO\(S\) COLETIVO\(S\) ENCONTRADO\(S\))\s*', n):
        return 0, 1, 1
    raise ConsultaIncompleta('Formato do resultado não reconhecido; não é possível confirmar a paginação')


def preparar_filtros(page, hoje, tipo):
    page.locator('#cboTPRequerimento').select_option(tipo)
    page.locator('#chkPeriodoRegistro').check()
    page.locator('#txtDTInicioRegistro').fill((hoje-timedelta(days=6)).strftime('%d/%m/%Y'))
    page.locator('#txtDTFimRegistro').fill(hoje.strftime('%d/%m/%Y'))
    page.locator('#cboSTVigencia').select_option('2')
    page.locator('#cboUFRegistro').select_option('')
    for campo in ['chkMunicipal', 'chkIntermunicipal', 'chkEstadual', 'chkInterestadual', 'chkNacional']:
        page.locator('#'+campo).check()
    page.locator('#cboUFAbrangenciaTerritorial').select_option('AL')
    with page.expect_response(lambda r: '/getPartAbrangenciaAddUF' in r.url, timeout=30000) as espera:
        page.locator('#btnAdicionarUF').click()
    if espera.value.status != 200:
        raise ConsultaIncompleta(f'Seleção territorial falhou: HTTP {espera.value.status}')


def pesquisar(page):
    # O código original do botão obtém o reCAPTCHA. Não interceptamos tokens.
    with page.expect_response(lambda r: '/ConsultarInstColetivo/getConsultaAvancada' in r.url, timeout=45000) as espera:
        page.locator('#btnPesquisar').click()
    resposta = espera.value
    if resposta.status != 200:
        detalhe = ''
        # O portal usa HTTP 500 também para notificar ausência de registros.
        # Preservamos o erro e a mensagem literal, sem converter falhas em sucesso.
        if resposta.status == 500:
            try:
                if resposta.json().get('message') == 'Nenhum registro encontrado.':
                    detalhe = ': portal informou "Nenhum registro encontrado."; resposta HTTP de erro preservada'
            except (ValueError, AttributeError, TypeError):
                pass
        raise ConsultaIncompleta(f'Pesquisa oficial respondeu HTTP {resposta.status}' + detalhe)
    page.locator('#divExibirConsultaDetalhada').wait_for(state='visible', timeout=15000)
    return paginacao(page.locator('#divConsultaDetalhada h2').inner_text())


def salvar_instrumento(page, row, pasta, hoje, eventos):
    regs = re.findall(r'\b' + monitor.REGEX_REGISTRO + r'\b', row.inner_text())
    if len(set(regs)) != 1:
        raise ConsultaIncompleta('Registro ambíguo na linha do resultado')
    reg = monitor.registro(regs[0])
    stem = reg.replace('/', '_')
    link = row.locator('a').filter(has_text='Visualizar Instrumento Coletivo')
    if link.count() != 1:
        raise ConsultaIncompleta(f'{reg}: link de visualização não reconhecido')
    fonte = urljoin(URL, link.get_attribute('href') or '')
    if not monitor.fonte_oficial(fonte):
        raise ConsultaIncompleta(f'{reg}: visualização fora da fonte oficial')
    original = None
    botao_download = row.locator('a').filter(has_text='Download')
    if botao_download.count() == 1:
        try:
            with page.expect_download(timeout=30000) as espera:
                botao_download.click()
            download = espera.value
            if urlsplit(download.url).hostname != urlsplit(URL).hostname:
                raise ConsultaIncompleta('Download redirecionado para origem não confirmada')
            ext = Path(download.suggested_filename).suffix.lower()
            if ext not in {'.pdf', '.doc', '.docx'}:
                raise ConsultaIncompleta('Formato de download oficial não reconhecido')
            original = pasta / (stem+'_original'+ext)
            download.save_as(original)
            if original.stat().st_size > 30*1024*1024:
                raise ConsultaIncompleta('Documento original excede 30 MB')
            eventos.append(f'{reg}: original oficial salvo em {original.name}; SHA256 '+hashlib.sha256(original.read_bytes()).hexdigest())
        except Exception as exc:
            eventos.append(f'{reg}: download indisponível ({type(exc).__name__}); tentando visualização oficial')
            original = None
    # A visualização gera token de segurança e POST por meio do código do portal.
    with page.expect_popup(timeout=30000) as popup:
        link.click()
    doc = popup.value
    try:
        doc.wait_for_function("document.body && document.body.innerText.toUpperCase().includes('NÚMERO DE REGISTRO NO MTE')", timeout=30000)
        original_texto = doc.locator('body').inner_text()
        dados = monitor.extrair(original_texto, hoje)
        if dados['Registro'] != reg:
            raise ConsultaIncompleta('Registro da visualização diverge do resultado de pesquisa')
        if original is not None and original.suffix == '.pdf':
            pdf = original
        else:
            pdf = pasta / (stem+'_impressao.pdf')
            doc.pdf(path=str(pdf), format='A4', print_background=True)
            eventos.append(f'{reg}: PDF de impressão gerado da visualização oficial; não é PDF original oferecido pelo portal')
        campos_pdf = monitor.extrair(monitor.ler_pdf(pdf), hoje)
        if any(campos_pdf[c] != dados[c] for c in ['Registro', 'Data de registro', 'Tipo']):
            raise ConsultaIncompleta('Campos do PDF divergem do documento visualizado')
        return {'registro': reg, 'arquivo': 'documentos/'+pdf.name, 'fonte': fonte}
    finally:
        doc.close()


def coletar(browser, pasta, hoje, eventos, progresso):
    instrumentos, pendencias, totais = [], [], {}
    for tipo in TIPOS:
        progresso('Pesquisando '+('convenções' if tipo == 'convencao' else 'aditivos de convenções')+' no Mediador…')
        # Sessões independentes impedem que a abrangência/session de uma pesquisa contamine a outra.
        context = browser.new_context(accept_downloads=True)
        context.on('response', lambda r: eventos.append(f'HTTP {r.status}: {urlsplit(r.url).path}')
                   if r.status >= 400 and urlsplit(r.url).hostname == urlsplit(URL).hostname else None)
        page = context.new_page()
        try:
            resposta = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            if resposta is None or resposta.status != 200:
                raise ConsultaIncompleta('Página de consulta não disponível: HTTP '+str(resposta.status if resposta else 'sem resposta'))
            if page.locator('input[type="password"]').count():
                raise ConsultaIncompleta('Autenticação exigida; acesso automático interrompido')
            preparar_filtros(page, hoje, tipo)
            total, atual, paginas = pesquisar(page)
            eventos.append(f'{tipo}: resultado oficial {total} instrumento(s), {paginas} página(s)')
            vistos = set()
            if paginas > 200:
                raise ConsultaIncompleta('Mais de 200 páginas; consulta interrompida sem presumir completude')
            for numero in range(1, paginas+1):
                if numero != atual:
                    raise ConsultaIncompleta('Página recebida fora da sequência')
                rows = page.locator('#grdInstrumentos tr[indice]')
                for i in range(rows.count()):
                    row = rows.nth(i)
                    identidade = row.get_attribute('indice')
                    if not identidade or identidade in vistos:
                        raise ConsultaIncompleta('Identificador de instrumento ausente/repetido na paginação')
                    vistos.add(identidade)
                    try:
                        item = salvar_instrumento(page, row, pasta, hoje, eventos)
                        instrumentos.append(item)
                        progresso('Documento lido: '+item['registro'])
                    except Exception as exc:
                        motivo = str(exc) if isinstance(exc, (ConsultaIncompleta, ValueError)) else type(exc).__name__
                        eventos.append(f'{identidade}: documento indisponível ou rejeitado: {motivo}')
                        # Exclusões documentadas não são uma falha na coleta.
                        if not motivo.startswith('Excluído:'):
                            pendencias.append(tipo+': '+identidade+': '+motivo)
                if numero < paginas:
                    proxima = page.locator('#grdInstrumentos > table > tfoot a').filter(has_text=re.compile(r'^\s*'+str(numero+1)+r'\s*$'))
                    if proxima.count() != 1:
                        raise ConsultaIncompleta('Controle da próxima página não reconhecido')
                    with page.expect_response(lambda r: '/getConsultaAvancada' in r.url, timeout=45000) as espera:
                        proxima.click()
                    if espera.value.status != 200:
                        raise ConsultaIncompleta(f'Paginação respondeu HTTP {espera.value.status}')
                    page.wait_for_function("n => document.querySelector('#divConsultaDetalhada h2').innerText.includes('Página '+n+' de')", arg=numero+1, timeout=15000)
                    novo_total, atual, novo_paginas = paginacao(page.locator('#divConsultaDetalhada h2').inner_text())
                    if (novo_total, novo_paginas) != (total, paginas):
                        raise ConsultaIncompleta('Resultado mudou durante paginação; consultar novamente')
            if len(vistos) != total:
                raise ConsultaIncompleta(f'Total oficial {total} difere dos {len(vistos)} registros examinados')
            totais[tipo] = total
        except Exception as exc:
            motivo = str(exc) if isinstance(exc, ConsultaIncompleta) else classificar_erro(str(exc))+': '+type(exc).__name__
            if not page.is_closed() and captcha_interativo(page):
                motivo = 'CAPTCHA interativo detectado; consulta interrompida sem resolver ou contornar o desafio'
            pendencias.append(tipo+': '+motivo)
            eventos.append(tipo+': '+motivo+'; sem contornar a proteção ou repetir a pesquisa')
            if any(s in motivo for s in ['HTTP 401', 'HTTP 403', 'CAPTCHA interativo', 'Autenticação exigida', 'BLOQUEIO_DO_TUNEL_PROXY', 'ERRO_TLS']):
                break
        finally:
            context.close()
    return instrumentos, pendencias, totais


def executar_online(controle=None, raiz=Path('saidas'), aba=None, progresso=lambda mensagem: None):
    hoje = hoje_alagoas()
    pasta = raiz / ('online_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
    pasta.mkdir(parents=True, exist_ok=False)
    docs = pasta/'documentos'; docs.mkdir()
    eventos = [f'Consulta iniciada em {datetime.now().isoformat(timespec="seconds")}',
               f'Período de registro: {hoje-timedelta(days=6)} a {hoje}, fuso America/Maceio; somente CCT/aditivo de CCT; abrangência AL']
    instrumentos, pendencias, totais = [], [], {}
    try:
        # Valida o controle antes de consultar; entrada é apenas lida.
        monitor.abrir_controle(controle, aba)
        from playwright.sync_api import sync_playwright
        proxy = proxy_do_ambiente()
        with sync_playwright() as p:
            options = {'headless': True, 'proxy': proxy}
            executavel = shutil.which('chromium') or shutil.which('chromium-browser')
            if executavel:
                options['executable_path'] = executavel
            browser = p.chromium.launch(**options)
            try:
                instrumentos, pendencias, totais = coletar(browser, docs, hoje, eventos, progresso)
            finally:
                browser.close()
    except Exception as exc:
        motivo = str(exc) if isinstance(exc, ValueError) else classificar_erro(str(exc))+': '+type(exc).__name__
        pendencias.append(motivo); eventos.append(motivo)
    completo = not pendencias and len(totais) == len(TIPOS)
    # Manifesto de auditoria gerado internamente; não é preparado pelo usuário.
    manifesto = pasta/'coleta_automatica.json'
    manifesto.write_text(json.dumps({'consulta_completa': completo, 'instrumentos': instrumentos}, ensure_ascii=False, indent=2), encoding='utf-8')
    resultado = pasta/'resultado'
    code = monitor.executar(manifesto, controle, resultado, hoje, aba, modo='online')
    eventos.extend('PENDÊNCIA: '+p for p in pendencias)
    log = resultado/'log_convencoes_AL.txt'
    log.write_text('\n'.join(eventos)+'\n'+log.read_text(encoding='utf-8'), encoding='utf-8')
    resumo = resultado/'resumo_convencoes_AL.txt'
    resumo.write_text(resumo.read_text(encoding='utf-8')+'Totais oficiais por tipo: '+str(totais)+'\n'+
                     ('Pendências: '+'; '.join(pendencias)+'\n' if pendencias else ''), encoding='utf-8')
    return {'codigo': code, 'pasta': resultado, 'controle': resultado/'controle_convencoes_AL.xlsx',
            'completa': completo and code == 0, 'resumo': resumo.read_text(encoding='utf-8')}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controle', type=Path)
    parser.add_argument('--aba')
    args = parser.parse_args()
    resultado = executar_online(args.controle, aba=args.aba, progresso=print)
    print(resultado['resumo']); print('Resultados:', resultado['pasta'].resolve())
    raise SystemExit(resultado['codigo'])
