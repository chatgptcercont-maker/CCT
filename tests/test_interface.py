from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from interface import Aplicacao, ordenar_resultados


class Valor:
    def __init__(self, valor=''):self.valor=valor
    def get(self):return self.valor
    def set(self, valor):self.valor=valor


class InterfaceTests(unittest.TestCase):
    def test_menu_consultas_abre_painel(self):
        app=self.app_sem_tela()
        app.menu={nome:MagicMock() for nome in ['Início','Consultas','Configurações','Ajuda']}
        app.navegar('Consultas')
        app.exibir_painel.assert_called_once()
        app.menu['Consultas'].configure.assert_called_with(background='#226c5c')
        app.root.update_idletasks.assert_not_called()

    def test_resultados_ordenados_por_data_sem_mover_pendencias(self):
        linhas=['Novos instrumentos: 3',
                'AL000002/2026 | Convenção | registro em 31/01/2026 | fonte',
                'SRT00001/2026 | Aditivo | registro em 02/10/2026 | fonte',
                'AL000001/2025 | Convenção | registro em 31/12/2025 | fonte',
                'Pendências: HTTP 403']
        resultado=ordenar_resultados('\n'.join(linhas)).splitlines()
        self.assertEqual(resultado,[linhas[0],linhas[3],linhas[1],linhas[2],linhas[4]])
        self.assertEqual(ordenar_resultados('Consulta com pendências.\nNenhum documento.'),'Consulta com pendências.\nNenhum documento.')

    def app_sem_tela(self):
        app=Aplicacao.__new__(Aplicacao)
        app.root=MagicMock();app.logs=MagicMock();app.texto=MagicMock();app.config={}
        app.percentual=Valor(0);app.indicador=Valor();app.status=Valor()
        app.fila=queue.Queue();app.ocupado=True;app.abas_resultados=MagicMock()
        app.campo_periodo=MagicMock();app.exibir_painel=MagicMock()
        for nome in ['consultar','escolher','campo_controle','campo_aba','abrir']:
            setattr(app,nome,MagicMock())
        return app

    def test_percentual_usa_contagem_real_e_aguarda_total(self):
        app=self.app_sem_tela()
        app.atualizar_percentual({'total':None})
        self.assertEqual(app.percentual.get(),0)
        self.assertIn('aguardando',app.indicador.get())
        app.atualizar_percentual({'total':8,'examinados':3})
        self.assertEqual(app.percentual.get(),37.5)
        self.assertIn('3 de 8',app.indicador.get())

    def test_mensagens_com_horario_e_erros_nao_declaram_sucesso(self):
        app=self.app_sem_tela()
        app.fila.put(('progresso','Pesquisando convenções'))
        app.fila.put(('progresso',{'total':10,'examinados':2}))
        app.fila.put(('erro','HTTP 403: consulta recusada'))
        app.atualizar()
        self.assertFalse(app.ocupado)
        self.assertEqual(app.percentual.get(),20)
        self.assertIn('interrompida',app.indicador.get())
        linhas=[c.args[1] for c in app.logs.insert.call_args_list]
        self.assertTrue(any('Pesquisando convenções' in s for s in linhas))
        self.assertTrue(any('HTTP 403' in s for s in linhas))
        self.assertRegex(linhas[0],r'^\[\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\]')

    def test_escolha_planilha_e_abertura_resultados(self):
        app=self.app_sem_tela();app.controle=Valor()
        with patch('interface.filedialog.askopenfilename',return_value='C:/controle.xlsx'):
            app.selecionar_controle()
        self.assertEqual(app.controle.get(),'C:/controle.xlsx')
        with tempfile.TemporaryDirectory() as tmp:
            app.ultima_pasta=Path(tmp)
            with patch('interface.os.name','nt'),patch('interface.os.startfile',create=True) as abrir:
                app.abrir_resultados()
            abrir.assert_called_once_with(Path(tmp).resolve())

    def test_painel_historico_nao_troca_controle_selecionado(self):
        app=self.app_sem_tela();app.dados_painel=None;app.controle=Valor('controle-original.xlsx')
        dados={'documentos':[],'pendencias':[],'completa':False,'consultada_em':'Não confirmado'}
        with patch('interface.filedialog.askdirectory',return_value='consulta/resultado'), \
                patch('analise_resultados.localizar_consulta',side_effect=ValueError('Sem consulta')), \
                patch('interface.salvar_config'), \
                patch('analise_resultados.carregar_consulta',return_value=dados) as carregar, \
                patch('painel_resultados.PainelResultados') as painel:
            Aplicacao.exibir_painel(app)
        carregar.assert_called_once_with('consulta/resultado')
        painel.assert_called_once()
        self.assertEqual(app.controle.get(),'controle-original.xlsx')

    def test_reabertura_recupera_ultima_consulta_sem_pedir_pasta(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta=Path(tmp)/'online_20261014_120000_id';(pasta/'resultado').mkdir(parents=True)
            (pasta/'coleta_automatica.json').write_text('{"consulta_completa":false,"instrumentos":[]}')
            app=self.app_sem_tela();app.dados_painel=None;app.controle=Valor('controle-original.xlsx')
            app.config={'ultima_consulta':str(pasta/'resultado')}
            with patch('interface.filedialog.askdirectory') as escolher,patch('interface.salvar_config') as salvar, \
                    patch('painel_resultados.PainelResultados') as painel:
                Aplicacao.exibir_painel(app)
            escolher.assert_not_called();painel.assert_called_once();salvar.assert_called_once()
            self.assertEqual(app.dados_painel['pasta'],str(pasta/'resultado'))
            self.assertEqual(app.controle.get(),'controle-original.xlsx')

    def test_botao_chama_online_sem_anexos_e_guarda_controle_cumulativo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);novo=p/'controle.xlsx';novo.write_bytes(b'arquivo ficticio de resultado')
            app=Aplicacao.__new__(Aplicacao)
            app.root=MagicMock();app.config={};app.controle=Valor();app.aba=Valor();app.status=Valor()
            app.periodo=Valor('Ano de 2026');app.campo_periodo=MagicMock()
            app.logs=MagicMock();app.percentual=Valor(0);app.indicador=Valor();app.abas_resultados=MagicMock()
            app.exibir_painel=MagicMock()
            app.fila=queue.Queue();app.ocupado=False;app.mostrar=MagicMock();app.ultima_pasta=None
            for nome in ['consultar','escolher','campo_controle','campo_aba','progresso','abrir']:setattr(app,nome,MagicMock())
            result={'pasta':p,'controle':novo,'completa':False,'resumo':'Consulta com pendências'}
            def thread(**kwargs):
                return SimpleNamespace(start=lambda:kwargs['target'](*kwargs['args']))
            with patch('interface.CONFIG',p/'config.json'),patch('interface.BASE',p),patch('interface.threading.Thread',side_effect=thread),patch('interface.executar_online',return_value=result) as online:
                app.iniciar();app.atualizar()
                online.assert_called_once()
                self.assertIsNone(online.call_args.args[0])
                self.assertEqual(online.call_args.kwargs['ano'],2026)
                self.assertEqual(online.call_args.args[1],p/'saidas')
                self.assertEqual(app.controle.get(),str(novo.resolve()))
                self.assertFalse(app.ocupado)
                self.assertIn('pendências',app.status.get())
                self.assertTrue((p/'config.json').is_file())
                app.periodo.set('Ontem')
                online.reset_mock()
                app.iniciar();app.atualizar()
                self.assertIsNone(online.call_args.kwargs['ano'])
                self.assertTrue(online.call_args.kwargs['ontem'])


if __name__ == '__main__':unittest.main()
