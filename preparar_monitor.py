"""Prepara a instalação local quando necessário e abre o monitor."""
import hashlib
from pathlib import Path
import subprocess
import sys


def preparar(base):
    if sys.version_info < (3, 11):
        raise RuntimeError('Instale Python 3.11 ou mais recente pelo site python.org.')
    ambiente = base / '.venv'
    python = ambiente / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if not python.is_file():
        print('Preparando o ambiente do monitor. Aguarde…', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(ambiente)], check=True)
    requisitos = base / 'requirements.txt'
    assinatura = hashlib.sha256(requisitos.read_bytes()).hexdigest()
    marcador = ambiente / '.monitor_requisitos.sha256'
    atual = marcador.is_file() and marcador.read_text(encoding='utf-8').strip() == assinatura
    verificar = [str(python), '-c', 'import tkinter, openpyxl, pypdf, playwright.sync_api, tzdata']
    if atual:
        atual = subprocess.run(verificar, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not atual:
        print('Instalando os componentes necessários. Esta etapa precisa de internet.', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requisitos)], check=True)
        subprocess.run(verificar, check=True)
        # O Windows usa o Edge instalado; não baixa outro navegador.
        if sys.platform != 'win32':
            subprocess.run([str(python), '-m', 'playwright', 'install', 'chromium'], check=True)
        marcador.write_text(assinatura, encoding='utf-8')
    return python


def main():
    base = Path(__file__).resolve().parent
    try:
        python = preparar(base)
        return subprocess.run([str(python), str(base / 'interface.py')], cwd=base).returncode
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('\nNão foi possível preparar ou abrir o monitor.', flush=True)
        print(f'Detalhe: {exc}', flush=True)
        print('Confira a conexão com a internet e a permissão de escrita nesta pasta. '
              'O Python deve incluir Tcl/Tk. Nenhuma planilha original foi alterada.', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
