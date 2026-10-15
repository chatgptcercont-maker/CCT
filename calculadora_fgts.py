"""Entrada local para FGTS em atraso; não estima coeficientes ausentes."""
from datetime import date, datetime
import queue
import threading
import re

from recibo_rescisao import valor_monetario

BASES = ('Trabalhadores', 'Aprendizes', 'Ambos')
REGRAS = (
    'Simples Federal — faturamento anual até R$ 1.200.000,00',
    'Empregador doméstico',
    'Produtor rural pessoa física — faturamento anual até R$ 1.200.000,00',
    'Nenhum',
)
REGIMES=('SEFIP/GRF','FGTS Digital','eSocial doméstico')


def competencia_valida(texto):
    texto=str(texto).strip()
    if not re.fullmatch(r'(0[1-9]|1[0-2])/\d{4}',texto):
        raise ValueError('Informe a competência em MM/AAAA.')
    data=datetime.strptime(texto,'%m/%Y').date()
    if data.year<1995:raise ValueError('O formulário de referência abrange competências a partir de 1995.')
    return data


def exige_regra(competencia):
    return date(2001,10,1)<=competencia_valida(competencia)<=date(2006,12,1)


def conferir_dados(dados):
    base=dados.get('base','')
    if base not in BASES:raise ValueError('Selecione Trabalhadores, Aprendizes ou Ambos.')
    competencia=competencia_valida(dados.get('competencia',''))
    pagamento=str(dados.get('pagamento','')).strip()
    if not re.fullmatch(r'\d{2}/\d{2}/\d{4}',pagamento):
        raise ValueError('Informe a data do pagamento em DD/MM/AAAA.')
    try:pagamento=datetime.strptime(pagamento,'%d/%m/%Y').date()
    except ValueError as exc:raise ValueError('Data de pagamento inválida.') from exc
    if pagamento<competencia:raise ValueError('O pagamento não pode ser anterior à competência.')
    regra=dados.get('regra','') if exige_regra(dados['competencia']) else ''
    if exige_regra(dados['competencia']) and regra not in REGRAS:
        raise ValueError('Selecione a regra de preenchimento para competências de 10/2001 a 12/2006.')
    valores={}
    for campo,ativo in [('folha',base in ('Trabalhadores','Ambos')),
                        ('aprendiz',base in ('Aprendizes','Ambos'))]:
        if ativo:
            valor=valor_monetario(dados.get(campo,''))
            if valor<=0:raise ValueError('Informe um valor de folha maior que zero para cada base selecionada.')
            valores[campo]=valor
    return {'base':base,'competencia':competencia,'pagamento':pagamento,
            'regra':regra,'valores':valores,'razao_social':str(dados.get('razao_social','')).strip(),
            'email':str(dados.get('email','')).strip()}


def calcular_online(entrada,cliente=None):
    from coeficientes_fgts import ClienteCaixa,calcular_com_coeficiente
    d=conferir_dados(entrada)
    if entrada.get('regime')!='SEFIP/GRF':
        raise ValueError('Esta tabela calcula recolhimento mensal pelo SEFIP/GRF. FGTS Digital e eSocial doméstico não são atendidos.')
    if d['competencia']>=date(2024,3,1) and entrada.get('excecao_sefip') is not True:
        raise ValueError('Desde 03/2024, use FGTS Digital. Para uma exceção legal que permanece no SEFIP (administração pública ou códigos 650/660), confirme o enquadramento antes de simular.')
    if entrada.get('suspensao') is not True:
        raise ValueError('Confirme que a competência não possui suspensão ou prorrogação especial do vencimento.')
    consulta=(cliente or ClienteCaixa()).consultar(d['competencia'].strftime('%m/%Y'),d['pagamento'])
    return calcular_com_coeficiente(d,consulta)


