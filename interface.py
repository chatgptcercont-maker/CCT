"""Interface manual: um clique inicia a coleta pública no Mediador."""
import json
from datetime import datetime
import os
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from consulta_online import executar_online

BASE = Path(__file__).resolve().parent
CONFIG = BASE/'configuracao_monitor.json'


def carregar_config():
    if not CONFIG.exists():
        controle = BASE/'controle_convencoes_AL.xlsx'
        return {'controle': str(controle) if controle.exists() else '', 'aba': ''}
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('Configuração local inválida')
    return config


def salvar_config(config):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=BASE, prefix='config_monitor_', suffix='.tmp', delete=False) as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        temporario = Path(f.name)
    os.replace(temporario, CONFIG)


class Cartao(tk.Canvas):
    """Painel com borda discreta e cantos arredondados, sem dependências extras."""
    def __init__(self, parent, grupo=None, destaque=False):
        self.grupo = grupo
        self.destaque = destaque
        super().__init__(parent, background='#f0f5f7', highlightthickness=0, height=80)
        self.borda = self.create_polygon(0, 0, 1, 0, 1, 1, 0, 1, fill='white', outline='#dde7ec', smooth=True)
        self.traco = self.create_line(3, 12, 3, 60, fill='#087c69', width=3) if destaque else None
        self.conteudo = tk.Frame(self, background='white')
        self.janela = self.create_window(16, 14, window=self.conteudo, anchor='nw')
        self.bind('<Configure>', self.redimensionar)
        self.conteudo.bind('<Configure>', self.ajustar_altura)

    def ajustar_altura(self, event=None):
        cartoes = self.grupo if self.grupo else [self]
        altura = max(max(132 if c.destaque else 0, c.conteudo.winfo_reqheight()+28) for c in cartoes)
        for cartao in cartoes:
            if int(cartao.cget('height')) != altura:
                cartao.configure(height=altura)

    def redimensionar(self, event):
        w, h, r = event.width-1, event.height-1, 12
        self.coords(self.borda, r,1,w-r,1,w,1,w,r,w,h-r,w,h,w-r,h,r,h,1,h,1,h-r,1,r,1,1)
        if self.traco is not None:
            self.coords(self.traco, 3, 14, 3, max(14,h-14))
        self.itemconfigure(self.janela, width=max(1, w-32))


