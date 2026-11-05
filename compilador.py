import sys
import re

# =====================================================================
# 1. ANALISADOR LÉXICO
# =====================================================================

TOKEN_TYPES = [
    ('PALAVRA_RESERVADA', r'\b(int|float|char|double|void|return|if|else|while)\b'),
    ('NUMERO',            r'\b\d+(\.\d+)?\b'),
    ('OP_ATRIB',          r'='),
    ('OP_ARITMETICO',     r'[+\-*/]'),
    ('PONTO_E_VIRGULA',   r';'),
    ('PARENTESE_ESQ',     r'\('),
    ('PARENTESE_DIR',     r'\)'),
    ('IDENTIFICADOR',     r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ('ESPACO',            r'[ \t]+'),
    ('NOVA_LINHA',        r'\n'),
]

class Token:
    def __init__(self, tipo, lexema, linha, coluna):
        self.tipo = tipo
        self.lexema = lexema
        self.linha = linha
        self.coluna = coluna

    def __repr__(self):
        return f"Token({self.tipo}, '{self.lexema}', Linha {self.linha})"

class AnalisadorLexico:
    def __init__(self, codigo_fonte):
        self.codigo_fonte = codigo_fonte
        self.tokens = []
        self.tabela_simbolos = []  # Lista com ordem de inserção

    def tokenizar(self):
        linha = 1
        pos_inicio_linha = 0
        pos = 0
        regex_unificada = '|'.join(f'(?P<{nome}>{padrao})' for nome, padrao in TOKEN_TYPES)

        for match in re.finditer(regex_unificada, self.codigo_fonte):
            tipo = match.lastgroup
            lexema = match.group(tipo)
            coluna = match.start() - pos_inicio_linha + 1

            if tipo == 'ESPACO':
                continue
            elif tipo == 'NOVA_LINHA':
                linha += 1
                pos_inicio_linha = match.end()
                continue

            tok = Token(tipo, lexema, linha, coluna)
            self.tokens.append(tok)

            # Inserção na Tabela de Símbolos se for Identificador ou Palavra Reservada
            if tipo in ('IDENTIFICADOR', 'PALAVRA_RESERVADA'):
                if not any(item['lexema'] == lexema for item in self.tabela_simbolos):
                    self.tabela_simbolos.append({
                        'ordem': len(self.tabela_simbolos) + 1,
                        'lexema': lexema,
                        'categoria': tipo,
                        'tipo_dado': None  # Será preenchido na análise sintática/semântica
                    })

        return self.tokens

    def exibir_tokens(self):
        print("=" * 60)
        print(" LISTA DE TOKENS (ETAPA I - LÉXICA)")
        print("=" * 60)
        print(f"{'TIPO':<22} | {'LEXEMA':<20} | {'LINHA':<6}")
        print("-" * 60)
        for t in self.tokens:
            print(f"{t.tipo:<22} | {t.lexema:<20} | {t.linha:<6}")
        print()

    def exibir_tabela_simbolos(self):
        print("=" * 65)
        print(" TABELA DE SÍMBOLOS (ETAPA I - LÉXICA)")
        print("=" * 65)
        print(f"{'ORDEM':<6} | {'LEXEMA':<18} | {'CATEGORIA':<20} | {'TIPO':<10}")
        print("-" * 65)
        for item in self.tabela_simbolos:
            tipo_str = item['tipo_dado'] if item['tipo_dado'] else '-'
            print(f"{item['ordem']:<6} | {item['lexema']:<18} | {item['categoria']:<20} | {tipo_str:<10}")
        print()


# =====================================================================
# 2. ÁRVORE SINTÁTICA ABSTRATA (AST)
# =====================================================================

class NoAST:
    def __init__(self, tipo, valor=None):
        self.tipo = tipo
        self.valor = valor
        self.filhos = []

    def adicionar_filho(self, filho):
        if filho is not None:
            self.filhos.append(filho)

    def exibir(self, nivel=0):
        prefixo = "  " * nivel
        if self.valor is not None:
            print(f"{prefixo}{self.tipo} ({self.valor})")
        else:
            print(f"{prefixo}{self.tipo}")
        for filho in self.filhos:
            filho.exibir(nivel + 1)


# =====================================================================
# 3. ANALISADOR SINTÁTICO (PARSER DESCENDENTE RECURSIVO)
# =====================================================================

class AnalisadorSintatico:
    def __init__(self, tokens, lexico):
        self.tokens = tokens
        self.lexico = lexico
        self.pos = 0
        self.token_atual = self.tokens[0] if self.tokens else None
        self.erros_semanticos = []

    def avancar(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.token_atual = self.tokens[self.pos]
        else:
            self.token_atual = None

    def casar(self, tipo_esperado, lexema_esperado=None):
        if self.token_atual is None:
            raise SyntaxError(f"Fim inesperado de ficheiro. Esperava '{tipo_esperado}'.")
        if self.token_atual.tipo == tipo_esperado:
            if lexema_esperado is None or self.token_atual.lexema == lexema_esperado:
                t = self.token_atual
                self.avancar()
                return t
        raise SyntaxError(f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Esperado {tipo_esperado} ('{lexema_esperado}'), obtido '{self.token_atual.lexema}'.")

    def parse(self):
        no_programa = NoAST("Programa")
        while self.token_atual is not None:
            # Reconhece Declaração: int x; | float total;
            if self.token_atual.tipo == 'PALAVRA_RESERVADA' and self.token_atual.lexema in ('int', 'float', 'char', 'double'):
                no_decl = self.declaracao()
                no_programa.adicionar_filho(no_decl)
            # Reconhece Atribuição: x = a + 5;
            elif self.token_atual.tipo == 'IDENTIFICADOR':
                no_atrib = self.atribuicao()
                no_programa.adicionar_filho(no_atrib)
            else:
                self.avancar()
        return no_programa

    def declaracao(self):
        tok_tipo = self.casar('PALAVRA_RESERVADA')
        tok_id = self.casar('IDENTIFICADOR')
        self.casar('PONTO_E_VIRGULA', ';')

        # Atualiza a tabela de símbolos com o tipo declarado
        for item in self.lexico.tabela_simbolos:
            if item['lexema'] == tok_id.lexema:
                item['tipo_dado'] = tok_tipo.lexema

        no = NoAST("Declaracao")
        no.adicionar_filho(NoAST("TIPO", tok_tipo.lexema))
        no.adicionar_filho(NoAST("ID", tok_id.lexema))
        return no

    def atribuicao(self):
        tok_id = self.casar('IDENTIFICADOR')
        
        # Validação Semântica: Checagem de Variável Não Declarada no lado esquerdo
        simbolo = next((s for s in self.lexico.tabela_simbolos if s['lexema'] == tok_id.lexema and s['tipo_dado'] is not None), None)
        if not simbolo:
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Variável '{tok_id.lexema}' utilizada na linha {tok_id.linha} não foi declarada previamente."
            )

        tok_op = self.casar('OP_ATRIB', '=')
        no_expr = self.expressao()
        self.casar('PONTO_E_VIRGULA', ';')

        no = NoAST("Atribuicao")
        no.adicionar_filho(NoAST("ID", tok_id.lexema))
        no.adicionar_filho(NoAST("OP_ATRIB", tok_op.lexema))
        no.adicionar_filho(no_expr)
        return no

    def expressao(self):
        no_termo_esq = self.termo()

        if self.token_atual and self.token_atual.tipo == 'OP_ARITMETICO':
            tok_op = self.casar('OP_ARITMETICO')
            no_termo_dir = self.termo()

            no_expr = NoAST("Expressao", tok_op.lexema)
            no_expr.adicionar_filho(no_termo_esq)
            no_expr.adicionar_filho(no_termo_dir)
            return no_expr

        return no_termo_esq

    def termo(self):
        if self.token_atual.tipo == 'IDENTIFICADOR':
            tok = self.casar('IDENTIFICADOR')

            # Validação Semântica: Checagem de Variável Não Declarada nas expressões
            simbolo = next((s for s in self.lexico.tabela_simbolos if s['lexema'] == tok.lexema and s['tipo_dado'] is not None), None)
            if not simbolo:
                self.erros_semanticos.append(
                    f"[ERRO SEMÂNTICO] Variável '{tok.lexema}' utilizada na linha {tok.linha} não foi declarada previamente."
                )

            return NoAST("ID", tok.lexema)
        elif self.token_atual.tipo == 'NUMERO':
            tok = self.casar('NUMERO')
            return NoAST("NUM", tok.lexema)
        else:
            raise SyntaxError(f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Termo inválido '{self.token_atual.lexema}'.")


# =====================================================================
# EXECUÇÃO PRINCIPAL
# =====================================================================

def main():
    if len(sys.argv) < 2:
        print("Uso: python compilador.py <ficheiro_fonte.c>")
        sys.exit(1)

    caminho_arquivo = sys.argv[1]
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            codigo = f.read()
    except Exception as e:
        print(f"Erro ao abrir ficheiro: {e}")
        sys.exit(1)

    # 1. Análise Léxica
    analisador_lexico = AnalisadorLexico(codigo)
    analisador_lexico.tokenizar()
    analisador_lexico.exibir_tokens()

    # 2. Análise Sintática & Construção da AST
    analisador_sintatico = AnalisadorSintatico(analisador_lexico.tokens, analisador_lexico)
    try:
        ast = analisador_sintatico.parse()
        
        # Exibe Tabela de Símbolos preenchida com tipos
        analisador_lexico.exibir_tabela_simbolos()

        print("=" * 60)
        print(" ÁRVORE SINTÁTICA ABSTRATA - AST (ETAPA II - SINTÁTICA)")
        print("=" * 60)
        ast.exibir()
        print()

    except SyntaxError as e:
        print(e)
        sys.exit(1)

    # 3. Análise Semântica
    print("=" * 60)
    print(" VALIDAÇÃO SEMÂNTICA (ETAPA III - SEMÂNTICA)")
    print("=" * 60)
    if analisador_sintatico.erros_semanticos:
        for err in analisador_sintatico.erros_semanticos:
            print(err)
    else:
        print("[SUCESSO] Nenhuma inconsistência semântica detectada.")
    print("=" * 60)

if __name__ == '__main__':
    main()
