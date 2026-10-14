from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from pypdf import PdfReader
from exemplos.criar_demo import documento, pdf_ficticio
import analise_resultados as analise
from painel_resultados import PainelResultados


def exemplo(numero='AL000001/2026', data='08/10/2026', percentual='5%'):
    texto=documento(numero=numero,data=data).replace('CLAUSULA PRIMEIRA',
        'SINDICATO DAS EMPRESAS FICTICIAS,\nCNPJ n. 11.111.111/0001-11\n'
        'SINDICATO DOS EMPREGADOS FICTICIOS,\nCNPJ n. 22.222.222/0001-22\nCLAUSULA PRIMEIRA')
    texto=texto.replace('Abrangencia territorial em Maceio/AL.',
        'A convencao abrangerá a(s) categoria(s) Trabalhadores ficticios, com abrangencia territorial em Maceio/AL.')
    texto=texto.replace('Dados ficticios para testes.',
        'A vigencia será no periodo de 01 de janeiro de 2026 a 31 de dezembro de 2026 e a data-base da categoria em 01 de janeiro.')
    return texto+f'''\nCLAUSULA TERCEIRA - REAJUSTE SALARIAL
Os salarios serão reajustados em {percentual}. Admitidos após janeiro terão reajuste proporcional.
CLAUSULA QUARTA - PISO SALARIAL
O piso será R$ 2.000,00.
CLAUSULA QUINTA - CONTRIBUICAO ASSISTENCIAL DOS EMPREGADOS
Será descontado 1% mensal. Oposição escrita em 10 dias. Isentos os empregados nas condições desta cláusula.
CLAUSULA SEXTA - CONTRIBUICAO ASSISTENCIAL PATRONAL
Será cobrado R$ 100,00 anual. Pagamento em 30 de abril.
CLAUSULA SETIMA - BENEFICIO FICTICIO
Vale alimentação de R$ 30,00.
CLAUSULA OITAVA - CONTRIBUICAO SINDICAL
Não classificar esta regra como assistencial.
'''