class Aplicacao:
    def __init__(self, root):
        self.root = root
        self.root.title('Monitor de Convenções e Aditivos — Alagoas | Cercont')
        largura = min(1180, max(760, root.winfo_screenwidth()-80))
        altura = min(820, max(500, root.winfo_screenheight()-110))
        self.root.geometry(f'{largura}x{altura}')
        self.root.minsize(760, 500)
        self.root.configure(background='#f0f5f7')
        familias = {f.lower() for f in tkfont.families(root)}
        self.fonte = 'Segoe UI' if 'segoe ui' in familias else 'Arial'
        self.configurar_estilo()
        self.fila = queue.Queue()
        self.ocupado = False
        self.ultima_pasta = None
        self.dados_painel = None
        self.config = carregar_config()
        self.controle = tk.StringVar(value=self.config.get('controle', ''))
        self.aba = tk.StringVar(value=self.config.get('aba', ''))
        self.periodo = tk.StringVar(value=self.config.get('periodo', 'Ano de 2026'))
        self.status = tk.StringVar(value='Pronto para consultar a fonte oficial.')
        self.percentual = tk.DoubleVar(value=0)
        self.indicador = tk.StringVar(value='Nenhuma consulta em andamento')

        cabecalho = tk.Frame(root, background='#064d47', padx=22, pady=16)
        cabecalho.pack(fill='x')
        marca = tk.Frame(cabecalho, background='white', padx=12, pady=6)
        marca.pack(side='left', padx=(0, 22))
        self.logo = None
        caminho_logo = BASE / 'assets' / 'cercont.png'
        if caminho_logo.is_file():
            try:
                original = tk.PhotoImage(master=root, file=str(caminho_logo))
                fator = max(1, (original.width()+179)//180, (original.height()+69)//70)
                self.logo = original.subsample(fator, fator)
            except tk.TclError:
                pass
        if self.logo is not None:
            tk.Label(marca, image=self.logo, background='white').pack()
        else:
            tk.Label(marca, text='Cercont', background='white', foreground='#064d47', font=(self.fonte, 18, 'bold')).pack()
            tk.Label(marca, text='Logo local não encontrada', background='white', foreground='#638193', font=(self.fonte, 10)).pack()
        titulos = tk.Frame(cabecalho, background='#064d47')
        titulos.pack(side='left', fill='x', expand=True)
        tk.Label(titulos, text='DEPARTAMENTO PESSOAL', background='#064d47', foreground='#cce5dc', font=(self.fonte, 11, 'bold')).pack(anchor='w')
        self.titulo = tk.Label(titulos, text='Monitor de Convenções e Aditivos', background='#064d47', foreground='white', font=(self.fonte, 18, 'bold'), justify='left', anchor='w')
        self.titulo.pack(anchor='w', pady=(4, 4), fill='x')
        tk.Label(titulos, text='Alagoas e seus municípios · Sistema Mediador', background='#064d47', foreground='#d9e7e4', font=(self.fonte, 10)).pack(anchor='w')
        titulos.bind('<Configure>', lambda e: self.titulo.configure(wraplength=max(250,e.width)))

        corpo = tk.Frame(root, background='#f0f5f7')
        corpo.pack(fill='both', expand=True)
        lateral = tk.Frame(corpo, background='#033f38', width=154)
        lateral.pack(side='left', fill='y'); lateral.pack_propagate(False)
        tk.Label(lateral, text='NAVEGAÇÃO', background='#033f38', foreground='#cce5dc', font=(self.fonte, 10, 'bold')).pack(anchor='w', padx=18, pady=(24, 12))
        self.menu = {}
        for nome, icone in [('Início','⌂'), ('Consultas','≡'), ('Configurações','⚙'), ('Ajuda','?')]:
            botao = tk.Button(lateral, text=f'{icone}   {nome}', command=lambda n=nome: self.navegar(n),
                              background='#033f38', foreground='white', activebackground='#226c5c', activeforeground='white',
                              relief='flat', borderwidth=0, anchor='w', padx=16, pady=12, font=(self.fonte, 10), cursor='hand2')
            botao.pack(fill='x', padx=8, pady=3); self.menu[nome] = botao
        tk.Label(lateral, text='Execução manual\nSem agendamento', background='#033f38', foreground='#cce5dc', font=(self.fonte, 9), justify='left').pack(side='bottom', anchor='w', padx=18, pady=20)

        self.canvas = tk.Canvas(corpo, background='#f0f5f7', highlightthickness=0)
        rolagem = ttk.Scrollbar(corpo, command=self.canvas.yview)
        rolagem.pack(side='right', fill='y'); self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=rolagem.set)
        self.pagina = tk.Frame(self.canvas, background='#f0f5f7', padx=20, pady=18)
        self.pagina_id = self.canvas.create_window(0, 0, window=self.pagina, anchor='nw')
        self.canvas.bind('<Configure>', self.redimensionar_pagina)
        self.pagina.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        root.bind('<MouseWheel>', self.rolar_pagina, add='+')

        self.topo = tk.Frame(self.pagina, background='#f0f5f7'); self.topo.pack(fill='x', pady=(0, 14))
        self.cartoes = []
        for tipo, titulo, valor, descricao in [
                ('fonte','Fonte oficial','Sistema Mediador','Consulta às convenções e aditivos diretamente da fonte oficial.'),
                ('local','Abrangência','Alagoas e municípios','Cobertura estadual e de qualquer município de Alagoas.'),
                ('controle','Controle','Planilha preservada','Mantém o histórico nas cópias do controle.')]:
            cartao = Cartao(self.topo, grupo=self.cartoes, destaque=True); self.cartoes.append(cartao)
            self.criar_icone(cartao.conteudo, tipo).pack(side='left', anchor='n', padx=(0,14), pady=3)
            detalhes = tk.Frame(cartao.conteudo, background='white'); detalhes.pack(side='left', fill='x', expand=True)
            ttk.Label(detalhes, text=titulo, style='Muted.TLabel').pack(anchor='w')
            forte = ttk.Label(detalhes, text=valor, style='Title.TLabel', wraplength=190, justify='left'); forte.pack(anchor='w', pady=(5,5))
            texto = ttk.Label(detalhes, text=descricao, style='Muted.TLabel', wraplength=190, justify='left'); texto.pack(anchor='w')
            detalhes.bind('<Configure>', lambda e, t=texto, f=forte: (t.configure(wraplength=max(100,e.width)),f.configure(wraplength=max(100,e.width))))

        self.card_filtros = Cartao(self.pagina); self.card_filtros.pack(fill='x', pady=(0,14))
        filtros = self.card_filtros.conteudo
        self.criar_titulo_painel(filtros, 'busca', 'Prepare sua consulta', 'Informe os dados para iniciar a consulta de convenções e aditivos.')
        self.campos = tk.Frame(filtros, background='white'); self.campos.pack(fill='x')
        self.grupo_periodo = tk.Frame(self.campos, background='white')
        self.grupo_aba = tk.Frame(self.campos, background='white')
        ttk.Label(self.grupo_periodo, text='Período de registro', style='Card.TLabel').pack(anchor='w')
        self.campo_periodo = ttk.Combobox(self.grupo_periodo, textvariable=self.periodo, values=['Ano de 2026','Últimos 7 dias','Ontem'], state='readonly', width=22)
        self.campo_periodo.pack(fill='x', pady=(5,10))
        ttk.Label(self.grupo_aba, text='Aba da planilha · opcional', style='Card.TLabel').pack(anchor='w')
        self.campo_aba = ttk.Entry(self.grupo_aba, textvariable=self.aba); self.campo_aba.pack(fill='x', pady=(5,10))
        ttk.Label(filtros, text='Planilha de controle · opcional na primeira consulta', style='Card.TLabel').pack(anchor='w')
        entrada = tk.Frame(filtros, background='white'); entrada.pack(fill='x', pady=(5,7))
        self.campo_controle = ttk.Entry(entrada, textvariable=self.controle); self.campo_controle.pack(side='left', fill='x', expand=True)
        self.escolher = ttk.Button(entrada, text='▱  Escolher planilha', command=self.selecionar_controle); self.escolher.pack(side='left', padx=(8,0))
        self.auxiliar = ttk.Label(filtros, text='O arquivo original é preservado. Sem planilha, um novo controle será criado.', style='Muted.TLabel', justify='left')
        self.auxiliar.pack(anchor='w', pady=(0,10))
        botoes = tk.Frame(filtros, background='white'); botoes.pack(fill='x')
        self.consultar = ttk.Button(botoes, text='Consultar novidades', style='Primary.TButton', command=self.iniciar); self.consultar.pack(side='left')
        self.abrir = ttk.Button(botoes, text='Abrir resultados', command=self.abrir_resultados, state='disabled'); self.abrir.pack(side='left', padx=8)
        self.botao_painel = ttk.Button(botoes, text='Ver painel', command=self.exibir_painel); self.botao_painel.pack(side='left')
        ttk.Label(filtros, text='Execução manual · sem agendamento', style='Muted.TLabel').pack(anchor='w', pady=(9,0))

        self.card_resultados = Cartao(self.pagina); self.card_resultados.pack(fill='x')
        resultados = self.card_resultados.conteudo
        self.criar_titulo_painel(resultados, 'documento', 'Acompanhe a consulta')
        self.rotulo_status = ttk.Label(resultados, textvariable=self.status, style='Status.TLabel', wraplength=750, justify='left'); self.rotulo_status.pack(anchor='w', pady=(7,4))
        ttk.Label(resultados, textvariable=self.indicador, style='Muted.TLabel', wraplength=750).pack(anchor='w', pady=(0,6))
        self.progresso = ttk.Progressbar(resultados, mode='determinate', maximum=100, variable=self.percentual, style='Query.Horizontal.TProgressbar'); self.progresso.pack(fill='x', pady=(0,12))
        self.abas_resultados = ttk.Notebook(resultados); self.abas_resultados.pack(fill='x')
        self.logs = self.criar_area_texto(self.abas_resultados, 'Etapas da execução')
        self.texto = self.criar_area_texto(self.abas_resultados, 'Resultados e pendências')
        self.mostrar('Selecione o período e clique em Consultar novidades.\n'
                     'O programa obtém os documentos automaticamente.\n'
                     'No Windows, aguarde sem fechar a janela do Edge.\n'
                     'Bloqueios e documentos indisponíveis são registrados como pendências.')
        self.abas_resultados.select(1)
        self.navegar('Início')
        root.protocol('WM_DELETE_WINDOW', self.fechar)
        root.after(100, self.atualizar)

    def criar_icone(self, parent, tipo, escuro=False):
        fundo, linha = ('#064d47','white') if escuro else ('#d6ece4','#064d47')
        c = tk.Canvas(parent, width=54, height=54, background='white', highlightthickness=0)
        c.create_oval(1,1,53,53,fill=fundo,outline=fundo)
        if tipo=='fonte':
            c.create_oval(17,14,37,22,outline=linha,width=2)
            c.create_line(17,18,17,35, smooth=True,fill=linha,width=2)
            c.create_line(37,18,37,35,fill=linha,width=2)
            for y in (25,32):c.create_arc(17,y-5,37,y+3,start=180,extent=180,style='arc',outline=linha,width=2)
        elif tipo=='local':
            c.create_line(27,41,17,27,16,20,20,14,27,12,34,14,38,20,37,27,27,41,smooth=True,fill=linha,width=2)
            c.create_oval(23,18,31,26,outline=linha,width=2)
        elif tipo=='controle':
            c.create_polygon(27,12,39,18,37,33,27,42,17,33,15,18,fill='',outline=linha,width=2)
            c.create_line(21,26,26,31,34,22,fill=linha,width=2)
        elif tipo=='busca':
            c.create_oval(16,14,31,29,outline=linha,width=2)
            c.create_line(29,27,38,37,fill=linha,width=2)
        else:
            c.create_rectangle(18,13,36,40,outline=linha,width=2)
            for y in (22,27,32):c.create_line(22,y,32,y,fill=linha,width=2)
        return c

    def criar_titulo_painel(self, parent, tipo, titulo, subtitulo=None):
        linha = tk.Frame(parent, background='white'); linha.pack(fill='x', pady=(0,14))
        self.criar_icone(linha,tipo,escuro=True).pack(side='left',padx=(0,14))
        textos = tk.Frame(linha, background='white'); textos.pack(side='left',fill='x',expand=True)
        ttk.Label(textos,text=titulo,style='Title.TLabel').pack(anchor='w')
        if subtitulo:
            legenda = ttk.Label(textos,text=subtitulo,style='Muted.TLabel',wraplength=600,justify='left'); legenda.pack(anchor='w',pady=(5,0))
            textos.bind('<Configure>',lambda e:legenda.configure(wraplength=max(100,e.width)))

    def criar_area_texto(self, notebook, titulo):
        painel = tk.Frame(notebook, background='white'); notebook.add(painel, text=titulo)
        texto = tk.Text(painel, wrap='word', height=11, background='#f4f7fa', foreground='#194e5a', font=(self.fonte,10), relief='flat', padx=12, pady=10, spacing3=4, state='disabled')
        texto.pack(side='left', fill='both', expand=True)
        barra = ttk.Scrollbar(painel, command=texto.yview); barra.pack(side='right', fill='y'); texto.configure(yscrollcommand=barra.set)
        return texto

    def redimensionar_pagina(self, event):
        self.canvas.itemconfigure(self.pagina_id, width=event.width)
        largura = max(200,event.width-40)
        colunas = 3 if largura >= 840 else 1
        for i in range(3): self.topo.columnconfigure(i, weight=1 if i<colunas else 0, uniform='informativos' if i<colunas else '')
        for i, cartao in enumerate(self.cartoes):
            cartao.grid(row=i//colunas, column=i%colunas, sticky='ew', padx=(5 if colunas>1 else 0), pady=(0,8 if colunas==1 else 0))
        duas = largura >= 650
        self.campos.columnconfigure(0, weight=1, uniform='campos')
        self.campos.columnconfigure(1, weight=1 if duas else 0, uniform='campos' if duas else '')
        self.grupo_periodo.grid(row=0,column=0,sticky='ew',padx=(0,8 if duas else 0))
        self.grupo_aba.grid(row=0 if duas else 1,column=1 if duas else 0,sticky='ew',padx=(8 if duas else 0,0))
        self.auxiliar.configure(wraplength=largura-40)
        self.rotulo_status.configure(wraplength=largura-40)

    def rolar_pagina(self, event):
        # A rolagem dos logs permanece independente da página.
        if isinstance(event.widget, tk.Text): return
        self.canvas.yview_scroll(-int(event.delta/120), 'units')

    def navegar(self, nome):
        for item, botao in self.menu.items():
            botao.configure(background='#226c5c' if item==nome else '#033f38')
        if nome == 'Ajuda':
            messagebox.showinfo('Ajuda', 'Escolha o período e clique em Consultar novidades.\n'
                'A planilha e sua aba são opcionais. O arquivo original é preservado.\n'
                'A barra mede registros examinados na pesquisa atual, não o sucesso dos documentos.\n'
                'Se houver pendências, confira o relatório e o log em Abrir resultados.\n'
                'A logo original deve estar em assets/cercont.png.')
            return
        self.root.update_idletasks()
        alvo = self.card_resultados if nome=='Consultas' else self.card_filtros if nome=='Configurações' else None
        if alvo:
            altura = max(1,self.pagina.winfo_height())
            self.canvas.yview_moveto(alvo.winfo_y()/altura)
            if nome=='Configurações': self.campo_periodo.focus_set()
        else: self.canvas.yview_moveto(0)

    def registrar_etapa(self, mensagem):
        linha = datetime.now().astimezone().strftime('[%d/%m/%Y %H:%M:%S] ') + str(mensagem) + '\n'
        self.logs.configure(state='normal'); self.logs.insert('end',linha); self.logs.see('end'); self.logs.configure(state='disabled')

    def atualizar_percentual(self, dados):
        total, examinados = dados.get('total'), dados.get('examinados',0)
        if total is None:
            self.percentual.set(0); self.indicador.set('Pesquisa atual · aguardando contagem oficial')
            return
        percentual = 100 if total==0 else min(100,examinados*100/total)
        self.percentual.set(percentual)
        self.indicador.set(f'Pesquisa atual · {percentual:.0f}% · {examinados} de {total} registros examinados')

    def configurar_estilo(self):
        for nome in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
            tkfont.nametofont(nome, root=self.root).configure(family=self.fonte, size=10)
        self.root.option_add('*TCombobox*Listbox.font', (self.fonte, 10))
        estilo = ttk.Style(self.root)
        estilo.theme_use('clam')
        estilo.configure('.', font=(self.fonte, 10))
        estilo.configure('App.TFrame', background='#f0f5f7')
        estilo.configure('Card.TFrame', background='white')
        estilo.configure('Card.TLabel', background='white', foreground='#194e5a')
        estilo.configure('Title.TLabel', background='white', foreground='#064d47', font=(self.fonte, 11, 'bold'))
        estilo.configure('Muted.TLabel', background='white', foreground='#638193', font=(self.fonte, 9))
        estilo.configure('Status.TLabel', background='white', foreground='#064d47')
        estilo.configure('Footer.TLabel', background='#f0f5f7', foreground='#638193', font=(self.fonte, 9))
        estilo.configure('TEntry', padding=7, fieldbackground='white')
        estilo.configure('TCombobox', padding=7, fieldbackground='white')
        estilo.map('TCombobox', fieldbackground=[('readonly', 'white')], foreground=[('readonly', '#194e5a')])
        estilo.configure('TButton', padding=(12, 9), background='#e6edf2', foreground='#194e5a')
        estilo.map('TButton', background=[('active', '#d5e3dd')], foreground=[('disabled', '#788580')])
        estilo.configure('Primary.TButton', padding=(16, 9), background='#087c69', foreground='white', font=(self.fonte, 10, 'bold'))
        estilo.map('Primary.TButton', background=[('disabled', '#c9d9d3'), ('pressed', '#003e39'), ('active', '#006b62')],
                   foreground=[('disabled', '#638193'), ('!disabled', 'white')])
        estilo.configure('Query.Horizontal.TProgressbar', background='#064d47', troughcolor='#e6edf2', borderwidth=0, thickness=5)

    def mostrar(self, texto):
        self.texto.configure(state='normal'); self.texto.delete('1.0', 'end')
        self.texto.insert('1.0', texto); self.texto.configure(state='disabled')

    def selecionar_controle(self):
        arquivo = filedialog.askopenfilename(title='Selecionar controle para leitura', filetypes=[('Planilha Excel', '*.xlsx')])
        if arquivo:
            self.controle.set(arquivo)
            self.registrar_etapa('Planilha de controle selecionada: '+Path(arquivo).name)

    def iniciar(self):
        if self.ocupado:
            return
        arquivo = self.controle.get().strip()
        controle = Path(arquivo).expanduser().resolve() if arquivo else None
        if controle is not None and not controle.is_file():
            messagebox.showerror('Controle indisponível', 'O controle selecionado não existe. Corrija o caminho antes de consultar.')
            return
        ano = 2026 if self.periodo.get() == 'Ano de 2026' else None
        self.config.update({'controle': str(controle) if controle else '', 'aba': self.aba.get().strip(), 'periodo': self.periodo.get()})
        try:
            salvar_config(self.config)
        except OSError as exc:
            messagebox.showerror('Configuração', str(exc)); return
        self.ocupado = True
        for widget in [self.consultar, self.escolher, self.campo_controle, self.campo_aba]:
            widget.configure(state='disabled')
        self.campo_periodo.configure(state='disabled')
        self.status.set('Consultando o Mediador…'); self.mostrar('Consulta em andamento. Aguarde o relatório.')
        self.atualizar_percentual({'total':None})
        self.registrar_etapa('Consulta iniciada · '+self.periodo.get())
        self.abas_resultados.select(0)
        aba = self.aba.get().strip() or None
        threading.Thread(target=self.trabalhar, args=(controle, aba, ano, self.periodo.get() == 'Ontem'), daemon=True).start()

    def trabalhar(self, controle, aba, ano=None, ontem=False):
        try:
            resultado = executar_online(controle, BASE/'saidas', aba, lambda m: self.fila.put(('progresso', m)), ano=ano, ontem=ontem)
            self.fila.put(('progresso', 'Organizando as referências documentais do painel…'))
            try:
                from analise_resultados import carregar_consulta
                resultado['dados_painel'] = carregar_consulta(resultado['pasta'])
                resultado['dados_painel']['completa'] = resultado['completa']
                # Cada execução já possui pasta própria; não altera relatórios anteriores.
                arquivo = resultado['pasta'] / 'painel_documental.json'
                if not arquivo.exists():
                    arquivo.write_text(json.dumps(resultado['dados_painel'], ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception as exc:
                resultado['dados_painel'] = {'documentos': [], 'pendencias': [
                    'Leitura para o painel não confirmada: '+type(exc).__name__+'. Os relatórios da consulta continuam disponíveis.'],
                    'completa':False,'consultada_em':'Não confirmado'}
            self.fila.put(('resultado', resultado))
        except Exception as exc:
            self.fila.put(('erro', f'Consulta não concluída: {type(exc).__name__}. Verifique permissões da pasta e instalação.'))

    def atualizar(self):
        try:
            while True:
                tipo, dado = self.fila.get_nowait()
                if tipo == 'progresso':
                    if isinstance(dado, dict):
                        self.atualizar_percentual(dado)
                    else:
                        self.status.set(dado); self.registrar_etapa(dado)
                else:
                    self.ocupado = False
                    for widget in [self.consultar, self.escolher, self.campo_controle, self.campo_aba]:
                        widget.configure(state='normal')
                    self.campo_periodo.configure(state='readonly')
                    if tipo == 'erro':
                        self.status.set('Consulta não concluída.'); self.mostrar(dado)
                        self.registrar_etapa(dado); self.indicador.set('Execução interrompida · consulta não confirmada')
                    else:
                        self.ultima_pasta = dado['pasta']; self.abrir.configure(state='normal')
                        self.dados_painel = dado.get('dados_painel')
                        self.botao_painel.configure(state='normal' if self.dados_painel else 'disabled')
                        self.status.set('Consulta concluída.' if dado['completa'] else 'Consulta com pendências. Confira o relatório e o log.')
                        self.registrar_etapa(self.status.get())
                        self.indicador.set('Execução encerrada · consulte o resultado e as pendências')
                        self.abas_resultados.select(1)
                        self.mostrar(dado['resumo']+'\n'+dado.get('relatorio', '')+'\nArquivos: '+str(dado['pasta']))
                        if dado['controle'].is_file():
                            # A próxima execução compara com a cópia cumulativa, sem tocar no original.
                            self.controle.set(str(dado['controle'].resolve()))
                            self.config['controle'] = self.controle.get()
                            try:
                                salvar_config(self.config)
                            except OSError:
                                self.status.set('Resultado salvo. Não foi possível guardar a seleção do controle para a próxima abertura.')
                        if self.dados_painel:
                            self.exibir_painel()
        except queue.Empty:
            pass
        self.root.after(100, self.atualizar)

    def abrir_resultados(self):
        if self.ultima_pasta:
            if os.name == 'nt':
                os.startfile(self.ultima_pasta.resolve())
            else:
                messagebox.showinfo('Resultados', str(self.ultima_pasta.resolve()))

    def exibir_painel(self):
        if not self.dados_painel:
            pasta = filedialog.askdirectory(title='Selecionar a pasta resultado de uma consulta salva', initialdir=BASE/'saidas')
            if not pasta:
                return
            try:
                from analise_resultados import carregar_consulta
                self.dados_painel = carregar_consulta(pasta)
            except Exception as exc:
                messagebox.showerror('Consulta salva indisponível', f'{type(exc).__name__}: {exc}. Escolha a pasta resultado que contém os relatórios de uma execução.')
                return
        from painel_resultados import PainelResultados
        def voltar():
            self.root.deiconify(); self.root.lift(); self.navegar('Início')
        try:
            PainelResultados(self.root, self.dados_painel, Cartao, voltar)
        except Exception as exc:
            messagebox.showerror('Painel indisponível', f'{type(exc).__name__}: {exc}. Os relatórios continuam em Abrir resultados.')

    def fechar(self):
        if self.ocupado:
            messagebox.showinfo('Consulta em andamento', 'Aguarde a conclusão da consulta antes de fechar.')
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        Aplicacao(root)
    except Exception as exc:
        messagebox.showerror('Não foi possível abrir o monitor', f'{type(exc).__name__}: {exc}')
        root.destroy(); return
    root.mainloop()


if __name__ == '__main__':
    main()
