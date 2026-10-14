from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import preparar_monitor as setup


class PreparacaoTests(unittest.TestCase):
    def estrutura(self, pasta):
        base = Path(pasta)
        (base / 'requirements.txt').write_text('pacote-ficticio==1\n')
        python = base / '.venv' / 'Scripts' / 'python.exe'
        python.parent.mkdir(parents=True)
        python.touch()
        return base

    def test_primeira_preparacao_instala_e_marca_sem_baixar_navegador_windows(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.sys, 'platform', 'win32'), \
                patch.object(setup.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            base = self.estrutura(tmp)
            setup.preparar(base)
            self.assertTrue((base / '.venv/.monitor_requisitos.sha256').is_file())
            comandos = [c.args[0] for c in run.call_args_list]
            self.assertTrue(any('pip' in c for c in comandos))
            self.assertFalse(any('chromium' in c for c in comandos))

    def test_reabertura_nao_reinstala(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.sys, 'platform', 'win32'), \
                patch.object(setup.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            base = self.estrutura(tmp)
            setup.preparar(base)
            run.reset_mock()
            setup.preparar(base)
            self.assertEqual(run.call_count, 1)
            self.assertNotIn('pip', run.call_args.args[0])

    def test_falha_instalacao_nao_marca_como_pronto(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.sys, 'platform', 'win32'), \
                patch.object(setup.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'pip')):
            base = self.estrutura(tmp)
            with self.assertRaises(subprocess.CalledProcessError):
                setup.preparar(base)
            self.assertFalse((base / '.venv/.monitor_requisitos.sha256').exists())

    def test_windows_abre_pythonw_sem_aguardar_interface(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.sys,'platform','win32'), \
                patch.object(setup.subprocess,'Popen') as popen, patch.object(setup.subprocess,'run') as run:
            base=self.estrutura(tmp);python=base/'.venv/Scripts/python.exe'
            python.with_name('pythonw.exe').touch()
            self.assertEqual(setup.abrir_interface(python,base),0)
            popen.assert_called_once();run.assert_not_called()
            self.assertEqual(popen.call_args.args[0],[str(python.with_name('pythonw.exe')),str(base/'interface.py')])
            self.assertEqual(popen.call_args.kwargs['creationflags'],0x208)
            self.assertEqual(len(list((base/'saidas').glob('inicializacao_*.log'))),1)

    def test_pythonw_ausente_informa_erro_sem_abrir_outro_console(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.sys,'platform','win32'), \
                patch.object(setup.subprocess,'Popen') as popen:
            base=self.estrutura(tmp)
            with self.assertRaisesRegex(RuntimeError,'pythonw.exe'):
                setup.abrir_interface(base/'.venv/Scripts/python.exe',base)
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
