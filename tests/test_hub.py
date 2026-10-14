import unittest
from unittest.mock import MagicMock,patch
from hub_agentes import HubAgentes


class HubTests(unittest.TestCase):
    def hub(self):
        h=HubAgentes.__new__(HubAgentes)
        h.root=MagicMock();h.home=MagicMock();h.admissao=MagicMock()
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

    def test_nao_fecha_durante_consulta(self):
        h=self.hub();h.monitor=MagicMock();h.monitor.ocupado=True
        with patch('hub_agentes.messagebox.showinfo') as alerta:h.fechar()
        alerta.assert_called_once();h.root.destroy.assert_not_called()
        h.monitor.ocupado=False;h.fechar();h.root.destroy.assert_called_once()

    def test_modulo_desconhecido_nao_abre(self):
        h=self.hub()
        with self.assertRaises(ValueError):h.abrir('inexistente')
        h.fabrica_monitor.assert_not_called()


if __name__=='__main__':unittest.main()
