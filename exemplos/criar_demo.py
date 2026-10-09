"""Gera documentos FICTÍCIOS sem acesso à internet."""
import argparse
import json
from pathlib import Path


def documento(numero='AL000001/2026', data='08/10/2026', tipo='CONVENCAO COLETIVA DE TRABALHO', local='Maceio/AL'):
    return f'DOCUMENTO FICTICIO - NAO E INSTRUMENTO OFICIAL\n{tipo} 2026/2027\nNUMERO DE REGISTRO NO MTE: {numero}\nDATA DE REGISTRO NO MTE: {data}\nCLAUSULA PRIMEIRA - ABRANGENCIA TERRITORIAL\nAbrangencia territorial em {local}.\nCLAUSULA SEGUNDA - VIGENCIA\nDados ficticios para testes.'


def pdf_ficticio(path, texto):
    stream = ('BT /F1 10 Tf 40 780 Td '+ ' '.join('('+s.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')+') Tj 0 -14 Td' for s in texto.splitlines())+' ET').encode('latin-1')
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 840] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data=b'%PDF-1.4\n'; offsets=[]
    for i,obj in enumerate(objs,1):
        offsets.append(len(data)); data+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(data); data+=b'xref\n0 6\n0000000000 65535 f \n'
    data+=b''.join(f'{o:010} 00000 n \n'.encode() for o in offsets)
    data+=f'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    with path.open('xb') as f: f.write(data)


def main():
    p=argparse.ArgumentParser(); p.add_argument('pasta',type=Path); a=p.parse_args()
    a.pasta.mkdir(parents=True,exist_ok=False)
    pdf_ficticio(a.pasta/'ficticio.pdf',documento())
    (a.pasta/'resultados.json').write_text(json.dumps({'consulta_completa':True,'instrumentos':[
        {'arquivo':'ficticio.pdf','registro':'AL000001/2026','fonte':'https://www3.mte.gov.br/sistemas/mediador/EXEMPLO-FICTICIO'}]},indent=2),encoding='utf-8')
    print('Demo fictícia criada. Use --hoje 2026-10-08. Não misture com dados oficiais.')


if __name__ == '__main__': main()
