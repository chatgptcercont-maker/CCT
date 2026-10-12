"""Interface manual: um clique inicia a coleta pública no Mediador."""
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

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


class Aplicacao:
    def __init__(self, root):
        self.root = root
        self.root.title('Monitor de Convenções e Aditivos — Alagoas | Cercont')
        self.root.geometry('980x740')
        self.root.minsize(860, 660)
        self.root.configure(background='#f3f4f3')
        self.configurar_estilo()
        self.fila = queue.Queue()
        self.ocupado = False
        self.ultima_pasta = None
        self.config = carregar_config()
        self.controle = tk.StringVar(value=self.config.get('controle', ''))
        self.aba = tk.StringVar(value=self.config.get('aba', ''))
        self.periodo = tk.StringVar(value=self.config.get('periodo', 'Ano de 2026'))
        self.status = tk.StringVar(value='Pronto para consultar a fonte oficial.')

        cabecalho = tk.Frame(root, background='white', padx=28, pady=16)
        cabecalho.pack(fill='x')
        marca = tk.Frame(cabecalho, background='white')
        marca.pack(side='left', padx=(0, 24))
        self.logo = None
        caminho_logo = BASE / 'assets' / 'cercont.png'
        if caminho_logo.is_file():
            try:
                original = tk.PhotoImage(master=root, file=str(caminho_logo))
                fator = max(1, (original.width()+219)//220, (original.height()+89)//90)
                self.logo = original.subsample(fator, fator)
            except tk.TclError:
                # Uma imagem inválida não impede a consulta nem afeta o controle.
                self.logo = None
        if self.logo is not None:
            tk.Label(marca, image=self.logo, background='white').pack(anchor='w')
        else:
            tk.Label(marca, text='cercont', background='white', foreground='#005952',
                     font=('Segoe UI', 25, 'bold')).pack(anchor='w')
            tk.Label(marca, text='SOLUÇÕES CONTÁBEIS', background='white', foreground='#303a37',
                     font=('Segoe UI', 9)).pack(anchor='w')
        titulos = tk.Frame(cabecalho, background='white')
        titulos.pack(side='left', fill='x', expand=True)
        tk.Label(titulos, text='DEPARTAMENTO PESSOAL', background='white', foreground='#5d6864',
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        tk.Label(titulos, text='Monitor de Convenções e Aditivos',
                 background='white', foreground='#005952',
                 font=('Segoe UI', 17, 'bold')).pack(anchor='w', pady=(6, 3))
        tk.Label(titulos, text='Alagoas e seus municípios  •  Sistema Mediador',
                 background='white', foreground='#5d6864',
                 font=('Segoe UI', 10)).pack(anchor='w')
        tk.Frame(root, background='#005952', height=3).pack(fill='x')

        frame = ttk.Frame(root, padding=(24, 18, 24, 12), style='App.TFrame')
        frame.pack(fill='both', expand=True)
        filtros = ttk.Frame(frame, padding=18, style='Card.TFrame')
        filtros.pack(fill='x')
        filtros.columnconfigure(0, weight=1)
        filtros.columnconfigure(1, weight=1)
        ttk.Label(filtros, text='Prepare sua consulta', style='Title.TLabel').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        ttk.Label(filtros, text='Período de registro', style='Card.TLabel').grid(row=1, column=0, sticky='w')
        ttk.Label(filtros, text='Aba da planilha · opcional', style='Card.TLabel').grid(row=1, column=1, sticky='w', padx=(18, 0))
        self.campo_periodo = ttk.Combobox(filtros, textvariable=self.periodo,
            values=['Ano de 2026', 'Últimos 7 dias'], state='readonly', width=28)
        self.campo_periodo.grid(row=2, column=0, sticky='ew', pady=(5, 12))
        self.campo_aba = ttk.Entry(filtros, textvariable=self.aba)
        self.campo_aba.grid(row=2, column=1, sticky='ew', padx=(18, 0), pady=(5, 12))
        ttk.Label(filtros, text='Planilha de controle · opcional na primeira consulta',
                  style='Card.TLabel').grid(row=3, column=0, columnspan=2, sticky='w')
        entrada = ttk.Frame(filtros, style='Card.TFrame')
        entrada.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(5, 7))
        self.campo_controle = ttk.Entry(entrada, textvariable=self.controle)
        self.campo_controle.pack(side='left', fill='x', expand=True)
        self.escolher = ttk.Button(entrada, text='Escolher planilha', command=self.selecionar_controle)
        self.escolher.pack(side='left', padx=(10, 0))
        ttk.Label(filtros, text='O arquivo original é preservado. Sem planilha, um novo controle será criado.',
                  style='Muted.TLabel').grid(row=5, column=0, columnspan=2, sticky='w')

        botoes = ttk.Frame(frame, style='App.TFrame')
        botoes.pack(fill='x', pady=14)
        self.consultar = ttk.Button(botoes, text='Consultar novidades', style='Primary.TButton', command=self.iniciar)
        self.consultar.pack(side='left')
        self.abrir = ttk.Button(botoes, text='Abrir resultados', command=self.abrir_resultados, state='disabled')
        self.abrir.pack(side='left', padx=10)
        ttk.Label(botoes, text='Execução manual · sem agendamento', style='Footer.TLabel').pack(side='right')

        resultados = ttk.Frame(frame, padding=16, style='Card.TFrame')
        resultados.pack(fill='both', expand=True)
        ttk.Label(resultados, text='Acompanhe a consulta', style='Title.TLabel').pack(anchor='w')
        ttk.Label(resultados, textvariable=self.status, style='Status.TLabel', wraplength=780).pack(anchor='w', pady=(6, 8))
        self.progresso = ttk.Progressbar(resultados, mode='indeterminate', style='Query.Horizontal.TProgressbar')
        self.progresso.pack(fill='x', pady=(0, 10))
        painel = ttk.Frame(resultados, style='Card.TFrame')
        painel.pack(fill='both', expand=True)
        self.texto = tk.Text(painel, wrap='word', height=10, background='#f6f8f6', foreground='#303a37',
                            font=('Segoe UI', 10), relief='flat', borderwidth=0,
                            padx=14, pady=12, spacing1=3, spacing3=5,
                            selectbackground='#cee7de', selectforeground='#005952')
        self.texto.pack(side='left', fill='both', expand=True)
        rolagem = ttk.Scrollbar(painel, command=self.texto.yview)
        rolagem.pack(side='right', fill='y')
        self.texto.configure(yscrollcommand=rolagem.set)
        ttk.Label(frame, text='CCTs e termos aditivos de CCT · acordos coletivos excluídos',
                  style='Footer.TLabel').pack(anchor='w', pady=(10, 0))
        self.mostrar('Ao clicar, o programa consulta o Mediador, obtém os documentos e gera uma nova cópia do controle.\n'
                     'Nenhum PDF ou arquivo de resultados precisa ser fornecido.\n'
                     'No Windows, uma janela do Edge será aberta e controlada pelo programa; aguarde sem fechar.\n'
                     'Se o portal bloquear o acesso, o relatório indicará consulta incompleta.\n'
                     'Sem controle selecionado, será criado um modelo novo.\n')
        root.protocol('WM_DELETE_WINDOW', self.fechar)
        root.after(100, self.atualizar)

    def configurar_estilo(self):
        estilo = ttk.Style(self.root)
        estilo.theme_use('clam')
        estilo.configure('.', font=('Segoe UI', 10))
        estilo.configure('App.TFrame', background='#f3f4f3')
        estilo.configure('Card.TFrame', background='white')
        estilo.configure('Card.TLabel', background='white', foreground='#303a37')
        estilo.configure('Title.TLabel', background='white', foreground='#005952', font=('Segoe UI', 12, 'bold'))
        estilo.configure('Muted.TLabel', background='white', foreground='#5d6864', font=('Segoe UI', 9))
        estilo.configure('Status.TLabel', background='white', foreground='#005952')
        estilo.configure('Footer.TLabel', background='#f3f4f3', foreground='#5d6864', font=('Segoe UI', 9))
        estilo.configure('TEntry', padding=7, fieldbackground='white')
        estilo.configure('TCombobox', padding=6, fieldbackground='white')
        estilo.map('TCombobox', fieldbackground=[('readonly', 'white')], foreground=[('readonly', '#303a37')])
        estilo.configure('TButton', padding=(12, 9), background='#e7eeeb', foreground='#303a37')
        estilo.map('TButton', background=[('active', '#d5e3dd')], foreground=[('disabled', '#788580')])
        estilo.configure('Primary.TButton', padding=(20, 11), background='#005952', foreground='white', font=('Segoe UI', 11, 'bold'))
        estilo.map('Primary.TButton', background=[('disabled', '#c9d9d3'), ('pressed', '#003e39'), ('active', '#006b62')],
                   foreground=[('disabled', '#5d6864'), ('!disabled', 'white')])
        estilo.configure('Query.Horizontal.TProgressbar', background='#005952', troughcolor='#e7eeeb', borderwidth=0, thickness=5)

    def mostrar(self, texto):
        self.texto.configure(state='normal'); self.texto.delete('1.0', 'end')
        self.texto.insert('1.0', texto); self.texto.configure(state='disabled')

    def selecionar_controle(self):
        arquivo = filedialog.askopenfilename(title='Selecionar controle para leitura', filetypes=[('Planilha Excel', '*.xlsx')])
        if arquivo:
            self.controle.set(arquivo)

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
        self.status.set('Consultando o Mediador…'); self.mostrar('Consulta em andamento. Aguarde o relatório.'); self.progresso.start()
        aba = self.aba.get().strip() or None
        threading.Thread(target=self.trabalhar, args=(controle, aba, ano), daemon=True).start()

    def trabalhar(self, controle, aba, ano=None):
        try:
            resultado = executar_online(controle, BASE/'saidas', aba, lambda m: self.fila.put(('progresso', m)), ano=ano)
            self.fila.put(('resultado', resultado))
        except Exception as exc:
            self.fila.put(('erro', f'Consulta não concluída: {type(exc).__name__}. Verifique permissões da pasta e instalação.'))

    def atualizar(self):
        try:
            while True:
                tipo, dado = self.fila.get_nowait()
                if tipo == 'progresso':
                    self.status.set(dado)
                else:
                    self.ocupado = False; self.progresso.stop()
                    for widget in [self.consultar, self.escolher, self.campo_controle, self.campo_aba]:
                        widget.configure(state='normal')
                    self.campo_periodo.configure(state='readonly')
                    if tipo == 'erro':
                        self.status.set('Consulta não concluída.'); self.mostrar(dado)
                    else:
                        self.ultima_pasta = dado['pasta']; self.abrir.configure(state='normal')
                        self.status.set('Consulta concluída.' if dado['completa'] else 'Consulta com pendências. Confira o relatório e o log.')
                        self.mostrar(dado['resumo']+'\n'+dado.get('relatorio', '')+'\nArquivos: '+str(dado['pasta']))
                        if dado['controle'].is_file():
                            # A próxima execução compara com a cópia cumulativa, sem tocar no original.
                            self.controle.set(str(dado['controle'].resolve()))
                            self.config['controle'] = self.controle.get()
                            try:
                                salvar_config(self.config)
                            except OSError:
                                self.status.set('Resultado salvo. Não foi possível guardar a seleção do controle para a próxima abertura.')
        except queue.Empty:
            pass
        self.root.after(100, self.atualizar)

    def abrir_resultados(self):
        if self.ultima_pasta:
            if os.name == 'nt':
                os.startfile(self.ultima_pasta.resolve())
            else:
                messagebox.showinfo('Resultados', str(self.ultima_pasta.resolve()))

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
