from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from interface import Aplicacao


class Valor:
    def __init__(self, valor=''):self.valor=valor
    def get(self):return self.valor
    def set(self, valor):self.valor=valor


class InterfaceTests(unittest.TestCase):
    def test_botao_chama_online_sem_anexos_e_guarda_controle_cumulativo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);novo=p/'controle.xlsx';novo.write_bytes(b'arquivo ficticio de resultado')
            app=Aplicacao.__new__(Aplicacao)
            app.root=MagicMock();app.config={};app.controle=Valor();app.aba=Valor();app.status=Valor()
            app.fila=queue.Queue();app.ocupado=False;app.mostrar=MagicMock();app.ultima_pasta=None
            for nome in ['consultar','escolher','campo_controle','campo_aba','progresso','abrir']:setattr(app,nome,MagicMock())
            result={'pasta':p,'controle':novo,'completa':False,'resumo':'Consulta com pendências'}
            def thread(**kwargs):
                return SimpleNamespace(start=lambda:kwargs['target'](*kwargs['args']))
            with patch('interface.CONFIG',p/'config.json'),patch('interface.BASE',p),patch('interface.threading.Thread',side_effect=thread),patch('interface.executar_online',return_value=result) as online:
                app.iniciar();app.atualizar()
                online.assert_called_once()
                self.assertIsNone(online.call_args.args[0])
                self.assertEqual(online.call_args.args[1],p/'saidas')
                self.assertEqual(app.controle.get(),str(novo.resolve()))
                self.assertFalse(app.ocupado)
                self.assertIn('pendências',app.status.get())
                self.assertTrue((p/'config.json').is_file())


if __name__ == '__main__':unittest.main()
