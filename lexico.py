import sys
import re

# 1. Definição das Regras Léxicas via Expressões Regulares (Regex)
REGRAS_TOKENS = [
    ('TIPO',             r'\b(int|float|double|char|void)\b'),
    ('IDENTIFICADOR',    r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ('NUMERO',           r'\b\d+(\.\d+)?\b'),
    ('OP_ATRIBUICAO',    r'='),
    ('OP_ARITMETICO',    r'[+\-*/]'),
    ('PONTO_E_VIRGULA',  r';'),
    ('ESPACO',           r'[ \t]+'),
    ('COMENTARIO',       r'//.*'),
]

PADRAO_REGEX = '|'.join(f'(?P<{nome}>{padrao})' for nome, padrao in REGRAS_TOKENS)

class AnalisadorLexico:
    def __init__(self):
        self.tokens = []           # Lista de tokens (3,0 pontos)
        self.tabela_simbolos = {}  # Tabela de símbolos (3,0 pontos)
        self.contador_ordem = 1

    def analisar(self, codigo_fonte: str):
        linhas = codigo_fonte.splitlines()

        for num_linha, linha in enumerate(linhas, start=1):
            for match in re.finditer(PADRAO_REGEX, linha):
                tipo = match.lastgroup
                lexema = match.group()

                if tipo in ('ESPACO', 'COMENTARIO'):
                    continue

                # 1. Registra o Token na sequência
                self.tokens.append({
                    'tipo': tipo,
                    'lexema': lexema,
                    'linha': num_linha
                })

                # 2. Registra na Tabela de Símbolos
                if tipo in ('TIPO', 'IDENTIFICADOR'):
                    if lexema not in self.tabela_simbolos:
                        categoria = 'Palavra Reservada' if tipo == 'TIPO' else 'Identificador'
                        self.tabela_simbolos[lexema] = {
                            'ordem': self.contador_ordem,
                            'lexema': lexema,
                            'categoria': categoria,
                            'tipo_dado': lexema if tipo == 'TIPO' else 'indefinido'
                        }
                        self.contador_ordem += 1

    def exibir_tokens(self):
        print("\n" + "="*50)
        print("LISTA DE TOKENS GERADOS (Item I - 3,0 pts)")
        print("="*50)
        print(f"{'LINHA':<8} | {'TIPO':<18} | {'LEXEMA'}")
        print("-" * 50)
        for t in self.tokens:
            print(f"{t['linha']:<8} | {t['tipo']:<18} | {t['lexema']}")

    def exibir_tabela_simbolos(self):
        print("\n" + "="*65)
        print("TABELA DE SÍMBOLOS (Item I - 3,0 pts)")
        print("="*65)
        print(f"{'ORDEM':<6} | {'LEXEMA':<15} | {'CATEGORIA':<20} | {'TIPO DADO'}")
        print("-" * 65)
        for _, dados in self.tabela_simbolos.items():
            print(f"{dados['ordem']:<6} | {dados['lexema']:<15} | {dados['categoria']:<20} | {dados['tipo_dado']}")
        print("="*65 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python lexico.py <caminho_do_arquivo.c>")
        sys.exit(1)

    caminho_arquivo = sys.argv[1]
    
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except FileNotFoundError:
        print(f"[ERRO] Arquivo '{caminho_arquivo}' não encontrado.")
        sys.exit(1)

    analisador = AnalisadorLexico()
    analisador.analisar(conteudo)
    analisador.exibir_tokens()
    analisador.exibir_tabela_simbolos()

if __name__ == "__main__":
    main()