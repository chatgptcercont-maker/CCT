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
            'regra':regra,'valores':valores}


def calcular_online(entrada,cliente=None):
    from coeficientes_fgts import ClienteCaixa,calcular_com_coeficiente
    d=conferir_dados(entrada)
    if entrada.get('regime')!='SEFIP/GRF':
        raise ValueError('Esta tabela calcula recolhimento mensal pelo SEFIP/GRF. FGTS Digital e eSocial doméstico não são atendidos.')
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
        aviso=ttk.Label(area,text='Informe os dados e consulte os coeficientes oficiais da CAIXA automaticamente. '
            'Simulação mensal SEFIP/GRF; não considera suspensões especiais e não emite guia.',style='Card.TLabel',wraplength=650)
        aviso.pack(fill='x',pady=(0,12))
        self.campos={};self.grupos={}
        campos_area=tk.Frame(area,background='white');campos_area.pack(fill='x')
        for coluna in range(2):campos_area.columnconfigure(coluna,weight=1,uniform='campos_fgts')
        nomes=[('base','Base do FGTS *'),('competencia','Competência · MM/AAAA *'),
               ('regra','Regra histórica · competências de 10/2001 a 12/2006 *'),
               ('regime','Regime de recolhimento *'),
               ('pagamento','Data de pagamento · DD/MM/AAAA *'),
               ('folha','Valor da folha — trabalhadores *'),('aprendiz','Valor da folha — aprendizes *')]
        rotulos=[]
        for i,(campo,nome) in enumerate(nomes):
            grupo=tk.Frame(campos_area,background='white');self.grupos[campo]=grupo
            grupo.grid(row=i//2,column=i%2,sticky='ew',padx=(0,8) if i%2==0 else (8,0),pady=6)
            rotulo=ttk.Label(grupo,text=nome,style='Card.TLabel',wraplength=280)
            rotulo.pack(anchor='w');rotulos.append(rotulo)
            var=tk.StringVar();self.campos[campo]=var
            if campo in ('base','regra','regime'):
                entrada=ttk.Combobox(grupo,textvariable=var,state='readonly',values={'base':BASES,'regra':REGRAS,'regime':REGIMES}[campo])
            else:entrada=ttk.Entry(grupo,textvariable=var)
            entrada.pack(fill='x',pady=(2,0))
        campos_area.bind('<Configure>',lambda e:[l.configure(wraplength=max(140,(e.width-32)//2)) for l in rotulos])
        self.campos['regime'].set('SEFIP/GRF')
        # Campos inativos ficam desabilitados e nunca participam da conferência.
        self.campos['base'].trace_add('write',self.atualizar_campos)
        self.campos['competencia'].trace_add('write',self.atualizar_campos)
        acoes=tk.Frame(area,background='white');acoes.pack(fill='x',pady=12)
        ttk.Button(acoes,text='Conferir dados',style='Primary.TButton',command=self.conferir).pack(side='left')
        self.botao_calcular=ttk.Button(acoes,text='Buscar coeficiente e calcular',command=self.calcular)
        self.botao_calcular.pack(side='left',padx=8)
        ttk.Button(acoes,text='Limpar',command=self.limpar).pack(side='left')
        self.resultado=tk.StringVar(value='Preencha os dados para iniciar.')
        for campo,var in self.campos.items():
            if campo not in ('base','competencia'):
                var.trace_add('write',self.invalidar_resultado)
        resultado=ttk.Label(area,textvariable=self.resultado,style='Card.TLabel',wraplength=650,justify='left')
        resultado.pack(fill='x',pady=(0,12))
        self.criar_painel_resultado(area)
        area.bind('<Configure>',lambda e:[l.configure(wraplength=max(200,e.width-64)) for l in (aviso,resultado,self.nota_resultado)],add='+')
        self.atualizar_campos()

    def criar_painel_resultado(self,parent):
        tk=self.tk;ttk=self.ttk
        self.painel_resultado=tk.Frame(parent,background='#f0f5f7',padx=16,pady=16)
        tk.Label(self.painel_resultado,text='Resultado da simulação',font=('Segoe UI',15,'bold'),
            background='#f0f5f7',foreground='#064d47').pack(anchor='w')
        self.subtitulo_resultado=tk.StringVar()
        tk.Label(self.painel_resultado,textvariable=self.subtitulo_resultado,font=('Segoe UI',10),
            background='#f0f5f7',foreground='#638193').pack(anchor='w',pady=(4,14))
        grade=tk.Frame(self.painel_resultado,background='#f0f5f7');grade.pack(fill='x')
        self.valores_resultado={}
        for i,(chave,titulo) in enumerate([('base','Base de remuneração'),('principal','FGTS principal'),
                                         ('encargos','Encargos'),('total','Total atualizado')]):
            destaque=chave=='total';fundo='#064d47' if destaque else 'white'
            cartao=tk.Frame(grade,background=fundo,padx=16,pady=14,highlightthickness=1,
                highlightbackground='#064d47' if destaque else '#dde7ec')
            cartao.grid(row=i//2,column=i%2,sticky='nsew',padx=4,pady=4)
            grade.columnconfigure(i%2,weight=1,uniform='resultado_fgts')
            grade.rowconfigure(i//2,weight=1,uniform='resultado_fgts')
            tk.Label(cartao,text=titulo,font=('Segoe UI',10),background=fundo,
                foreground='#d9e7e4' if destaque else '#638193').pack(anchor='w')
            var=tk.StringVar(value='');self.valores_resultado[chave]=var
            tk.Label(cartao,textvariable=var,font=('Segoe UI',19,'bold'),background=fundo,
                foreground='white' if destaque else '#064d47').pack(anchor='w',pady=(6,0))
        self.tabela_resultado=ttk.Treeview(self.painel_resultado,
            columns=('grupo','base','principal','encargos','total'),show='headings',height=2)
        for nome,titulo in [('grupo','Grupo'),('base','Base'),('principal','FGTS'),('encargos','Encargos'),('total','Total')]:
            self.tabela_resultado.heading(nome,text=titulo)
            self.tabela_resultado.column(nome,width=120 if nome=='grupo' else 100,minwidth=65,anchor='w' if nome=='grupo' else 'e')
        self.nota_resultado=tk.Label(self.painel_resultado,text='',font=('Segoe UI',10),background='#f0f5f7',
            foreground='#638193',wraplength=600,justify='left')
        self.nota_resultado.pack(fill='x',pady=(12,8))
        self.botao_detalhes=ttk.Button(self.painel_resultado,text='Ver memória de cálculo e fonte',command=self.alternar_detalhes)
        self.botao_detalhes.pack(anchor='w')
        self.detalhes_frame=tk.Frame(self.painel_resultado,background='#f0f5f7')
        self.texto_detalhes=tk.Text(self.detalhes_frame,height=12,wrap='word',font=('Segoe UI',10),
            background='white',foreground='#194e5a',relief='flat',padx=12,pady=12,state='disabled')
        barra=ttk.Scrollbar(self.detalhes_frame,command=self.texto_detalhes.yview)
        barra.pack(side='right',fill='y');self.texto_detalhes.pack(fill='both',expand=True)
        self.texto_detalhes.configure(yscrollcommand=barra.set)

    def alternar_detalhes(self):
        if self.detalhes_frame.winfo_manager():
            self.detalhes_frame.pack_forget();self.botao_detalhes.configure(text='Ver memória de cálculo e fonte')
        else:
            self.detalhes_frame.pack(fill='x',pady=(10,0));self.botao_detalhes.configure(text='Ocultar memória de cálculo e fonte')

    def invalidar_resultado(self,*args):
        if hasattr(self,'painel_resultado'):self.painel_resultado.pack_forget()
        if hasattr(self,'resultado'):self.resultado.set('Dados alterados. Calcule novamente para atualizar o resultado.')

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
        self.invalidar_resultado()

    def conferir(self):
        from recibo_rescisao import reais
        self.painel_resultado.pack_forget()
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
        self.painel_resultado.pack_forget()
        self.resultado.set('Formulário limpo. Nenhum cálculo realizado.')

    def entrada_atual(self):
        return {k:v.get() for k,v in self.campos.items()}

    def calcular(self):
        if self.ocupado:return
        entrada=self.entrada_atual()
        self.painel_resultado.pack_forget()
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
        self.apresentar_resultado(entrada,resultado,'\n'.join(linhas))

    def apresentar_resultado(self,entrada,resultado,memoria):
        from recibo_rescisao import reais
        partes=resultado['partes'];c=resultado['consulta']
        valores={'base':sum(p['base'] for p in partes),'principal':sum(p['principal'] for p in partes),
                 'encargos':sum(p['encargos'] for p in partes),'total':resultado['total']}
        for chave,var in self.valores_resultado.items():var.set(reais(valores[chave]))
        self.subtitulo_resultado.set('Competência '+entrada['competencia']+'  •  Pagamento '+entrada['pagamento'])
        for item in self.tabela_resultado.get_children():self.tabela_resultado.delete(item)
        for p in partes:
            self.tabela_resultado.insert('','end',values=('Aprendizes' if p['campo']=='aprendiz' else 'Trabalhadores',
                reais(p['base']),reais(p['principal']),reais(p['encargos']),reais(p['total'])))
        self.tabela_resultado.pack_forget()
        if len(partes)>1:self.tabela_resultado.pack(fill='x',pady=(12,0),before=self.nota_resultado)
        self.nota_resultado.configure(text='Coeficiente CAIXA: '+str(c['coeficiente']).replace('.',',')+
            '  •  Tabela 7, página '+str(c['pagina'])+'\nTotal truncado em centavos conforme o edital. '
            'Encargos incluem atualização, juros, multa e contribuição social quando devida. '
            'Suspensões especiais não consideradas; aplicável ao regime SEFIP/GRF selecionado.')
        self.detalhes_frame.pack_forget();self.botao_detalhes.configure(text='Ver memória de cálculo e fonte')
        self.texto_detalhes.configure(state='normal');self.texto_detalhes.delete('1.0','end')
        self.texto_detalhes.insert('1.0',memoria);self.texto_detalhes.configure(state='disabled')
        self.resultado.set('Consulta concluída com coeficiente oficial da CAIXA.')
        self.painel_resultado.pack(fill='x',pady=(4,12))
