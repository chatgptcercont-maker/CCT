from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from pypdf import PdfReader
from recibo_rescisao import preparar_recibo,valor_monetario,exportar_recibo,texto_recibo


def dados():
    return {'empresa':'EMPRESA FICTICIA','trabalhador':'TRABALHADOR FICTICIO','local':'Maceió',
            'data_recibo':'14/10/2026','admissao':'01/01/2026','desligamento':'10/10/2026'}


class ReciboTests(unittest.TestCase):
    def test_valores_brasileiros_e_decimais_sem_arredondar_silenciosamente(self):
        self.assertEqual(valor_monetario('R$ 1.250,50'),Decimal('1250.50'))
        self.assertEqual(valor_monetario('1.000'),Decimal('1000.00'))
        self.assertEqual(valor_monetario('1250.50'),Decimal('1250.50'))
        for v in ['-10','10,001','abc','1e3','']:
            with self.assertRaises(ValueError):valor_monetario(v)

    def test_soma_apenas_as_verbas_informadas(self):
        r=preparar_recibo(dados(),[{'tipo':'Provento','descricao':'Verba manual','valor':'0,10'},
                                  {'tipo':'Provento','descricao':'Outra verba manual','valor':'0,20'},
                                  {'tipo':'Desconto','descricao':'Desconto informado','valor':'0,05'}])
        self.assertEqual(r['liquido'],Decimal('0.25'))
        self.assertEqual(len(r['itens']),3)
        self.assertNotIn('aviso prévio',texto_recibo(r).lower())

    def test_dados_incompletos_datas_e_total_negativo_impedem_emissao(self):
        itens=[{'tipo':'Provento','descricao':'Verba manual','valor':'100'}]
        d=dados();d['empresa']=''
        with self.assertRaises(ValueError):preparar_recibo(d,itens)
        d=dados();d['admissao']='20/10/2026'
        with self.assertRaises(ValueError):preparar_recibo(d,itens)
        with self.assertRaises(ValueError):preparar_recibo(dados(),[])
        with self.assertRaises(ValueError):preparar_recibo(dados(),itens+[{'tipo':'Desconto','descricao':'Desconto','valor':'101'}])

    def test_pdf_reproduz_valores_e_nao_sobrescreve_existentes(self):
        r=preparar_recibo(dados(),[{'tipo':'Provento','descricao':'Saldo informado','valor':'1.250,50'},
                                  {'tipo':'Desconto','descricao':'Adiantamento informado','valor':'50,00'}])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'recibo.pdf';exportar_recibo(r,p)
            conteudo='\n'.join(x.extract_text() or '' for x in PdfReader(p).pages)
            self.assertIn('R$ 1.200,50',conteudo);self.assertIn('EMPRESA FICTICIA',conteudo)
            self.assertIn('Assinatura do trabalhador',conteudo)
            original=p.read_bytes()
            with self.assertRaises(ValueError):exportar_recibo(r,p)
            self.assertEqual(original,p.read_bytes())
            with self.assertRaises(ValueError):exportar_recibo(r,Path(tmp)/'controle.xlsx')


if __name__=='__main__':unittest.main()