class ResultadosTests(unittest.TestCase):
    def test_ordem_crescente_pelo_numero_do_registro(self):
        docs=[{'Registro':'SRT00003/2026'},{'Registro':'AL000003/2026'},
              {'Registro':'AL000001/2026'},{'Registro':'AL000002/2026'}]
        ordenados=analise.ordenar_por_registro(docs)
        self.assertEqual([d['Registro'] for d in ordenados],['AL000001/2026','AL000002/2026','AL000003/2026','SRT00003/2026'])
        self.assertEqual(docs[0]['Registro'],'SRT00003/2026')

    def test_ordem_alfabetica_categoria_sem_acentos_e_sem_alterar_origem(self):
        docs=[{'categoria':'Zeladores','Registro':'AL000001/2026'},
              {'categoria':None,'Registro':'AL000002/2026'},
              {'categoria':'Água e saneamento','Registro':'AL000003/2026'},
              {'categoria':'Comércio','Registro':'AL000004/2026'}]
        ordenados=analise.ordenar_por_categoria(docs)
        self.assertEqual([d['Registro'] for d in ordenados],['AL000003/2026','AL000004/2026','AL000001/2026','AL000002/2026'])
        self.assertEqual(docs[0]['categoria'],'Zeladores')

    def ler(self,base,texto=None,nome='documento.pdf'):
        p=base/nome;pdf_ficticio(p,texto or exemplo())
        return analise.ler_documento(p,hoje=date(2026,10,12))

    def test_identificacao_clausulas_e_resumo_com_fontes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=self.ler(Path(tmp))
            self.assertEqual(d['vigencia_inicio'],'2026-01-01')
            self.assertEqual(d['categoria'],'Trabalhadores ficticios')
            self.assertEqual(d['patronal']['cnpj'],'11.111.111/0001-11')
            self.assertIn('Não confirmada',d['situacao'])
            grupos=analise.resumo_executivo(d)
            self.assertEqual([c['numero'] for c in grupos['Reajuste salarial']],['TERCEIRA'])
            self.assertEqual(len(grupos['Empregados']),1);self.assertEqual(len(grupos['Patronal']),1)
            cl=grupos['Empregados'][0]
            self.assertEqual(cl['pagina'],1);self.assertIn('Oposição',cl['texto'])
            self.assertTrue(any(p['titulo']=='Oposição' for p in analise.pontos_resumo(cl)))
            self.assertNotIn('QUARTA',' '.join(c['numero'] for v in grupos.values() for c in v))
            self.assertNotIn('OITAVA',' '.join(c['numero'] for v in grupos.values() for c in v))

    def test_ausencia_e_destinacao_ambigua_nao_sao_inventadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=self.ler(Path(tmp),exemplo().replace('ASSISTENCIAL DOS EMPREGADOS','ASSISTENCIAL').replace('ASSISTENCIAL PATRONAL','SOCIAL PATRONAL'))
            r=analise.resumo_executivo(d)
            self.assertEqual(r['Empregados'],[]);self.assertEqual(r['Patronal'],[])
            self.assertEqual(len(r['Destinação não confirmada']),1)

    def test_pesquisa_categoria_municipio_cnpj_e_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=self.ler(Path(tmp))
            for termo in ['maceió','trabalhadores ficticios','11111111000111','AL000001','EMPREGADOS FICTICIOS']:
                self.assertEqual(analise.pesquisar([d],termo),[d])
            self.assertEqual(analise.pesquisar([d],'Recife'),[])

    def test_carregamento_preserva_pdf_e_rejeita_path_externo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);(raiz/'documentos').mkdir();(raiz/'resultado').mkdir()
            d=self.ler(raiz/'documentos');antes=Path(d['caminho']).read_bytes()
            m={'consulta_completa':False,'instrumentos':[{'registro':d['Registro'],'arquivo':'documentos/documento.pdf','fonte':''},
                {'registro':'AL000002/2026','arquivo':'../externo.pdf'}]}
            (raiz/'coleta_automatica.json').write_text(json.dumps(m))
            c=analise.carregar_consulta(raiz/'resultado')
            self.assertEqual(len(c['documentos']),1);self.assertEqual(len(c['pendencias']),1)
            self.assertFalse(c['completa']);self.assertEqual(Path(d['caminho']).read_bytes(),antes)

    def test_comparativo_exige_documentos_anteriores_compatíveis(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);atual=self.ler(p)
            anterior=self.ler(p,exemplo('AL000099/2025','08/10/2025','3%'),'anterior.pdf')
            dif=analise.comparar(atual,anterior)
            self.assertTrue(any('5%' in x['diferencas'] and '3%' in x['diferencas'] for x in dif))
            with self.assertRaises(ValueError):analise.comparar(atual,atual)
            anterior['categoria']='Outra categoria'
            with self.assertRaises(ValueError):analise.comparar(atual,anterior)

    def test_exportacao_pdf_nao_altera_origem_e_reproduz_valores(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);d=self.ler(p);antes=Path(d['caminho']).read_bytes()
            c={'documentos':[d],'consultada_em':'12/10/2026 10:00','pendencias':[]}
            destino=analise.exportar_pdf(d,c,p/'resumo.pdf')
            texto='\n'.join(pg.extract_text() for pg in PdfReader(destino).pages)
            self.assertIn('5%',texto);self.assertIn('R$ 100,00',texto)
            self.assertIn('QUINTA',texto);self.assertIn('Oposição',texto)
            self.assertNotIn('R$ 2.000,00',texto)
            self.assertEqual(Path(d['caminho']).read_bytes(),antes)
            with self.assertRaises(ValueError):analise.exportar_pdf(d,c,d['caminho'])

    def test_detalhes_expandem_recolhem_e_abrem_pdf_na_pagina(self):
        painel=PainelResultados.__new__(PainelResultados)
        frame=MagicMock();botao=MagicMock();painel.secoes={'Salários':(MagicMock(),frame,botao)}
        frame.winfo_manager.return_value=''
        painel.expandir(frame);frame.pack.assert_called_once()
        frame.winfo_manager.return_value='pack';painel.expandir(frame);frame.pack_forget.assert_called_once()
        painel.janela_texto=MagicMock()
        c={'numero':'TERCEIRA','titulo':'Reajuste','texto':'Texto integral com exceções','pagina':2,'pagina_final':3,'arquivo':'origem.pdf','registro':'AL000001/2026'}
        painel.ver_clausula(c);self.assertEqual(painel.janela_texto.call_args.args[1],c['texto'])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'doc.pdf';p.touch()
            with patch('painel_resultados.webbrowser.open',return_value=True) as abrir:
                painel.abrir_arquivo(p,2)
            abrir.assert_called_once_with(p.as_uri()+'#page=2')

    def test_nova_consulta_volta_sem_modificar_historico(self):
        painel=PainelResultados.__new__(PainelResultados);painel.root=MagicMock();painel.voltar=MagicMock()
        painel.nova_consulta();painel.voltar.assert_called_once();painel.root.destroy.assert_not_called()

    def test_clausula_continuada_mantem_as_paginas_reais(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'documento.pdf';p.write_bytes(b'fixture de leitura')
            pagina1=documento()+'\nCLAUSULA TERCEIRA - REAJUSTE SALARIAL\nReajuste de 5%.'
            pagina2='Continuação: ressalvadas as condições anteriores.\nCLAUSULA QUARTA - BENEFICIOS\nBeneficio ficticio.'
            leitor=SimpleNamespace(is_encrypted=False,pages=[SimpleNamespace(extract_text=lambda:pagina1),SimpleNamespace(extract_text=lambda:pagina2)])
            with patch.object(analise,'PdfReader',return_value=leitor):d=analise.ler_documento(p,hoje=date(2026,10,12))
            salario=next(c for c in d['clausulas'] if c['numero']=='TERCEIRA')
            self.assertEqual((salario['pagina'],salario['pagina_final']),(1,2))
            self.assertIn('ressalvadas',salario['texto'])
            beneficio=next(c for c in d['clausulas'] if c['numero']=='QUARTA')
            self.assertEqual(beneficio['pagina'],2)

    def test_exportacao_nao_substitui_planilha(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);d=self.ler(p);planilha=p/'controle.xlsx';planilha.write_bytes(b'original')
            c={'documentos':[d],'consultada_em':'Não confirmado','pendencias':[]}
            with self.assertRaises(ValueError):analise.exportar_pdf(d,c,planilha)
            self.assertEqual(planilha.read_bytes(),b'original')

    def test_aditivo_so_relacionado_por_referencia_documental_explicita(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);(raiz/'documentos').mkdir();(raiz/'resultado').mkdir()
            base=exemplo().replace('CLAUSULA PRIMEIRA','NUMERO DO PROCESSO: 12345.000001/2026-00\nCLAUSULA PRIMEIRA',1)
            aditivo=exemplo('AL000002/2026').replace('CONVENCAO COLETIVA DE TRABALHO','TERMO ADITIVO DE CONVENCAO COLETIVA DE TRABALHO',1)
            aditivo=aditivo.replace('CLAUSULA PRIMEIRA','NUMERO DO PROCESSO DA CONVENCAO COLETIVA PRINCIPAL: 12345.000001/2026-00\nCLAUSULA PRIMEIRA',1)
            self.ler(raiz/'documentos',base,'base.pdf');self.ler(raiz/'documentos',aditivo,'aditivo.pdf')
            manifest={'consulta_completa':True,'instrumentos':[{'registro':'AL000001/2026','arquivo':'documentos/base.pdf'},
                {'registro':'AL000002/2026','arquivo':'documentos/aditivo.pdf'}]}
            (raiz/'coleta_automatica.json').write_text(json.dumps(manifest))
            c=analise.carregar_consulta(raiz/'resultado')
            self.assertEqual(c['documentos'][0]['aditivos_relacionados'],['AL000002/2026'])

    def test_consulta_salva_carrega_resumos_pela_raiz_execucao_ou_resultado(self):
        with tempfile.TemporaryDirectory() as tmp:
            saidas=Path(tmp);raiz=saidas/'online_20261014_120000_id'
            (raiz/'documentos').mkdir(parents=True);(raiz/'resultado').mkdir()
            d=self.ler(raiz/'documentos');antes=Path(d['caminho']).read_bytes()
            m={'consulta_completa':True,'instrumentos':[{'registro':d['Registro'],'arquivo':'documentos/documento.pdf'}]}
            (raiz/'coleta_automatica.json').write_text(json.dumps(m))
            for pasta in [saidas,raiz,raiz/'resultado']:
                c=analise.carregar_consulta(pasta)
                self.assertEqual(len(c['documentos']),1)
                resumo=analise.resumo_executivo(c['documentos'][0])
                self.assertIn('5%',resumo['Reajuste salarial'][0]['texto'])
                self.assertEqual(c['pasta'],str(raiz/'resultado'))
            self.assertEqual(Path(d['caminho']).read_bytes(),antes)


if __name__=='__main__':unittest.main()
