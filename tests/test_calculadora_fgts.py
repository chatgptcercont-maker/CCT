import unittest
from decimal import Decimal
from unittest.mock import MagicMock,patch

from calculadora_fgts import conferir_dados,exige_regra,REGRAS
from hub_agentes import HubAgentes


class FGTSTests(unittest.TestCase):
    def dados(self):
        return {'base':'Trabalhadores','competencia':'01/2026','pagamento':'14/10/2026','folha':'1.250,50'}

    def test_base_ambos_exige_valores_separados(self):
        d=self.dados();d.update(base='Ambos',aprendiz='500,00')
        r=conferir_dados(d)
        self.assertEqual(r['valores'],{'folha':Decimal('1250.50'),'aprendiz':Decimal('500.00')})
        self.assertNotIn('total_atualizado',r)
        d['aprendiz']=''
        with self.assertRaises(ValueError):conferir_dados(d)

    def test_base_inativa_nao_participa_da_conferencia(self):
        d=self.dados();d.update(base='Aprendizes',aprendiz='100',folha='inválido')
        self.assertEqual(conferir_dados(d)['valores'],{'aprendiz':Decimal('100.00')})

    def test_regra_historica_obrigatoria_apenas_no_intervalo(self):
        for comp in ('10/2001','01/2002','12/2006'):
            self.assertTrue(exige_regra(comp))
            d=self.dados();d['competencia']=comp
            with self.assertRaises(ValueError):conferir_dados(d)
            for regra in REGRAS:
                d['regra']=regra;self.assertEqual(conferir_dados(d)['regra'],regra)
        for comp in ('09/2001','01/2007'):self.assertFalse(exige_regra(comp))

    def test_entradas_invalidas_nao_produzem_resultado(self):
        for campo,valor in [('competencia','13/2026'),('competencia','01/1994'),
            ('competencia','1/2026'),('pagamento','31/02/2026'),('pagamento','01/12/2025'),
            ('folha','-1'),('folha','0'),('folha','1,001'),('base','')]:
            with self.subTest(campo=campo,valor=valor):
                d=self.dados();d[campo]=valor
                with self.assertRaises(ValueError):conferir_dados(d)

    def test_troca_calculadora_preserva_formulario_fgts_na_sessao(self):
        h=HubAgentes.__new__(HubAgentes)
        for nome in ('seletor_calculadora','detalhe_calculadora_widget','detalhe_calculadora','area_fgts'):
            setattr(h,nome,MagicMock())
        h.formulario_fgts=None;h.seletor_calculadora.current.return_value=3
        with patch('calculadora_fgts.FormularioFGTS') as fabrica:
            h.selecionar_calculadora();form=h.formulario_fgts
            h.seletor_calculadora.current.return_value=0;h.selecionar_calculadora()
            h.area_fgts.pack_forget.assert_called_once()
            h.seletor_calculadora.current.return_value=3;h.selecionar_calculadora()
        fabrica.assert_called_once_with(h.area_fgts)
        self.assertIs(h.formulario_fgts,form)


if __name__=='__main__':unittest.main()
