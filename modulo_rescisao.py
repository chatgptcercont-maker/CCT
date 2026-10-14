"""Formulário local do recibo de rescisão com verbas manuais."""
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import webbrowser
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from recibo_rescisao import preparar_recibo,texto_recibo,exportar_recibo,reais


class ModuloRescisao:
    def __init__(self,parent,voltar):
        self.root=tk.Frame(parent,background='#f0f5f7');self.voltar=voltar;self.itens=[];self.ultimo_pdf=None
        topo=tk.Frame(self.root,background='#064d47',padx=20,pady=16);topo.pack(fill='x')
        tk.Label(topo,text='Recibo de Rescisão Avulsa',font=('Segoe UI',18,'bold'),background='#064d47',foreground='white').pack(side='left')
        ttk.Button(topo,text='Voltar ao hub',command=voltar).pack(side='right')
        viewport=tk.Frame(self.root,background='#f0f5f7');viewport.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(viewport,background='#f0f5f7',highlightthickness=0)
        scroll=ttk.Scrollbar(viewport,command=self.canvas.yview);scroll.pack(side='right',fill='y')
        self.canvas.pack(fill='both',expand=True);self.canvas.configure(yscrollcommand=scroll.set)
        area=tk.Frame(self.canvas,background='white',padx=20,pady=16)
        janela=self.canvas.create_window(0,0,window=area,anchor='nw')
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(janela,width=e.width))
        area.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        parent.bind('<MouseWheel>',self.rolar,add='+')
        ttk.Label(area,text='Informe as verbas já apuradas. O módulo soma valores, sem calcular direitos rescisórios.',style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=(0,14))
        campos=tk.Frame(area,background='white');campos.pack(fill='x');self.campos={}
        nomes=[('empresa','Empresa / contratante *'),('documento_empresa','CPF ou CNPJ do contratante'),
               ('trabalhador','Trabalhador *'),('cpf','CPF do trabalhador'),('admissao','Admissão · DD/MM/AAAA'),
               ('desligamento','Desligamento · DD/MM/AAAA'),('local','Local *'),('data_recibo','Data do recibo · DD/MM/AAAA *')]
        for i,(campo,nome) in enumerate(nomes):
            grupo=tk.Frame(campos,background='white');grupo.grid(row=i//2,column=i%2,sticky='ew',padx=6,pady=5)
            campos.columnconfigure(i%2,weight=1,uniform='dados')
            ttk.Label(grupo,text=nome,style='Card.TLabel').pack(anchor='w')
            v=tk.StringVar(value=datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y') if campo=='data_recibo' else '')
            self.campos[campo]=v;ttk.Entry(grupo,textvariable=v).pack(fill='x',pady=(4,0))
        ttk.Label(area,text='Verbas e descontos',style='Title.TLabel').pack(anchor='w',pady=(16,8))
        entrada=tk.Frame(area,background='white');entrada.pack(fill='x')
        self.descricao=tk.StringVar();self.valor=tk.StringVar();self.tipo=tk.StringVar(value='Provento')
        for coluna,titulo,var,largura in [(0,'Descrição',self.descricao,36),(1,'Valor em reais',self.valor,14)]:
            grupo=tk.Frame(entrada,background='white');grupo.grid(row=0,column=coluna,sticky='ew',padx=(0,8))
            ttk.Label(grupo,text=titulo,style='Card.TLabel').pack(anchor='w');ttk.Entry(grupo,textvariable=var,width=largura).pack(fill='x',pady=4)
        entrada.columnconfigure(0,weight=1)
        grupo=tk.Frame(entrada,background='white');grupo.grid(row=0,column=2,sticky='ew')
        ttk.Label(grupo,text='Tipo',style='Card.TLabel').pack(anchor='w')
        ttk.Combobox(grupo,textvariable=self.tipo,values=['Provento','Desconto'],state='readonly',width=12).pack(pady=4)
        ttk.Button(area,text='Adicionar verba',command=self.adicionar).pack(anchor='w',pady=8)
        self.tabela=ttk.Treeview(area,columns=('descricao','tipo','valor'),show='headings',height=6)
        for nome,titulo,largura in [('descricao','Descrição',380),('tipo','Tipo',100),('valor','Valor',120)]:
            self.tabela.heading(nome,text=titulo);self.tabela.column(nome,width=largura,minwidth=60)
        self.tabela.pack(fill='x');ttk.Button(area,text='Remover verba selecionada',command=self.remover).pack(anchor='w',pady=7)
        self.total=tk.StringVar(value='Proventos: R$ 0,00 · Descontos: R$ 0,00 · Líquido: R$ 0,00')
        ttk.Label(area,textvariable=self.total,style='Title.TLabel').pack(anchor='w',pady=(5,12))
        ttk.Label(area,text='Observações',style='Card.TLabel').pack(anchor='w');self.observacoes=tk.Text(area,height=3,wrap='word',font=('Segoe UI',10));self.observacoes.pack(fill='x',pady=5)
        acoes=tk.Frame(area,background='white');acoes.pack(fill='x',pady=12)
        ttk.Button(acoes,text='Conferir prévia',command=self.previa).pack(side='left')
        ttk.Button(acoes,text='Gerar recibo PDF',style='Primary.TButton',command=self.gerar).pack(side='left',padx=8)
        self.abrir=ttk.Button(acoes,text='Abrir PDF',command=self.abrir_pdf,state='disabled');self.abrir.pack(side='left')
        self.texto=tk.Text(area,height=14,wrap='word',font=('Segoe UI',10),state='disabled');self.texto.pack(fill='x')
        ttk.Label(area,text='Revise as partes, as verbas e o valor líquido antes de gerar. Os dados ficam locais e os recibos anteriores são preservados.',style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=12)

    def rolar(self,event):
        if self.root.winfo_ismapped() and not isinstance(event.widget,tk.Text):self.canvas.yview_scroll(-int(event.delta/120),'units')

    def adicionar(self):
        from recibo_rescisao import valor_monetario
        try:
            descricao=self.descricao.get().strip();valor=valor_monetario(self.valor.get())
            if not descricao or valor<=0:raise ValueError('Informe uma descrição e valor maior que zero.')
            self.itens.append({'descricao':descricao,'valor':str(valor),'tipo':self.tipo.get()})
            self.descricao.set('');self.valor.set('');self.atualizar()
        except ValueError as exc:messagebox.showerror('Verba inválida',str(exc),parent=self.root)

    def remover(self):
        indices=sorted((int(i) for i in self.tabela.selection()),reverse=True)
        for i in indices:del self.itens[i]
        self.atualizar()

    def atualizar(self):
        from decimal import Decimal
        for i in self.tabela.get_children():self.tabela.delete(i)
        proventos=Decimal('0');descontos=Decimal('0')
        for i,item in enumerate(self.itens):
            v=Decimal(item['valor']);self.tabela.insert('', 'end',iid=str(i),values=(item['descricao'],item['tipo'],reais(v)))
            if item['tipo']=='Provento':proventos+=v
            else:descontos+=v
        self.total.set(f'Proventos: {reais(proventos)} · Descontos: {reais(descontos)} · Líquido: {reais(proventos-descontos)}')

    def dados_recibo(self):
        dados={k:v.get() for k,v in self.campos.items()};dados['observacoes']=self.observacoes.get('1.0','end-1c')
        return preparar_recibo(dados,self.itens)

    def previa(self):
        try:
            r=self.dados_recibo();self.texto.configure(state='normal');self.texto.delete('1.0','end');self.texto.insert('1.0',texto_recibo(r));self.texto.configure(state='disabled');return r
        except ValueError as exc:messagebox.showerror('Confira os dados',str(exc),parent=self.root);return None

    def gerar(self):
        r=self.previa()
        if r is None:return
        destino=filedialog.asksaveasfilename(parent=self.root,title='Salvar novo recibo',initialfile='recibo_rescisao.pdf',defaultextension='.pdf',filetypes=[('PDF','*.pdf')])
        if not destino:return
        try:
            self.ultimo_pdf=exportar_recibo(r,destino);self.abrir.configure(state='normal')
            messagebox.showinfo('Recibo gerado','PDF salvo em '+str(self.ultimo_pdf),parent=self.root)
        except (OSError,ValueError) as exc:messagebox.showerror('Recibo não gerado',str(exc),parent=self.root)

    def abrir_pdf(self):
        if self.ultimo_pdf:
            try:
                if os.name=='nt':os.startfile(self.ultimo_pdf.resolve())
                else:webbrowser.open(self.ultimo_pdf.resolve().as_uri())
            except OSError as exc:messagebox.showerror('PDF indisponível',str(exc),parent=self.root)
