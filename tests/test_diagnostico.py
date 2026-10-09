from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import diagnosticar_mediador as d
import monitor


class DiagnosticoTests(unittest.TestCase):
    def test_origem_tunel(self):
        self.assertEqual(d.classificar_erro('net::ERR_TUNNEL_CONNECTION_FAILED'), 'BLOQUEIO_DO_TUNEL_PROXY')
        self.assertEqual(d.classificar_erro('Tunnel connection failed: 403 Forbidden'), 'BLOQUEIO_DO_TUNEL_PROXY')
        self.assertEqual(d.classificar_erro('HTTP 403 Forbidden'), 'FALHA_DE_ACESSO')
        self.assertEqual(d.classificar_erro('net::ERR_CERT_AUTHORITY_INVALID'), 'ERRO_TLS')

    def test_nao_registra_parametros_ou_credenciais(self):
        self.assertEqual(d.endereco_sem_parametros('https://usuario:segredo@exemplo.gov.br/documento?token=segredo#sessao'), 'https://exemplo.gov.br/documento')

    def test_proxy_configurado_sem_bypass(self):
        with patch.dict('os.environ', {'HTTPS_PROXY':'http://usuario:senha%40local@proxy.test:8080'}, clear=True):
            p=d.proxy_do_ambiente()
            self.assertEqual(p['server'],'http://proxy.test:8080')
            self.assertEqual(p['password'],'senha@local')
        with patch.dict('os.environ', {}, clear=True):
            self.assertIsNone(d.proxy_do_ambiente())

    def test_falha_gera_relatorios_sem_falsos_resultados(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'out'
            with patch.object(d,'proxy_do_ambiente',side_effect=ValueError('configuração inválida')):
                resultado=d.investigar(p)
            self.assertFalse(resultado['consulta_validada'])
            self.assertIsNone(resultado['instrumentos_coletados'])
            self.assertTrue((p/'diagnostico_mediador.json').exists())
            self.assertIn('NÃO CONCLUÍDA',(p/'resumo_convencoes_AL.txt').read_text())
            self.assertFalse((p/'controle_convencoes_AL.xlsx').exists())
            with self.assertRaises(FileExistsError): d.investigar(p)

    def test_endereco_oficial_atualizado(self):
        self.assertEqual(monitor.CONSULTA,d.URL)
        self.assertTrue(monitor.fonte_oficial(d.URL))


if __name__ == '__main__': unittest.main()
