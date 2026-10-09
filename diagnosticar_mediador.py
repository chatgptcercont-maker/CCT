"""Inspeção pública com navegador. Não é um coletor de instrumentos."""
import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit, urlunsplit
import uuid
from zoneinfo import ZoneInfo

URL = 'https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo'


def endereco_sem_parametros(url):
    u = urlsplit(url)
    return urlunsplit((u.scheme, u.hostname or '', u.path, '', ''))


def proxy_do_ambiente():
    # Usa a rota autorizada; não imprime configuração ou credenciais.
    valor = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if not valor:
        return None
    u = urlsplit(valor)
    if not u.hostname or u.scheme not in {'http', 'https'}:
        raise ValueError('Proxy HTTPS configurado em formato não suportado')
    proxy = {'server': f'{u.scheme}://{u.hostname}:{u.port or (443 if u.scheme == "https" else 80)}'}
    if u.username:
        proxy['username'] = unquote(u.username)
    if u.password:
        proxy['password'] = unquote(u.password)
    return proxy


def classificar_erro(mensagem):
    if 'ERR_TUNNEL_CONNECTION_FAILED' in mensagem or 'Tunnel connection failed: 403' in mensagem:
        return 'BLOQUEIO_DO_TUNEL_PROXY'
    if 'ERR_CERT' in mensagem or 'CERTIFICATE_VERIFY_FAILED' in mensagem:
        return 'ERRO_TLS'
    return 'FALHA_DE_ACESSO'


