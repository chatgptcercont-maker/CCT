"""Entrada local para as ferramentas da Cercont; não executa agentes ao abrir."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

AGENTES = (
    {'id':'cct','nome':'Monitor de CCT','status':'Disponível',
     'descricao':'Convenções e aditivos com abrangência em Alagoas. Consulte novidades, confira resumos e preserve seu histórico.',
     'acao':'Abrir monitor'},
    {'id':'admissao','nome':'Conferência de Admissão','status':'Aguardando definição das regras',
     'descricao':'Espaço reservado para conferir documentos e dados de admissão. Nenhuma conferência automática está implementada neste módulo.',
     'acao':'Ver módulo'},
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
        root.protocol('WM_DELETE_WINDOW',self.fechar)
        self.mostrar_inicio()

    def rolar_inicio(self,event):
        if self.home.winfo_ismapped():
            self.canvas_inicio.yview_scroll(-int(event.delta/120),'units')

    def redimensionar(self,event):
        colunas=2 if event.width>=850 else 1
        for i,c in enumerate(self.cards):
            self.grade.columnconfigure(i,weight=1 if i<colunas else 0,uniform='agentes' if i<colunas else '')
            c.grid(row=i//colunas,column=i%colunas,sticky='ew',padx=(0,12 if colunas==2 and i==0 else 0),pady=(0,12))

    def ocultar_telas(self):
        self.home.pack_forget();self.admissao.pack_forget()
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
        self.ocultar_telas()
        if identificador=='cct':
            self.tela_monitor.pack(fill='both',expand=True)
            self.root.title('Monitor de Convenções e Aditivos — Alagoas | Cercont')
        else:
            self.admissao.pack(fill='both',expand=True)
            self.root.title('Conferência de Admissão | Cercont — Em preparação')

    def fechar(self):
        if self.monitor is not None and self.monitor.ocupado:
            messagebox.showinfo('Consulta em andamento','Aguarde a conclusão da consulta antes de fechar o hub.',parent=self.root)
            return
        self.root.destroy()
