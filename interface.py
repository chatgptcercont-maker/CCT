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
        self.root.geometry('880x640')
        self.fila = queue.Queue()
        self.ocupado = False
        self.ultima_pasta = None
        self.config = carregar_config()
        self.controle = tk.StringVar(value=self.config.get('controle', ''))
        self.aba = tk.StringVar(value=self.config.get('aba', ''))
        self.periodo = tk.StringVar(value=self.config.get('periodo', 'Ano de 2026'))
        self.status = tk.StringVar(value='Pronto para consultar a fonte oficial. Não há agendamento.')
        frame = ttk.Frame(root, padding=16); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Monitor Diário de Convenções e Aditivos — Alagoas', font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='CCTs e aditivos de CCT · abrangência em Alagoas').pack(anchor='w', pady=(4, 14))
        periodo = ttk.Frame(frame); periodo.pack(fill='x', pady=4)
        ttk.Label(periodo, text='Período de registro:').pack(side='left')
        self.campo_periodo = ttk.Combobox(periodo, textvariable=self.periodo, values=['Ano de 2026', 'Últimos 7 dias'], state='readonly', width=24)
        self.campo_periodo.pack(side='left', padx=8)
        ttk.Label(frame, text='Controle existente (opcional na primeira execução; arquivo original preservado):').pack(anchor='w')
        entrada = ttk.Frame(frame); entrada.pack(fill='x', pady=4)
        self.campo_controle = ttk.Entry(entrada, textvariable=self.controle); self.campo_controle.pack(side='left', fill='x', expand=True)
        self.escolher = ttk.Button(entrada, text='Escolher planilha', command=self.selecionar_controle); self.escolher.pack(side='left', padx=(8, 0))
        aba = ttk.Frame(frame); aba.pack(fill='x', pady=4)
        ttk.Label(aba, text='Aba (se houver mais de uma):').pack(side='left')
        self.campo_aba = ttk.Entry(aba, textvariable=self.aba, width=30); self.campo_aba.pack(side='left', padx=8)
        botoes = ttk.Frame(frame); botoes.pack(fill='x', pady=12)
        self.consultar = ttk.Button(botoes, text='Consultar novidades', command=self.iniciar); self.consultar.pack(side='left')
        self.abrir = ttk.Button(botoes, text='Abrir resultados', command=self.abrir_resultados, state='disabled'); self.abrir.pack(side='left', padx=8)
        ttk.Label(frame, textvariable=self.status, wraplength=820).pack(anchor='w', pady=4)
        self.progresso = ttk.Progressbar(frame, mode='indeterminate'); self.progresso.pack(fill='x', pady=6)
        painel = ttk.Frame(frame); painel.pack(fill='both', expand=True)
        self.texto = tk.Text(painel, wrap='word', height=20); self.texto.pack(side='left', fill='both', expand=True)
        rolagem = ttk.Scrollbar(painel, command=self.texto.yview); rolagem.pack(side='right', fill='y')
        self.texto.configure(yscrollcommand=rolagem.set)
        self.mostrar('Ao clicar, o programa consulta o Mediador, obtém os documentos e gera uma nova cópia do controle.\n'
                     'Nenhum PDF ou arquivo de resultados precisa ser fornecido.\n'
                     'No Windows, uma janela do Edge será aberta e controlada pelo programa; aguarde sem fechar.\n'
                     'Se o portal bloquear o acesso, o relatório indicará consulta incompleta.\n'
                     'Sem controle selecionado, será criado um modelo novo.\n')
        root.protocol('WM_DELETE_WINDOW', self.fechar)
        root.after(100, self.atualizar)

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