def investigar(saida, visivel=False, pesquisar=False):
    saida.mkdir(parents=True, exist_ok=False)
    resultado = {'url': URL, 'consulta_validada': False, 'instrumentos_coletados': None,
                 'estado': 'NAO_EXECUTADO', 'requisicoes': [], 'formularios': [], 'links': []}
    try:
        from playwright.sync_api import sync_playwright
        proxy = proxy_do_ambiente()
        with sync_playwright() as p:
            executavel = shutil.which('chromium') or shutil.which('chromium-browser')
            options = {'headless': not visivel, 'proxy': proxy}
            if executavel:
                options['executable_path'] = executavel
            navegador = p.chromium.launch(**options)
            try:
                context = navegador.new_context()
                page = context.new_page()
                page.on('response', lambda r: resultado['requisicoes'].append({
                    'metodo': r.request.method, 'url': endereco_sem_parametros(r.url), 'status': r.status}))
                page.on('requestfailed', lambda r: resultado['requisicoes'].append({
                    'metodo': r.method, 'url': endereco_sem_parametros(r.url), 'falha': r.failure}))
                resposta = page.goto(URL, wait_until='domcontentloaded', timeout=30000)
                resultado['http'] = resposta.status if resposta else None
                if resposta is None or resposta.status >= 400:
                    resultado['estado'] = 'HTTP_BLOQUEADO_OU_INDISPONIVEL'
                else:
                    # Permite JavaScript e requisições normais da página terminarem.
                    # Não aguarda desafios de segurança nem tenta solucioná-los.
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                    except Exception:
                        resultado['carregamento'] = 'Rede não estabilizou em 10 segundos'
                    resultado['titulo'] = page.title()
                    desafio = page.locator('iframe[src*="bframe"], iframe[src*="hcaptcha"]')
                    captcha = any(desafio.nth(i).is_visible() for i in range(desafio.count()))
                    if captcha:
                        resultado['estado'] = 'CAPTCHA_NAO_CONTORNADO'
                    elif page.locator('input[type="password"]').count():
                        resultado['estado'] = 'AUTENTICACAO_NAO_REALIZADA'
                    else:
                        resultado['estado'] = 'PAGINA_PUBLICA_RECEBIDA_CONSULTA_AINDA_NAO_IMPLEMENTADA'
                        # Nunca salva cookies, cabeçalhos de autenticação ou tokens ocultos.
                        resultado['formularios'] = page.locator('form, #divPrincipal').evaluate_all('''forms => forms.map(f => ({
                            action: f.action, method: f.method,
                            campos: Array.from(f.querySelectorAll('input:not([type="hidden"]):not([type="password"]), select, textarea, button')).map(e => ({
                                tag: e.tagName, id: e.id, nome: e.name, tipo: e.type,
                                rotulo: Array.from(e.labels || []).map(l => l.innerText).join(' '),
                                texto: e.tagName === 'BUTTON' ? e.innerText : '',
                                opcoes: e.tagName === 'SELECT' ? Array.from(e.options).map(o => ({texto:o.text, valor:o.value})) : []
                            }))
                        }))''')
                        for form in resultado['formularios']:
                            form['action'] = endereco_sem_parametros(form['action'])
                        if pesquisar:
                            pesquisar_pelo_botao(page, resultado)
                        links = page.locator('a[href]').evaluate_all('es => es.map(e => ({texto:e.innerText, url:e.href}))')
                        resultado['links'] = [{'texto': l['texto'], 'url': endereco_sem_parametros(l['url'])} for l in links
                                              if urlsplit(l['url']).hostname in {'mediador.trabalho.gov.br','www3.mte.gov.br','www.gov.br'}]
            finally:
                navegador.close()
    except Exception as exc:
        # A mensagem completa do navegador pode incluir configuração do proxy.
        # Registra apenas classe e causa conhecida, sem valores de credenciais.
        resultado['estado'] = classificar_erro(str(exc))
        resultado['erro_classe'] = type(exc).__name__
    (saida/'diagnostico_mediador.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=lambda v: v.decode('utf-8', errors='replace') if isinstance(v, bytes) else str(v)), encoding='utf-8')
    mensagem = ('CONSULTA NÃO CONCLUÍDA. Esta ferramenta inspeciona o acesso público; '
                'não pesquisa instrumentos nem comprova ausência de novidades.\nEstado: '+resultado['estado']+'\n')
    (saida/'resumo_convencoes_AL.txt').write_text(mensagem, encoding='utf-8')
    (saida/'log_convencoes_AL.txt').write_text(mensagem+f'URL: {URL}\nConsulte diagnostico_mediador.json para evidências técnicas.\n', encoding='utf-8')
    return resultado


def pesquisar_pelo_botao(page, resultado):
    """Somente navegação normal. Não lê, fabrica ou reaproveita tokens."""
    hoje = datetime.now(ZoneInfo('America/Maceio')).date()
    page.locator('#cboTPRequerimento').select_option('convencao')
    page.locator('#chkPeriodoRegistro').check()
    page.locator('#txtDTInicioRegistro').fill((hoje-timedelta(days=6)).strftime('%d/%m/%Y'))
    page.locator('#txtDTFimRegistro').fill(hoje.strftime('%d/%m/%Y'))
    page.locator('#cboSTVigencia').select_option('2')
    # Não confundir UF de registro com abrangência territorial.
    page.locator('#cboUFRegistro').select_option('')
    for campo in ['chkMunicipal','chkIntermunicipal','chkEstadual','chkInterestadual','chkNacional']:
        page.locator('#'+campo).check()
    page.locator('#cboUFAbrangenciaTerritorial').select_option('AL')
    with page.expect_response(lambda r: '/getPartAbrangenciaAddUF' in r.url, timeout=20000):
        page.locator('#btnAdicionarUF').click()
    resultado['filtros_testados'] = {'tipo':'convencao','abrangencia':'AL',
        'inicio':(hoje-timedelta(days=6)).isoformat(),'fim':hoje.isoformat()}
    try:
        with page.expect_response(lambda r: '/getConsultaAvancada' in r.url, timeout=30000) as espera:
            page.locator('#btnPesquisar').click()
        resposta = espera.value
        resultado['http_pesquisa'] = resposta.status
        if resposta.status >= 400:
            resultado['estado'] = 'PESQUISA_REJEITADA'
        else:
            resultado['estado'] = 'RESPOSTA_DE_PESQUISA_RECEBIDA_NAO_VALIDADA'
            resultado['texto_resultado'] = page.locator('#divConsultaDetalhada').inner_text(timeout=10000)[:100000]
    except Exception:
        resultado['estado'] = 'PESQUISA_NAO_CONCLUIDA_SEGURANCA_OU_INDISPONIBILIDADE'
        # Não tenta de novo para alterar pontuação de CAPTCHA nem interage com desafios.
    return resultado


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saida', type=Path)
    p.add_argument('--pesquisar', action='store_true', help='Testa o botão oficial com filtros de CCT/AL/sete dias; usa a validação nativa do site')
    p.add_argument('--visivel', action='store_true', help='Abre o navegador normalmente, sem interferir em CAPTCHA/login')
    a = p.parse_args()
    saida = a.saida or Path('saidas') / ('investigacao_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
    try:
        r = investigar(saida, a.visivel, a.pesquisar)
    except FileExistsError:
        print('Escolha uma pasta nova; nada foi sobrescrito.')
        return 2
    print(r['estado']); print(f'Evidências: {saida.resolve()}')
    return 2  # Inspeção nunca é apresentada como consulta concluída.


if __name__ == '__main__':
    raise SystemExit(main())
