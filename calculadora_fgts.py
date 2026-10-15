"""Entrada local para FGTS em atraso; não estima coeficientes ausentes."""
from datetime import datetime
import re

from recibo_rescisao import valor_monetario

BASES = ('Trabalhadores', 'Aprendizes', 'Ambos')
REGRAS = (
    'Simples Federal — faturamento anual até R$ 1.200.000,00',
    'Empregador doméstico',
    'Produtor rural pessoa física — faturamento anual até R$ 1.200.000,00',
    'Nenhum',
)


def competencia_valida(texto):
    texto=str(texto).strip()
    if not re.fullmatch(r'(0[1-9]|1[0-2])/\d{4}',texto):
        raise ValueError('Informe a competência em MM/AAAA.')
    data=datetime.strptime(texto,'%m/%Y').date()
    if data.year<1995:raise ValueError('O formulário de referência abrange competências a partir de 1995.')
    return data


def exige_regra(competencia):
    return 2002<=competencia_valida(competencia).year<=2006


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
        raise ValueError('Selecione a regra de preenchimento para competências de 2002 a 2006.')
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


class FormularioFGTS:
    """Formulário independente de serviços, cookies ou credenciais da Econet."""
    def __init__(self,parent):
        import tkinter as tk
        from tkinter import ttk
        self.tk=tk;self.ttk=ttk
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
        aviso=ttk.Label(area,text='Formulário adaptado · cálculo aguardando coeficientes oficiais. '
            'Nenhum dado é enviado à Econet.',style='Card.TLabel',wraplength=650)
        aviso.pack(fill='x',pady=(0,12))
        self.campos={};self.grupos={}
        nomes=[('base','Base do FGTS *'),('competencia','Competência · MM/AAAA *'),
               ('regra','Regra histórica · competências de 2002 a 2006 *'),
               ('razao_social','Razão social · opcional'),('email','E-mail · opcional, apenas local'),
               ('pagamento','Data de pagamento · DD/MM/AAAA *'),
               ('folha','Valor da folha — trabalhadores *'),('aprendiz','Valor da folha — aprendizes *')]
        for campo,nome in nomes:
            grupo=tk.Frame(area,background='white');self.grupos[campo]=grupo
            grupo.pack(fill='x',pady=3)
            ttk.Label(grupo,text=nome,style='Card.TLabel').pack(anchor='w')
            var=tk.StringVar();self.campos[campo]=var
            if campo in ('base','regra'):
                entrada=ttk.Combobox(grupo,textvariable=var,state='readonly',values=BASES if campo=='base' else REGRAS)
            else:entrada=ttk.Entry(grupo,textvariable=var)
            entrada.pack(fill='x',pady=(2,0))
        # Campos inativos ficam desabilitados e nunca participam da conferência.
        self.campos['base'].trace_add('write',self.atualizar_campos)
        self.campos['competencia'].trace_add('write',self.atualizar_campos)
        acoes=tk.Frame(area,background='white');acoes.pack(fill='x',pady=12)
        ttk.Button(acoes,text='Conferir dados',style='Primary.TButton',command=self.conferir).pack(side='left')
        ttk.Button(acoes,text='Calcular · aguardando coeficientes',state='disabled').pack(side='left',padx=8)
        ttk.Button(acoes,text='Limpar',command=self.limpar).pack(side='left')
        self.resultado=tk.StringVar(value='Preencha os dados para conferência. Nenhum valor atualizado foi calculado.')
        for campo,var in self.campos.items():
            if campo not in ('base','competencia'):
                var.trace_add('write',lambda *args:self.resultado.set('Dados alterados. Confira novamente; nenhum valor atualizado foi calculado.'))
        resultado=ttk.Label(area,textvariable=self.resultado,style='Card.TLabel',wraplength=650,justify='left')
        resultado.pack(fill='x',pady=(0,12))
        area.bind('<Configure>',lambda e:[l.configure(wraplength=max(200,e.width-32)) for l in (aviso,resultado)],add='+')
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
            linhas.append('Para apurar FGTS, juros, atualização e multa, faltam as fórmulas e os coeficientes oficiais aplicáveis à competência e à data. Não substitui guia de recolhimento; suspensões especiais não foram verificadas.')
            self.resultado.set('\n'.join(linhas))
        except ValueError as exc:self.resultado.set('Confira o preenchimento: '+str(exc))

    def limpar(self):
        for var in self.campos.values():var.set('')
        self.resultado.set('Formulário limpo. Nenhum cálculo realizado.')
