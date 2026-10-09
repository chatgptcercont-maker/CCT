from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import consulta_online as online
import monitor
from exemplos.criar_demo import documento


class AbrangenciaTests(unittest.TestCase):
    def test_qualquer_municipio_al_sem_exigir_estado_inteiro(self):
        for local in ['Maceió/AL', 'Arapiraca/AL', 'Penedo/AL', 'Água Branca/AL',
                      'Belém/AL', 'São José da Tapera/AL', 'Recife/PE e Pilar/AL']:
            for tipo in ['CONVENCAO COLETIVA DE TRABALHO',
                         'TERMO ADITIVO DE CONVENCAO COLETIVA DE TRABALHO']:
                with self.subTest(local=local, tipo=tipo):
                    dados = monitor.extrair(documento(local=local, tipo=tipo), date(2026, 10, 8))
                    self.assertIn('AL', dados['Abrangência territorial'])
        with self.assertRaises(ValueError):
            monitor.extrair(documento(local='Belém/PA'), date(2026, 10, 8))

    def test_seletor_usa_todos_disponiveis_e_aguarda_gravacao(self):
        page = MagicMock()
        page.expect_response.return_value.__enter__.return_value.value.status = 200
        page.locator.return_value.inner_text.return_value = 'Município\nUF: AL'
        online.selecionar_municipios_al(page)
        seletores = [call.args[0] for call in page.locator.call_args_list]
        self.assertIn('#chkTodosDisponiveisAbrangencia', seletores)
        self.assertNotIn('#chkTodosMunicipiosDestaInicial', seletores)
        self.assertEqual(page.expect_response.call_count, 3)

    def test_seletor_nao_aceita_outra_uf(self):
        page = MagicMock()
        page.expect_response.return_value.__enter__.return_value.value.status = 200
        page.locator.return_value.inner_text.return_value = 'Município\nUF: PE'
        with self.assertRaisesRegex(online.ConsultaIncompleta, 'não confirmou'):
            online.selecionar_municipios_al(page)

    def test_filtro_municipios_nao_adiciona_uf_em_seu_lugar(self):
        page = MagicMock()
        with patch.object(online, 'selecionar_municipios_al') as selecionar:
            online.preparar_filtros(page, date(2026, 10, 9), 'convencao', date(2026, 1, 1), area='municipios')
        selecionar.assert_called_once_with(page)
        self.assertNotIn('#btnAdicionarUF', [c.args[0] for c in page.locator.call_args_list])
        page.locator.assert_any_call('#cboUFRegistro')

    def test_uniao_das_quatro_pesquisas_nao_duplica_documento(self):
        browser = MagicMock()
        page = browser.new_context.return_value.new_page.return_value
        page.goto.return_value.status = 200
        rows = MagicMock(); rows.count.return_value = 1
        rows.nth.return_value.get_attribute.return_value = 'MR000001/2026'
        rows.nth.return_value.inner_text.return_value = 'AL000001/2026'
        vazio = MagicMock(); vazio.count.return_value = 0
        page.locator.side_effect = lambda s: rows if s == '#grdInstrumentos tr[indice]' else vazio
        dados = monitor.extrair(documento(), date(2026, 10, 8))
        item = {'registro': dados['Registro'], 'arquivo': 'documentos/demo.pdf',
                'fonte': online.URL, 'campos': dados}
        catalogo = []
        with tempfile.TemporaryDirectory() as tmp, patch.object(online, 'preparar_filtros'), \
                patch.object(online, 'pesquisar', return_value=(1, 1, 1)), \
                patch.object(online, 'salvar_instrumento', return_value=item) as salvar:
            itens, pendencias, totais = online.coletar(browser, Path(tmp), date(2026, 10, 8), [], lambda m: None, catalogo=catalogo)
        self.assertEqual(len(totais), 4)
        self.assertEqual(pendencias, [])
        self.assertEqual(len(itens), 1)
        self.assertEqual(len(catalogo), 1)
        salvar.assert_called_once()


if __name__ == '__main__':
    unittest.main()