class FormularioFGTS:
    """Formulário independente de serviços, cookies ou credenciais da Econet."""
    def __init__(self,parent):
        import tkinter as tk
        from tkinter import ttk
        self.tk=tk;self.ttk=ttk
        self.ocupado=False;self.fila=queue.Queue()
        self.root=tk.Frame(parent,background='white')
        canvas=tk.Canvas(self.root,background='white',highlightthickness=0)
        barra=ttk.Scrollbar(self.root,command=canvas.yview);barra.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=barra.set)
        area=tk.Frame(canvas,background='white',padx=16,pady=12)
        janela=canvas.create_window(0,0,window=area,anchor='nw')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(janela,width=e.width))
        area.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        self.root.winfo_toplevel().bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120),'units') if self.root.winfo_ismapped() and not isinstance(e.widget,ttk.Combobox) else None,add='+')
        ttk.Label(area,text='FGTS — Recolhimento em atraso',style='Title.TLabel').pack(anchor='w',pady=(0,8))
        aviso=ttk.Label(area,text='Consulta automática dos coeficientes oficiais da CAIXA — recolhimento mensal SEFIP/GRF. '
            'Nenhuma remuneração, razão social ou e-mail é enviada à internet. Não emite guia.',style='Card.TLabel',wraplength=650)
        aviso.pack(fill='x',pady=(0,12))
        self.campos={};self.grupos={}
        nomes=[('base','Base do FGTS *'),('competencia','Competência · MM/AAAA *'),
               ('regra','Regra histórica · competências de 10/2001 a 12/2006 *'),
               ('regime','Regime de recolhimento *'),
               ('razao_social','Razão social · opcional'),('email','E-mail · opcional, apenas local'),
               ('pagamento','Data de pagamento · DD/MM/AAAA *'),
               ('folha','Valor da folha — trabalhadores *'),('aprendiz','Valor da folha — aprendizes *')]
        for campo,nome in nomes:
            grupo=tk.Frame(area,background='white');self.grupos[campo]=grupo
            grupo.pack(fill='x',pady=3)
            ttk.Label(grupo,text=nome,style='Card.TLabel').pack(anchor='w')
            var=tk.StringVar();self.campos[campo]=var
            if campo in ('base','regra','regime'):
                entrada=ttk.Combobox(grupo,textvariable=var,state='readonly',values={'base':BASES,'regra':REGRAS,'regime':REGIMES}[campo])
            else:entrada=ttk.Entry(grupo,textvariable=var)
            entrada.pack(fill='x',pady=(2,0))
        self.campos['regime'].set('SEFIP/GRF')
        self.excecao_sefip=tk.BooleanVar(value=False)
        self.sem_suspensao=tk.BooleanVar(value=False)
        confirmacoes=[]
        for texto,var in [('A partir de 03/2024: confirmo enquadramento em exceção que permanece no SEFIP.',self.excecao_sefip),
                          ('Conferi que não há suspensão ou prorrogação especial do vencimento para esta competência.',self.sem_suspensao)]:
            check=tk.Checkbutton(area,text=texto,variable=var,background='white',activebackground='white',
                foreground='#194e5a',font=('Segoe UI',10),wraplength=600,justify='left',anchor='w')
            check.pack(anchor='w',pady=4);confirmacoes.append(check)
        # Campos inativos ficam desabilitados e nunca participam da conferência.
        self.campos['base'].trace_add('write',self.atualizar_campos)
        self.campos['competencia'].trace_add('write',self.atualizar_campos)
        acoes=tk.Frame(area,background='white');acoes.pack(fill='x',pady=12)
        ttk.Button(acoes,text='Conferir dados',style='Primary.TButton',command=self.conferir).pack(side='left')
        self.botao_calcular=ttk.Button(acoes,text='Buscar coeficiente e calcular',command=self.calcular)
        self.botao_calcular.pack(side='left',padx=8)
        ttk.Button(acoes,text='Limpar',command=self.limpar).pack(side='left')
        self.resultado=tk.StringVar(value='Preencha os dados para conferência. Nenhum valor atualizado foi calculado.')
        for var in (self.excecao_sefip,self.sem_suspensao):
            var.trace_add('write',lambda *args:self.resultado.set('Enquadramento alterado. Calcule novamente.'))
        for campo,var in self.campos.items():
            if campo not in ('base','competencia'):
                var.trace_add('write',lambda *args:self.resultado.set('Dados alterados. Confira novamente; nenhum valor atualizado foi calculado.'))
        resultado=ttk.Label(area,textvariable=self.resultado,style='Card.TLabel',wraplength=650,justify='left')
        resultado.pack(fill='x',pady=(0,12))
        area.bind('<Configure>',lambda e:[l.configure(wraplength=max(200,e.width-32)) for l in (aviso,resultado,*confirmacoes)],add='+')
        self.atualizar_campos()

    def atualizar_campos(self,*args):
        base=self.campos['base'].get()
        try:regra=exige_regra(self.campos['competencia'].get())
        except ValueError:regra=False
        ativos={'regra':regra,'folha':base in ('Trabalhadores','Ambos'),'aprendiz':base in ('Aprendizes','Ambos')}
        for campo,ativo in ativos.items():
            for widget in self.grupos[campo].winfo_children():
                if isinstance(widget,(self.ttk.Entry,self.ttk.Combobox)):
                    widget.configure(state=('readonly' if campo=='regra' else 'normal') if ativo else 'disabled')
            if not ativo:self.campos[campo].set('')
        if hasattr(self,'resultado'):self.resultado.set('Dados alterados. Confira novamente; nenhum valor atualizado foi calculado.')

    def conferir(self):
        from recibo_rescisao import reais
        try:
            d=conferir_dados({k:v.get() for k,v in self.campos.items()})
            linhas=['Dados de entrada conferidos — cálculo não realizado.',
                    'Base: '+d['base'],'Competência: '+d['competencia'].strftime('%m/%Y'),
                    'Pagamento: '+d['pagamento'].strftime('%d/%m/%Y')]
            for campo,valor in d['valores'].items():
                linhas.append(('Folha de trabalhadores: ' if campo=='folha' else 'Folha de aprendizes: ')+reais(valor))
            linhas.append('Use Buscar coeficiente e calcular para consultar a tabela oficial. Conferir dados não realiza cálculo.')
            self.resultado.set('\n'.join(linhas))
        except ValueError as exc:self.resultado.set('Confira o preenchimento: '+str(exc))

    def limpar(self):
        for var in self.campos.values():var.set('')
        self.excecao_sefip.set(False);self.sem_suspensao.set(False)
        self.resultado.set('Formulário limpo. Nenhum cálculo realizado.')

    def entrada_atual(self):
        entrada={k:v.get() for k,v in self.campos.items()}
        entrada.update(excecao_sefip=self.excecao_sefip.get(),suspensao=self.sem_suspensao.get())
        return entrada

    def calcular(self):
        if self.ocupado:return
        entrada=self.entrada_atual()
        self.ocupado=True;self.botao_calcular.configure(state='disabled')
        self.resultado.set('Consultando o catálogo público e o edital da CAIXA. Aguarde…')
        def executar():
            try:self.fila.put((entrada,calcular_online(entrada),None))
            except Exception as exc:self.fila.put((entrada,None,str(exc)))
        threading.Thread(target=executar,daemon=True).start()
        self.root.after(150,self.receber_calculo)

    def receber_calculo(self):
        try:entrada,resultado,erro=self.fila.get_nowait()
        except queue.Empty:
            self.root.after(150,self.receber_calculo);return
        self.ocupado=False;self.botao_calcular.configure(state='normal')
        if entrada!=self.entrada_atual():
            self.resultado.set('Os dados foram alterados durante a consulta. Consulte novamente para calcular os valores atuais.');return
        if erro:
            self.resultado.set('Cálculo indisponível: '+erro+' Nenhum valor foi estimado.');return
        from recibo_rescisao import reais
        c=resultado['consulta'];linhas=['SIMULAÇÃO — FGTS mensal em atraso (SEFIP/GRF)',
            'Competência: '+entrada['competencia']+' · Pagamento: '+entrada['pagamento'],
            'Coeficiente oficial sobre a remuneração: '+str(c['coeficiente']).replace('.',','),
            'Tabela 7 · página '+str(c['pagina'])+' · Vigência: '+c['inicio'].strftime('%d/%m/%Y')+' a '+c['fim'].strftime('%d/%m/%Y')]
        for p in resultado['partes']:
            linhas.extend(['','APRENDIZES' if p['campo']=='aprendiz' else 'TRABALHADORES',
                'Base: '+reais(p['base'])+' · FGTS principal: '+reais(p['principal']),
                'Cálculo: '+str(p['base'])+' × '+str(c['coeficiente'])+' × fator '+str(p['fator']),
                'Encargos agregados (atualização, juros, multa e contribuição social, quando devida): '+reais(p['encargos']),
                'Total: '+reais(p['total'])])
        linhas.extend(['','TOTAL: '+reais(resultado['total']),
            'Valores truncados em 2 casas decimais, conforme orientação da CAIXA.',
            'Comparação com arredondamento de centavos: '+reais(resultado['comparacao_arredondada'])+' (não é o critério de truncamento do edital).',
            'Fonte: '+c['fonte'],'Cópia local: '+c['arquivo'],'SHA-256: '+c['sha256'],
            'Simulação para conferência. Não emite guia nem confirma enquadramento jurídico.'])
        self.resultado.set('\n'.join(linhas))
