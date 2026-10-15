import unittest
from unittest.mock import MagicMock,patch
from hub_agentes import HubAgentes


class HubTests(unittest.TestCase):
    def hub(self):
        h=HubAgentes.__new__(HubAgentes)
        h.root=MagicMock();h.home=MagicMock();h.admissao=MagicMock();h.rescisao=MagicMock();h.auditor_folha=MagicMock()
        h.sero=MagicMock()
        h.monitor=None;h.tela_monitor=None;h.fabrica_monitor=MagicMock()
        return h

    def test_monitor_construido_uma_vez_e_reutilizado(self):
        h=self.hub()
        with patch('hub_agentes.tk.Frame',return_value=MagicMock()) as frame:
            h.abrir('cct');monitor=h.monitor
            h.mostrar_inicio();h.abrir('cct')
        h.fabrica_monitor.assert_called_once()
        self.assertIs(h.monitor,monitor)
        self.assertIs(h.fabrica_monitor.call_args.kwargs['container'],h.tela_monitor)
        self.assertEqual(h.fabrica_monitor.call_args.kwargs['ao_voltar'],h.mostrar_inicio)
        frame.assert_called_once()

    def test_admissao_nao_inicia_consulta(self):
        h=self.hub();h.abrir('admissao')
        h.fabrica_monitor.assert_not_called();h.admissao.pack.assert_called_once()
        h.root.title.assert_called_with('Conferência de Admissão | Cercont — Em preparação')

    def test_recibo_abre_modulo_sem_emitir_ou_calcular(self):
        h=self.hub();h.abrir('rescisao')
        h.fabrica_monitor.assert_not_called();h.rescisao.pack.assert_called_once()
        h.root.title.assert_called_with('Recibo de Rescisão Avulsa | Cercont — Valores manuais')

    def test_modulo_recibo_e_reutilizado_ao_voltar_ao_hub(self):
        h=self.hub();h.rescisao=None
        with patch('modulo_rescisao.ModuloRescisao') as modulo:
            h.abrir('rescisao');instancia=h.modulo_rescisao
            h.mostrar_inicio();h.abrir('rescisao')
        modulo.assert_called_once()
        self.assertIs(h.modulo_rescisao,instancia)

    def test_nao_fecha_durante_consulta(self):
        h=self.hub();h.monitor=MagicMock();h.monitor.ocupado=True
        with patch('hub_agentes.messagebox.showinfo') as alerta:h.fechar()
        alerta.assert_called_once();h.root.destroy.assert_not_called()
        h.monitor.ocupado=False;h.fechar();h.root.destroy.assert_called_once()

    def test_modulo_desconhecido_nao_abre(self):
        h=self.hub()
        with self.assertRaises(ValueError):h.abrir('inexistente')
        h.fabrica_monitor.assert_not_called()

    def test_seletor_abre_sero_e_retorna_ao_hub(self):
        from hub_agentes import AGENTES
        h=self.hub();h.seletor_modulo=MagicMock()
        h.seletor_modulo.current.return_value=next(i for i,a in enumerate(AGENTES) if a['id']=='sero')
        h.abrir_selecionado()
        h.sero.pack.assert_called_once();h.fabrica_monitor.assert_not_called()
        h.root.title.assert_called_with('Regularização de Obras (SERO) | Cercont — A configurar')
        h.mostrar_inicio();h.home.pack.assert_called_once()
        self.assertGreaterEqual(h.sero.pack_forget.call_count,2)

    def test_seletor_sem_selecao_nao_abre_modulo(self):
        h=self.hub();h.seletor_modulo=MagicMock();h.seletor_modulo.current.return_value=-1
        h.abrir_selecionado();h.fabrica_monitor.assert_not_called();h.sero.pack.assert_not_called()


if __name__=='__main__':unittest.main()
