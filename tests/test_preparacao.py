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


if __name__ == '__main__':
    unittest.main()
