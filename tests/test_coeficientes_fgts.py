"""Dados sintéticos para regras e falhas; não comprovam acesso à CAIXA."""
from datetime import date
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch
from urllib.error import HTTPError
from zipfile import ZipFile

from calculadora_fgts import conferir_dados,calcular_online,REGRAS
from coeficientes_fgts import (ler_pagina_tabela7,calcular_com_coeficiente,
    ClienteCaixa,CoeficienteIndisponivel,url_oficial)


TEXTO='''EDITAL - GFIP - TABELA.07
COEFICIENTES POR DATA DE PAGAMENTO NO PERIODO DE 21/09/2026 A 20/10/2026
DATAS DE 01/2024 02/2024
PAGAMENTO
19/10/2026 0,105093260 - 0,104656933
20/10/2026 0,105101710 - 0,104665349
DATAS DE 03/2024 04/2024
PAGAMENTO
20/10/2026 0,103784644 - 0,103680613
'''


def entrada():
    return {'base':'Trabalhadores','competencia':'02/2024','pagamento':'20/10/2026',
            'folha':'1200','regime':'SEFIP/GRF','suspensao':True}


def consulta(comp='02/2024',coef='0.104665349'):
    return {'coeficiente':Decimal(coef),'competencia':comp,'pagamento':date(2026,10,20),
            'inicio':date(2026,9,21),'fim':date(2026,10,20),'pagina':1,'tabela':7}


class CoeficientesTests(unittest.TestCase):
    def test_seleciona_coluna_e_bloco_exatos(self):
        r=ler_pagina_tabela7(TEXTO,'02/2024',date(2026,10,20))
        self.assertEqual(r[0],Decimal('0.104665349'))
        r=ler_pagina_tabela7(TEXTO,'04/2024',date(2026,10,20))
        self.assertEqual(r[0],Decimal('0.103680613'))

    def test_nao_troca_data_competencia_tabela_ou_vigencia(self):
        for texto,comp,dia in [(TEXTO,'05/2024',date(2026,10,20)),
             (TEXTO,'02/2024',date(2026,10,17)),(TEXTO,'02/2024',date(2026,10,21)),
             (TEXTO.replace('TABELA.07','TABELA.08'),'02/2024',date(2026,10,20))]:
            self.assertIsNone(ler_pagina_tabela7(texto,comp,dia))

    def test_celula_ausente_ou_duplicada_bloqueia(self):
        for texto in [TEXTO.replace('0,104665349',''),TEXTO+TEXTO]:
            with self.assertRaises(CoeficienteIndisponivel):ler_pagina_tabela7(texto,'02/2024',date(2026,10,20))

    def test_truncamento_oficial_e_comparacao_arredondada(self):
        r=calcular_com_coeficiente(conferir_dados(entrada()),consulta())
        self.assertEqual(r['partes'][0]['principal'],Decimal('96.00'))
        self.assertEqual(r['partes'][0]['encargos'],Decimal('29.59'))
        self.assertEqual(r['total'],Decimal('125.59'))
        self.assertEqual(r['comparacao_arredondada'],Decimal('125.60'))

    def test_aprendiz_e_fator_contribuicao_historica(self):
        d=entrada();d.update(base='Ambos',aprendiz='1000',competencia='01/2002',regra='Nenhum')
        r=calcular_com_coeficiente(conferir_dados(d),consulta('01/2002','0.200000000'))
        self.assertEqual(r['partes'][0]['fator'],Decimal('1.0625'))
        self.assertEqual(r['partes'][1]['fator'],Decimal('0.3125'))
        for regra in REGRAS[:3]:
            d['regra']=regra
            r=calcular_com_coeficiente(conferir_dados(d),consulta('01/2002','0.200000000'))
            self.assertEqual(r['partes'][1]['fator'],Decimal('0.25'))

    def test_consulta_vinculada_a_mes_e_data(self):
        for c in [consulta('01/2024'),dict(consulta(),pagamento=date(2026,10,19))]:
            with self.assertRaises(CoeficienteIndisponivel):calcular_com_coeficiente(conferir_dados(entrada()),c)

    def test_regimes_e_suspensoes_bloqueiam_antes_da_internet(self):
        for alteracao in [{'regime':'FGTS Digital'},{'regime':'eSocial doméstico'},
                          {'suspensao':False},{'competencia':'03/2024'}]:
            d=entrada();d.update(alteracao);cliente=MagicMock()
            with self.assertRaises(ValueError):calcular_online(d,cliente)
            cliente.consultar.assert_not_called()

    def test_somente_https_caixa_sem_credenciais(self):
        for u in ['http://www.caixa.gov.br/a','https://outro.exemplo/a',
                  'https://www.caixa.gov.br.exemplo/a','https://senha@www.caixa.gov.br/a']:
            with self.assertRaises(CoeficienteIndisponivel):url_oficial(u)

    def test_http_403_nao_repete_nem_contorna(self):
        c=ClienteCaixa();c.opener=MagicMock()
        c.opener.open.side_effect=HTTPError('https://www.caixa.gov.br/a',403,'Forbidden',{},None)
        with self.assertRaisesRegex(CoeficienteIndisponivel,'403'):c.baixar('https://www.caixa.gov.br/a')
        c.opener.open.assert_called_once()

    def test_catalogo_download_e_copia_local_sem_enviar_folha(self):
        doc={'Title':'Edital 09/2026','EncodedAbsUrl':'http://www.caixa.gov.br/Downloads/FGTS-coeficientes/ED_202609.zip'}
        b=BytesIO()
        with ZipFile(b,'w') as z:z.writestr('edital.pdf',b'%PDF-arquivo-ficticio')
        with tempfile.TemporaryDirectory() as tmp:
            c=ClienteCaixa(tmp);c.baixar=MagicMock(side_effect=[json.dumps({'d':{'results':[doc]}}).encode(),b.getvalue()])
            with patch('coeficientes_fgts.extrair_coeficiente',return_value=consulta()):
                r=calcular_online(entrada(),c)
            self.assertTrue(Path(r['consulta']['arquivo']).is_file())
            self.assertEqual(c.baixar.call_count,2)
            for chamada in c.baixar.call_args_list:
                self.assertNotIn('1200',chamada.args[0]);self.assertNotIn('folha',chamada.args[0])
            self.assertIn('GetFileByServerRelativeUrl',c.baixar.call_args.args[0])


if __name__=='__main__':unittest.main()
