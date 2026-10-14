"""Painel documental integrado à área central da janela principal."""
from pathlib import Path
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import analise_resultados as analise
import monitor


class PainelResultados:
    EMBUTIDO = True

    def __init__(self, parent, consulta, cartao, voltar):
        self.consulta=consulta; self.cartao=cartao; self.voltar=voltar
        self.doc=None; self.anterior=None; self.comparacao=None; self.abrindo=False
        self.root=tk.Frame(parent,background='#f0f5f7')
        self.root.pack(fill='both',expand=True)
        busca=tk.Frame(self.root,background='white',padx=20,pady=12);busca.pack(fill='x')
        self.termo=tk.StringVar()
        ttk.Label(busca,text='Categoria, sindicato, município, CNPJ ou registro',style='Card.TLabel').pack(anchor='w')
        barra=tk.Frame(busca,background='white');barra.pack(fill='x',pady=(6,0))
        self.campo_busca=ttk.Entry(barra,textvariable=self.termo);self.campo_busca.pack(side='left',fill='x',expand=True)
        self.campo_busca.bind('<Return>',lambda e:self.filtrar())
        ttk.Button(barra,text='Consultar',style='Primary.TButton',command=self.filtrar).pack(side='left',padx=8)
        ttk.Button(barra,text='Nova consulta',command=self.nova_consulta).pack(side='left')
        orientacao=ttk.Label(busca,text='A pesquisa acima filtra os documentos obtidos nesta execução. Nova consulta retorna aos filtros do Mediador.',style='Muted.TLabel',wraplength=900,justify='left')
        orientacao.pack(anchor='w',pady=(6,0))
        busca.bind('<Configure>',lambda e:orientacao.configure(wraplength=max(200,e.width-40)))
        escolha=tk.Frame(self.root,background='#f0f5f7',padx=20,pady=10);escolha.pack(fill='x')
        self.selecionado=tk.StringVar()
        self.seletor=ttk.Combobox(escolha,textvariable=self.selecionado,state='readonly',width=70)
        self.seletor.pack(side='left',fill='x',expand=True);self.seletor.bind('<<ComboboxSelected>>',lambda e:self.escolher())
        self.contagem=tk.StringVar();ttk.Label(escolha,textvariable=self.contagem,style='Footer.TLabel').pack(side='right',padx=(12,0))
        area=tk.Frame(self.root,background='#f0f5f7');area.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(area,background='#f0f5f7',highlightthickness=0)
        scroll=ttk.Scrollbar(area,command=self.canvas.yview);scroll.pack(side='right',fill='y')
        self.canvas.pack(fill='both',expand=True);self.canvas.configure(yscrollcommand=scroll.set)
        self.conteudo=tk.Frame(self.canvas,background='#f0f5f7',padx=20,pady=4)
        self.janela=self.canvas.create_window(0,0,window=self.conteudo,anchor='nw')
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.janela,width=e.width))
        self.conteudo.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.filtrar()

    def rolar(self,event):
        if isinstance(event.widget,tk.Text):return
        self.canvas.yview_scroll(-int(event.delta/120),'units')

    def novo_cartao(self,titulo):
        c=self.cartao(self.conteudo);c.pack(fill='x',pady=(0,12))
        ttk.Label(c.conteudo,text=titulo,style='Title.TLabel').pack(anchor='w',pady=(0,8))
        return c.conteudo

    def rotulo(self,parent,texto,muted=False):
        r=ttk.Label(parent,text=texto,style='Muted.TLabel' if muted else 'Card.TLabel',wraplength=850,justify='left')
        r.pack(anchor='w',fill='x',pady=3)
        parent.bind('<Configure>',lambda e:r.configure(wraplength=max(220,e.width)),add='+')
        return r

    def filtrar(self):
        self.visiveis=analise.ordenar_por_categoria(analise.pesquisar(self.consulta['documentos'],self.termo.get()))
        opcoes=[]
        for d in self.visiveis:
            categoria=d.get('categoria') or 'Categoria não localizada'
            nome=categoria[:60]+('…' if len(categoria)>60 else '')
            tipo='Aditivo de CCT' if 'Aditivo' in d['Tipo'] else 'CCT'
            opcoes.append(nome+' · '+d['Registro']+' · '+tipo)
        self.seletor.configure(values=opcoes)
        self.contagem.set(f'{len(self.visiveis)} documento(s)')
        if self.visiveis:self.seletor.current(0)
        else:self.selecionado.set('Nenhum documento disponível para este filtro')
        self.escolher()

    def escolher(self):
        i=self.seletor.current()
        self.doc=self.visiveis[i] if 0<=i<len(self.visiveis) else None
        self.anterior=None;self.comparacao=None
        for w in self.conteudo.winfo_children():w.destroy()
        self.canvas.yview_moveto(0)
        if self.doc is None:
            c=self.novo_cartao('Resultado da consulta')
            self.rotulo(c,'Nenhum documento disponível no painel. Isso não comprova ausência de instrumentos no Mediador.')
            for p in self.consulta['pendencias']:self.rotulo(c,p)
            if not self.consulta['completa']:self.rotulo(c,'Consulta incompleta: confira os relatórios e o log da execução.')
            return
        d=self.doc
        c=self.novo_cartao(d.get('categoria') or 'Categoria não localizada')
        self.rotulo(c,f"{d['Tipo']} · {d['Registro']} · registro em {d['Data de registro']}")
        identificacao=tk.Frame(c,background='white');identificacao.pack(fill='x',pady=8)
        blocos=[('Sindicato patronal',d['patronal']['nome'] if d['patronal'] else 'Não confirmado'),
                ('Sindicato profissional',d['profissional']['nome'] if d['profissional'] else 'Não confirmado'),
                ('Abrangência territorial',d['Abrangência territorial']),
                ('Data-base',d['data_base'] or 'Não confirmado'),
                ('Início da vigência documental',d['vigencia_inicio'] or 'Não confirmado'),
                ('Fim da vigência documental',d['vigencia_fim'] or 'Não confirmado')]
        for i,(nome,valor) in enumerate(blocos):
            bloco=tk.Frame(identificacao,background='white')
            bloco.grid(row=i//2,column=i%2,sticky='nsew',padx=(0,14) if i%2==0 else (14,0),pady=5)
            identificacao.columnconfigure(i%2,weight=1,uniform='identificacao')
            ttk.Label(bloco,text=nome,style='Muted.TLabel').pack(anchor='w')
            label=ttk.Label(bloco,text=valor[:240]+('…' if len(valor)>240 else ''),style='Card.TLabel',wraplength=400,justify='left')
            label.pack(anchor='w',fill='x',pady=(4,0))
            bloco.bind('<Configure>',lambda e,l=label:l.configure(wraplength=max(150,e.width)))
        for p in d['partes']:self.rotulo(c,'Entidade signatária: '+p['nome']+' · CNPJ '+p['cnpj'],True)
        self.rotulo(c,'Situação: '+d['situacao'],True)
        self.rotulo(c,'Aditivos relacionados por referência explícita: '+(', '.join(d['aditivos_relacionados']) or 'Não localizados nesta consulta; não comprova inexistência'),True)
        if d['principal']:self.rotulo(c,'Instrumento principal citado: '+d['principal'])
        if d.get('processo_principal'):self.rotulo(c,'Processo da convenção principal citado: '+d['processo_principal'])
        for ref in d['referencia_identificacao'].values():
            if ref:ttk.Button(c,text='Ver cláusula de '+ref['titulo'],command=lambda r=ref:self.ver_clausula(r)).pack(anchor='w',pady=3)
        a=self.novo_cartao('Atenção · conferência documental')
        if not self.consulta['completa']:self.rotulo(a,'Consulta incompleta. O painel contém somente os documentos efetivamente disponíveis.')
        for alerta in d['alertas']+self.consulta['pendencias']:self.rotulo(a,alerta,True)
        self.rotulo(a,'Prévia textual, sem interpretação jurídica. Condições, exceções e tabelas devem ser conferidas no texto integral.',True)
        grupos=analise.resumo_executivo(d)
        salario=self.novo_cartao('Resumo executivo · Reajuste salarial')
        self.bloco_resumo(salario,grupos['Reajuste salarial'],True)
        assist=self.novo_cartao('Resumo executivo · Contribuições assistenciais')
        for grupo in ('Empregados','Patronal','Destinação não confirmada'):
            if grupo=='Destinação não confirmada' and not grupos[grupo]:continue
            ttk.Label(assist,text=grupo,style='Title.TLabel').pack(anchor='w',pady=(8,2))
            self.bloco_resumo(assist,grupos[grupo])
        filtro=self.novo_cartao('Seções detalhadas')
        self.assunto=tk.StringVar(value='Todos os assuntos')
        seletor=ttk.Combobox(filtro,textvariable=self.assunto,state='readonly',values=['Todos os assuntos',*analise.ASSUNTOS,'Pontos de atenção','Comparativo com a convenção anterior'])
        seletor.pack(fill='x');seletor.bind('<<ComboboxSelected>>',lambda e:self.filtrar_assuntos())
        self.secoes={}
        for n,nome in enumerate([*analise.ASSUNTOS,'Pontos de atenção','Comparativo com a convenção anterior'],1):
            painel=self.cartao(self.conteudo);painel.pack(fill='x',pady=(0,12));p=painel.conteudo
            ttk.Label(p,text=f'{n}. {nome}',style='Title.TLabel').pack(anchor='w')
            itens=analise.por_assunto(d,nome)
            previa=' · '.join(x['titulo'] for x in itens[:2]) if itens else 'Sem classificação automática confirmada; confira as cláusulas originais.'
            self.rotulo(p,previa,True)
            detalhes=tk.Frame(p,background='white')
            b=ttk.Button(p,text='Ver detalhes',command=lambda f=detalhes: self.expandir(f));b.pack(anchor='w',pady=6)
            if nome=='Pontos de atenção':
                for alerta in d['alertas']:self.rotulo(detalhes,alerta)
                for cl in d['clausulas']:
                    if any(x in monitor.normalizar(cl['texto']) for x in ('EXCE','PRAZO','RESSALV','CONDIC')):
                        ttk.Button(detalhes,text='Ver cláusula '+cl['numero']+' · '+cl['titulo'],command=lambda r=cl:self.ver_clausula(r)).pack(anchor='w',pady=3)
            elif nome=='Comparativo com a convenção anterior':
                self.rotulo(detalhes,'Comparativo não realizado: nenhum documento anterior foi confirmado. A comparação é textual, sem consolidar aditivos.')
                ttk.Button(detalhes,text='Selecionar convenção anterior para comparar',command=self.comparar).pack(anchor='w',pady=5)
            else:
                for cl in itens:
                    self.rotulo(detalhes,analise.referencia(cl),True)
                    self.rotulo(detalhes,analise.previa(cl))
                    ttk.Button(detalhes,text='Ver cláusula integral',command=lambda r=cl:self.ver_clausula(r)).pack(anchor='w',pady=(2,10))
                if not itens:self.rotulo(detalhes,'Não localizado na classificação por palavras-chave. Isso não significa que a regra não existe.')
            self.secoes[nome]=(painel,detalhes,b)
        c=self.novo_cartao('Como usar este resumo')
        self.rotulo(c,'Abra Ver cláusula para conferir o texto completo, condições e exceções. Leia integralmente a convenção e seus aditivos antes de aplicar as regras. O resumo não substitui essa leitura.',True)
        c=self.novo_cartao('Informações não confirmadas')
        for alerta in d['alertas']+self.consulta['pendencias']:self.rotulo(c,alerta,True)
        for nome in ('Reajuste salarial','Empregados','Patronal'):
            if not grupos[nome]:self.rotulo(c,nome+': não localizado com segurança na extração; confira o documento.',True)
        c=self.novo_cartao('Referências')
        self.rotulo(c,f"Registro: {d['Registro']} · arquivo: {Path(d['caminho']).name}")
        self.rotulo(c,'Consulta (horário registrado no log): '+self.consulta['consultada_em']+' · Última atualização: não conhecida',True)
        self.rotulo(c,d['pagina_tipo'],True)
        self.rotulo(c,'SHA256: '+d['sha256'],True)
        ttk.Button(c,text='Abrir PDF consultado',command=lambda:self.abrir_arquivo(d['caminho'])).pack(anchor='w',pady=3)
        if d.get('original'):ttk.Button(c,text='Abrir download original do Mediador',command=lambda:self.abrir_arquivo(d['original'])).pack(anchor='w',pady=3)
        if monitor.fonte_oficial(d['fonte']):ttk.Button(c,text='Abrir referência na fonte oficial',command=lambda:webbrowser.open(d['fonte'])).pack(anchor='w',pady=3)
        self.rotulo(c,'Todos os documentos consultados: '+', '.join(x['Registro'] for x in self.consulta['documentos']),True)
        ttk.Button(c,text='Exportar resumo em PDF',command=self.exportar).pack(anchor='w',pady=5)
        if os.name=='nt':ttk.Button(c,text='Imprimir resumo',command=self.imprimir).pack(anchor='w',pady=3)
        ttk.Button(c,text='Retornar à tela inicial',command=self.nova_consulta).pack(anchor='w',pady=5)
        self.rotulo(c,'Cercont · Departamento Pessoal · Informações documentais para conferência',True)

    def bloco_resumo(self,parent,itens,reajuste=False):
        if not itens:
            self.rotulo(parent,'Não localizado com segurança na extração. Confira o documento; não representa ausência da regra.',True)
        for c in itens:
            self.rotulo(parent,analise.referencia(c),True)
            self.rotulo(parent,analise.previa(c,reajuste))
            for ponto in analise.pontos_resumo(c,reajuste):
                self.rotulo(parent,ponto['titulo']+': '+ponto['trecho'],True)
            ttk.Button(parent,text='Ver cláusula',command=lambda r=c:self.ver_clausula(r)).pack(anchor='w',pady=(2,8))

    def expandir(self,frame):
        for _,(painel,f,b) in self.secoes.items():
            if f is frame:
                if frame.winfo_manager():frame.pack_forget();b.configure(text='Ver detalhes ▾')
                else:frame.pack(fill='x');b.configure(text='Recolher detalhes ▴')
                break

    def filtrar_assuntos(self):
        for nome,(painel,_,_) in self.secoes.items():
            if self.assunto.get() in ('Todos os assuntos',nome):painel.pack(fill='x',pady=(0,12),before=self.rodape_inicio())
            else:painel.pack_forget()

    def rodape_inicio(self):
        # Os seis painéis detalhados precedem os três cartões finais.
        return self.conteudo.winfo_children()[-3]

    def ver_clausula(self,c):
        self.janela_texto(analise.referencia(c),c['texto'],c)

    def janela_texto(self,titulo,texto,clausula=None):
        janela=tk.Toplevel(self.root);janela.title(titulo)
        janela.geometry(f'{min(900,self.root.winfo_screenwidth()-80)}x{min(650,self.root.winfo_screenheight()-110)}');janela.minsize(600,400)
        rotulo=ttk.Label(janela,text=titulo,wraplength=800,justify='left');rotulo.pack(fill='x',padx=16,pady=12)
        rotulo.bind('<Configure>',lambda e:rotulo.configure(wraplength=max(200,e.width)))
        frame=tk.Frame(janela);frame.pack(fill='both',expand=True,padx=16,pady=8)
        t=tk.Text(frame,wrap='word',font=('Segoe UI',10),padx=12,pady=10);t.pack(side='left',fill='both',expand=True)
        barra=ttk.Scrollbar(frame,command=t.yview);barra.pack(side='right',fill='y');t.configure(yscrollcommand=barra.set)
        t.insert('1.0',texto);t.configure(state='disabled')
        if clausula:ttk.Button(janela,text='Abrir PDF na página '+str(clausula['pagina']),command=lambda:self.abrir_arquivo(self.doc['caminho'],clausula['pagina'])).pack(pady=10)

    def abrir_arquivo(self,caminho,pagina=None):
        try:
            p=Path(caminho).resolve()
            if not p.is_file():raise FileNotFoundError('Documento local indisponível')
            if pagina:
                aberto=webbrowser.open(p.as_uri()+'#page='+str(pagina))
                if not aberto:raise OSError('O navegador não confirmou a abertura do PDF')
            elif os.name=='nt':os.startfile(p)
            else:webbrowser.open(p.as_uri())
        except (OSError,ValueError) as exc:messagebox.showerror('Documento indisponível',str(exc),parent=self.root)

    def comparar(self):
        arquivo=filedialog.askopenfilename(parent=self.root,title='Selecionar convenção anterior',filetypes=[('Documento PDF','*.pdf')])
        if not arquivo:return
        try:
            anterior=analise.ler_documento(arquivo)
            diferencas=analise.comparar(self.doc,anterior)
            cab='Comparação textual dos documentos selecionados. Não confirma sucessão jurídica nem consolida aditivos.\n'
            if not diferencas:cab+='Nenhuma diferença textual identificada nas cláusulas segmentadas; isso não garante equivalência jurídica.'
            partes=[cab]
            for d in diferencas:
                partes+=[d['titulo']]
                for ref in (d['anterior'],d['atual']):
                    if ref:partes.append(analise.referencia(ref))
                partes.append(d['diferencas'])
            self.anterior=anterior;self.comparacao=diferencas
            self.janela_texto('Comparativo · '+anterior['Registro']+' → '+self.doc['Registro'],'\n\n'.join(partes))
        except (ValueError,OSError) as exc:messagebox.showwarning('Comparativo não confirmado',str(exc),parent=self.root)
        except Exception as exc:messagebox.showwarning('Comparativo não disponível',type(exc).__name__+': não foi possível ler o documento',parent=self.root)

    def exportar(self):
        if not self.doc:return None
        destino=filedialog.asksaveasfilename(parent=self.root,title='Exportar resumo',defaultextension='.pdf',initialfile='resumo_'+self.doc['Registro'].replace('/','_')+'.pdf',filetypes=[('PDF','*.pdf')])
        if not destino:return None
        try:
            consulta={**self.consulta,'documentos':self.consulta['documentos']+([self.anterior] if self.anterior else [])}
            p=analise.exportar_pdf(self.doc,consulta,destino)
            messagebox.showinfo('Resumo exportado',str(p),parent=self.root)
            return p
        except Exception as exc:messagebox.showerror('Exportação não concluída',str(exc),parent=self.root)
        return None

    def imprimir(self):
        p=self.exportar()
        if p:
            try:os.startfile(p,'print')
            except OSError as exc:messagebox.showerror('Impressão não iniciada',str(exc),parent=self.root)

    def nova_consulta(self):
        self.voltar()
