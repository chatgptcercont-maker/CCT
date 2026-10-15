"""Entrada local para as ferramentas da Cercont; não executa agentes ao abrir."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

AGENTES = (
    {'id':'cct','nome':'Monitor de CCT','status':'Disponível',
     'descricao':'Convenções e aditivos com abrangência em Alagoas. Consulte novidades, confira resumos e preserve seu histórico.',
     'acao':'Abrir monitor'},
    {'id':'rescisao','nome':'Recibo de Rescisão Avulsa','status':'Disponível · valores manuais',
     'descricao':'Informe as partes, verbas e descontos já apurados. Confira a prévia e gere o recibo em PDF, sem cálculo de direitos rescisórios.',
     'acao':'Elaborar recibo'},
    {'id':'admissao','nome':'Conferência de Admissão','status':'Aguardando definição das regras',
     'descricao':'Espaço reservado para conferir documentos e dados de admissão. Nenhuma conferência automática está implementada neste módulo.',
     'acao':'Ver módulo'},
    {'id':'auditor_folha','nome':'Conferência de Folhas de Pagamentos (Auditor)','status':'A configurar',
     'descricao':'Módulo reservado para auditoria de folhas de pagamento. Os documentos, as regras de conferência e os relatórios serão definidos posteriormente.',
     'acao':'Ver módulo'},
    {'id':'sero','nome':'Regularização de Obras (SERO)','status':'A configurar',
     'descricao':'Espaço reservado para regularização de obras. Os documentos, as regras e as funcionalidades serão definidos posteriormente.',
     'acao':'Ver módulo'},
    {'id':'calculadoras','nome':'Calculadoras','status':'A configurar · 5 calculadoras',
     'descricao':'Afastamento, seguro-desemprego, desoneração da folha, juros de FGTS em atraso e custo mensal/anual do funcionário em um único módulo.',
     'acao':'Abrir calculadoras'},
)

CALCULADORAS = (
    'Calculadora de Afastamento',
    'Calculadora de Seguro-Desemprego',
    'Calculadora da Desoneração da Folha',
    'Calculadora de Juros — FGTS em Atraso',
    'Calculadora de Custo Mensal / Anual do Funcionário',
)


class HubAgentes:
    def __init__(self, root, fabrica_monitor, cartao):
        self.root=root;self.fabrica_monitor=fabrica_monitor;self.cartao=cartao
        self.monitor=None;self.tela_monitor=None
        root.geometry(f'{min(1120,max(760,root.winfo_screenwidth()-80))}x{min(740,max(500,root.winfo_screenheight()-110))}')
        root.minsize(760,500);root.configure(background='#f0f5f7')
        estilo=ttk.Style(root);estilo.theme_use('clam')
        estilo.configure('.',font=('Segoe UI',10))
        estilo.configure('Title.TLabel',background='white',foreground='#064d47',font=('Segoe UI',13,'bold'))
        estilo.configure('Card.TLabel',background='white',foreground='#194e5a')
        estilo.configure('Muted.TLabel',background='white',foreground='#638193',font=('Segoe UI',10))
        estilo.configure('Primary.TButton',padding=(16,10),background='#087c69',foreground='white')
        estilo.map('Primary.TButton',background=[('active','#064d47')],foreground=[('!disabled','white')])
        self.home=tk.Frame(root,background='#f0f5f7')
        cab=tk.Frame(self.home,background='#064d47',padx=26,pady=22);cab.pack(fill='x')
        self.logo=None;logo=Path(__file__).resolve().parent/'assets/cercont.png'
        if logo.is_file():
            try:
                imagem=tk.PhotoImage(master=root,file=str(logo));fator=max(1,(imagem.width()+179)//180,(imagem.height()+69)//70)
                self.logo=imagem.subsample(fator,fator)
                tk.Label(cab,image=self.logo,background='white').pack(side='left',padx=(0,22))
            except tk.TclError:pass
        titulo=tk.Frame(cab,background='#064d47');titulo.pack(side='left',fill='x',expand=True)
        tk.Label(titulo,text='CERCONT · DEPARTAMENTO PESSOAL',background='#064d47',foreground='#d9e7e4',font=('Segoe UI',10)).pack(anchor='w')
        tk.Label(titulo,text='Hub de agentes',background='#064d47',foreground='white',font=('Segoe UI',24,'bold')).pack(anchor='w',pady=(6,0))
        tk.Label(titulo,text='Escolha a ferramenta para começar.',background='#064d47',foreground='#d9e7e4',font=('Segoe UI',11)).pack(anchor='w',pady=(6,0))
        atalhos=tk.Frame(self.home,background='white',padx=24,pady=12)
        atalhos.pack(fill='x')
        ttk.Label(atalhos,text='Abrir módulo:',style='Card.TLabel').pack(side='left',padx=(0,10))
        self.seletor_modulo=ttk.Combobox(atalhos,state='readonly',height=len(AGENTES),
            values=[a['nome'] for a in AGENTES],font=('Segoe UI',10))
        self.seletor_modulo.set(f'Escolha um dos {len(AGENTES)} módulos')
        self.seletor_modulo.pack(side='left',fill='x',expand=True)
        self.seletor_modulo.bind('<<ComboboxSelected>>',self.abrir_selecionado)
        ttk.Label(atalhos,text='Hub · SERO e Calculadoras',style='Muted.TLabel').pack(side='right',padx=(12,0))
        viewport=tk.Frame(self.home,background='#f0f5f7');viewport.pack(fill='both',expand=True)
        self.canvas_inicio=tk.Canvas(viewport,background='#f0f5f7',highlightthickness=0)
        barra=ttk.Scrollbar(viewport,command=self.canvas_inicio.yview);barra.pack(side='right',fill='y')
        self.canvas_inicio.pack(side='left',fill='both',expand=True);self.canvas_inicio.configure(yscrollcommand=barra.set)
        area=tk.Frame(self.canvas_inicio,background='#f0f5f7',padx=24,pady=24)
        janela=self.canvas_inicio.create_window(0,0,window=area,anchor='nw')
        self.canvas_inicio.bind('<Configure>',lambda e:self.canvas_inicio.itemconfigure(janela,width=e.width))
        area.bind('<Configure>',lambda e:self.canvas_inicio.configure(scrollregion=self.canvas_inicio.bbox('all')))
        root.bind('<MouseWheel>',self.rolar_inicio,add='+')
        self.grade=tk.Frame(area,background='#f0f5f7');self.grade.pack(fill='x')
        self.cards=[]
        for agente in AGENTES:
            c=cartao(self.grade,grupo=self.cards,destaque=True);self.cards.append(c)
            ttk.Label(c.conteudo,text=agente['status'],style='Muted.TLabel').pack(anchor='w')
            ttk.Label(c.conteudo,text=agente['nome'],style='Title.TLabel').pack(anchor='w',pady=(9,8))
            descricao=ttk.Label(c.conteudo,text=agente['descricao'],style='Card.TLabel',wraplength=400,justify='left');descricao.pack(fill='x',pady=(0,14))
            c.conteudo.bind('<Configure>',lambda e,l=descricao:l.configure(wraplength=max(160,e.width)),add='+')
            ttk.Button(c.conteudo,text=agente['acao'],style='Primary.TButton',command=lambda a=agente['id']:self.abrir(a)).pack(anchor='w')
        self.grade.bind('<Configure>',self.redimensionar)
        self.admissao=tk.Frame(root,background='#f0f5f7',padx=26,pady=26)
        c=cartao(self.admissao);c.pack(fill='x')
        ttk.Label(c.conteudo,text='Conferência de Admissão',style='Title.TLabel').pack(anchor='w',pady=(0,12))
        texto=ttk.Label(c.conteudo,text='Este módulo ainda não executa conferências.\n\n'
            'Para desenvolvê-lo, precisamos definir:\n'
            '• Quais documentos e planilhas serão usados;\n'
            '• Quais campos devem ser comparados;\n'
            '• Quais divergências devem ser sinalizadas;\n'
            '• Qual relatório a equipe precisa receber.\n\n'
            'O Monitor de CCT já pode ser utilizado pelo hub.',style='Card.TLabel',wraplength=650,justify='left')
        texto.pack(fill='x',pady=(0,15));c.conteudo.bind('<Configure>',lambda e:texto.configure(wraplength=max(200,e.width)),add='+')
        ttk.Button(c.conteudo,text='Voltar ao hub',command=self.mostrar_inicio).pack(anchor='w')
        self.auditor_folha=tk.Frame(root,background='#f0f5f7',padx=26,pady=26)
        c=cartao(self.auditor_folha);c.pack(fill='x')
        titulo=ttk.Label(c.conteudo,text='Conferência de Folhas de Pagamentos (Auditor)',style='Title.TLabel',wraplength=650)
        titulo.pack(anchor='w',pady=(0,12))
        texto_auditor=ttk.Label(c.conteudo,text='A configurar\n\n'
            'Este módulo será configurado posteriormente. Ainda não executa auditorias.\n\n'
            'Serão definidos os documentos de entrada, os campos e regras de conferência, '
            'as divergências a sinalizar e o formato do relatório.',
            style='Card.TLabel',wraplength=650,justify='left')
        texto_auditor.pack(fill='x',pady=(0,15))
        c.conteudo.bind('<Configure>',lambda e:[l.configure(wraplength=max(200,e.width)) for l in (titulo,texto_auditor)],add='+')
        ttk.Button(c.conteudo,text='Voltar ao hub',command=self.mostrar_inicio).pack(anchor='w')
        self.sero=tk.Frame(root,background='#f0f5f7',padx=26,pady=26)
        c=cartao(self.sero);c.pack(fill='x')
        ttk.Label(c.conteudo,text='Regularização de Obras (SERO)',style='Title.TLabel').pack(anchor='w',pady=(0,12))
        texto_sero=ttk.Label(c.conteudo,text='A configurar\n\n'
            'Este módulo será configurado posteriormente.\n\n'
            'Serão definidos os documentos necessários, as regras e as funcionalidades '
            'para regularização de obras. Ainda não realiza cálculos, consultas ou envios ao SERO.',
            style='Card.TLabel',wraplength=650,justify='left')
        texto_sero.pack(fill='x',pady=(0,15))
        c.conteudo.bind('<Configure>',lambda e:texto_sero.configure(wraplength=max(200,e.width)),add='+')
        ttk.Button(c.conteudo,text='Voltar ao hub',command=self.mostrar_inicio).pack(anchor='w')
        self.calculadoras=tk.Frame(root,background='#f0f5f7',padx=26,pady=26)
        c=cartao(self.calculadoras);c.pack(fill='x')
        ttk.Label(c.conteudo,text='Calculadoras',style='Title.TLabel').pack(anchor='w',pady=(0,12))
        ttk.Label(c.conteudo,text='Escolha uma calculadora. Todas aguardam configuração das regras.',
            style='Card.TLabel',wraplength=650).pack(anchor='w',pady=(0,12))
        self.seletor_calculadora=ttk.Combobox(c.conteudo,state='readonly',values=CALCULADORAS,height=5)
        self.seletor_calculadora.pack(fill='x',pady=(0,12))
        self.seletor_calculadora.current(0)
        self.detalhe_calculadora=tk.StringVar()
        detalhe=ttk.Label(c.conteudo,textvariable=self.detalhe_calculadora,
            style='Card.TLabel',wraplength=650,justify='left')
        detalhe.pack(fill='x',pady=(0,15))
        c.conteudo.bind('<Configure>',lambda e:detalhe.configure(wraplength=max(200,e.width)),add='+')
        self.seletor_calculadora.bind('<<ComboboxSelected>>',self.selecionar_calculadora)
        self.selecionar_calculadora()
        ttk.Button(c.conteudo,text='Voltar ao hub',command=self.mostrar_inicio).pack(anchor='w')
        self.rescisao=None
        root.protocol('WM_DELETE_WINDOW',self.fechar)
        self.mostrar_inicio()

    def rolar_inicio(self,event):
        if self.home.winfo_ismapped():
            self.canvas_inicio.yview_scroll(-int(event.delta/120),'units')

    def abrir_selecionado(self,event=None):
        indice=self.seletor_modulo.current()
        if 0<=indice<len(AGENTES):
            self.abrir(AGENTES[indice]['id'])
            self.seletor_modulo.set(f'Escolha um dos {len(AGENTES)} módulos')

    def selecionar_calculadora(self,event=None):
        indice=self.seletor_calculadora.current()
        if 0<=indice<len(CALCULADORAS):
            self.detalhe_calculadora.set(CALCULADORAS[indice]+'\n\nA configurar\n\n'
                'Os campos, as fórmulas, as tabelas aplicáveis e os resultados serão definidos posteriormente. '
                'Esta calculadora ainda não executa cálculos.')

    def redimensionar(self,event):
        colunas=2 if event.width>=850 else 1
        for i,c in enumerate(self.cards):
            self.grade.columnconfigure(i,weight=1 if i<colunas else 0,uniform='agentes' if i<colunas else '')
            c.grid(row=i//colunas,column=i%colunas,sticky='ew',padx=(6 if colunas==2 else 0),pady=(0,12))

    def ocultar_telas(self):
        self.home.pack_forget();self.admissao.pack_forget();self.auditor_folha.pack_forget()
        self.sero.pack_forget()
        self.calculadoras.pack_forget()
        if self.rescisao is not None:self.rescisao.pack_forget()
        if self.tela_monitor is not None:self.tela_monitor.pack_forget()

    def mostrar_inicio(self):
        self.ocultar_telas();self.home.pack(fill='both',expand=True)
        self.root.title('Hub de agentes | Cercont — Departamento Pessoal')

    def abrir(self,identificador):
        if identificador not in {a['id'] for a in AGENTES}:
            raise ValueError('Ferramenta não cadastrada')
        if identificador=='cct' and self.monitor is None:
            tela=tk.Frame(self.root,background='#f0f5f7')
            try:
                self.monitor=self.fabrica_monitor(self.root,container=tela,ao_voltar=self.mostrar_inicio)
                self.tela_monitor=tela
            except Exception as exc:
                tela.destroy()
                messagebox.showerror('Monitor indisponível',str(exc),parent=self.root)
                return
        if identificador=='rescisao' and self.rescisao is None:
            from modulo_rescisao import ModuloRescisao
            try:
                self.modulo_rescisao=ModuloRescisao(self.root,self.mostrar_inicio)
                self.rescisao=self.modulo_rescisao.root
            except Exception as exc:
                messagebox.showerror('Recibo indisponível',str(exc),parent=self.root)
                return
        self.ocultar_telas()
        if identificador=='cct':
            self.tela_monitor.pack(fill='both',expand=True)
            self.root.title('Monitor de Convenções e Aditivos — Alagoas | Cercont')
        elif identificador=='rescisao':
            self.rescisao.pack(fill='both',expand=True)
            self.root.title('Recibo de Rescisão Avulsa | Cercont — Valores manuais')
        elif identificador=='auditor_folha':
            self.auditor_folha.pack(fill='both',expand=True)
            self.root.title('Conferência de Folhas de Pagamentos (Auditor) | Cercont — A configurar')
        elif identificador=='sero':
            self.sero.pack(fill='both',expand=True)
            self.root.title('Regularização de Obras (SERO) | Cercont — A configurar')
        elif identificador=='calculadoras':
            self.calculadoras.pack(fill='both',expand=True)
            self.root.title('Calculadoras | Cercont — A configurar')
        else:
            self.admissao.pack(fill='both',expand=True)
            self.root.title('Conferência de Admissão | Cercont — Em preparação')

    def fechar(self):
        if self.monitor is not None and self.monitor.ocupado:
            messagebox.showinfo('Consulta em andamento','Aguarde a conclusão da consulta antes de fechar o hub.',parent=self.root)
            return
        self.root.destroy()
