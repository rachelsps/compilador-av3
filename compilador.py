import sys
import re

# Garante que os caracteres da árvore (├── └──) e acentos saiam certos no terminal do Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TIPOS_DADO = ('int', 'float', 'char', 'double')

# =====================================================================
# 1. ANALISADOR LÉXICO
# =====================================================================
# A ORDEM importa: o primeiro padrão que casar vence.
# Os padrões ERRO_* existem para NUNCA ignorar um caractere em silêncio.

TOKEN_TYPES = [
    ('COMENTARIO_LINHA',   r'//[^\n]*'),
    ('COMENTARIO_BLOCO',   r'/\*[\s\S]*?\*/'),
    ('ERRO_COMENTARIO',    r'/\*[\s\S]*'),                      # comentário sem fechar
    ('PREPROCESSADOR',     r'\#[^\n]*'),                        # #include, #define...
    ('STRING',             r'"[^"\n]*"'),
    ('ERRO_STRING',        r'"[^\n]*'),                         # string sem fechar
    ('CARACTERE',          r"'(?:\\.|[^'\\\n])'"),
    ('ERRO_IDENTIFICADOR', r'\d+[a-zA-Z_][a-zA-Z0-9_]*'),      # ex: 2abc
    ('NUMERO',             r'\b\d+(?:\.\d+)?'),
    ('PALAVRA_RESERVADA',  r'\b(?:int|float|char|double|void|return|if|else|while|for)\b'),
    ('OP_RELACIONAL',      r'==|!=|<=|>=|<|>'),
    ('OP_LOGICO',          r'&&|\|\||!'),
    ('OP_ATRIB',           r'='),
    ('OP_ARITMETICO',      r'[+\-*/%]'),
    ('PONTO_E_VIRGULA',    r';'),
    ('VIRGULA',            r','),
    ('PARENTESE_ESQ',      r'\('),
    ('PARENTESE_DIR',      r'\)'),
    ('CHAVE_ESQ',          r'\{'),
    ('CHAVE_DIR',          r'\}'),
    ('IDENTIFICADOR',      r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('ESPACO',             r'[ \t\r\f\v]+'),
    ('NOVA_LINHA',         r'\n'),
    ('ERRO_LEXICO',        r'.'),                               # qualquer outro caractere
]

MENSAGENS_ERRO_LEXICO = {
    'ERRO_COMENTARIO':    "Comentário de bloco não foi fechado",
    'ERRO_STRING':        "String não foi fechada",
    'ERRO_IDENTIFICADOR': "Identificador ou número malformado",
    'ERRO_LEXICO':        "Caractere inválido",
}


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
        self.tabela_simbolos = []   # lista com ordem de inserção
        self.erros_lexicos = []

    def tokenizar(self):
        linha = 1
        pos_inicio_linha = 0
        regex_unificada = '|'.join(f'(?P<{nome}>{padrao})' for nome, padrao in TOKEN_TYPES)

        for match in re.finditer(regex_unificada, self.codigo_fonte):
            tipo = match.lastgroup
            lexema = match.group()
            coluna = match.start() - pos_inicio_linha + 1

            if tipo == 'ESPACO':
                continue
            if tipo == 'NOVA_LINHA':
                linha += 1
                pos_inicio_linha = match.end()
                continue
            if tipo in ('COMENTARIO_LINHA', 'PREPROCESSADOR'):
                continue
            if tipo == 'COMENTARIO_BLOCO':
                # comentário de várias linhas: mantém a contagem de linhas correta
                qtd = lexema.count('\n')
                if qtd:
                    linha += qtd
                    pos_inicio_linha = match.start() + lexema.rfind('\n') + 1
                continue
            if tipo.startswith('ERRO_'):
                self.erros_lexicos.append({
                    'mensagem': MENSAGENS_ERRO_LEXICO[tipo],
                    'lexema': lexema,
                    'linha': linha,
                    'coluna': coluna,
                })
                continue

            self.tokens.append(Token(tipo, lexema, linha, coluna))

            # Tabela de Símbolos: identificadores e palavras reservadas (sem repetir)
            if tipo in ('IDENTIFICADOR', 'PALAVRA_RESERVADA'):
                if not any(item['lexema'] == lexema for item in self.tabela_simbolos):
                    self.tabela_simbolos.append({
                        'ordem': len(self.tabela_simbolos) + 1,
                        'lexema': lexema,
                        'categoria': tipo,
                        'tipo_dado': None   # preenchido quando a variável é declarada
                    })

        return self.tokens

    def exibir_tokens(self):
        print("=" * 66)
        print(" LISTA DE TOKENS (ETAPA I - LÉXICA)")
        print("=" * 66)
        print(f"{'TIPO':<22} | {'LEXEMA':<20} | {'LINHA':<6} | {'COL':<4}")
        print("-" * 66)
        for t in self.tokens:
            print(f"{t.tipo:<22} | {t.lexema:<20} | {t.linha:<6} | {t.coluna:<4}")
        print()

    def exibir_erros_lexicos(self):
        print("=" * 66)
        print(" ERROS LÉXICOS (ETAPA I - LÉXICA)")
        print("=" * 66)
        if not self.erros_lexicos:
            print("[SUCESSO] Nenhum erro léxico encontrado.")
        for e in self.erros_lexicos:
            print(f"[ERRO LÉXICO] Linha {e['linha']}, coluna {e['coluna']}: "
                  f"{e['mensagem']} -> '{e['lexema']}'")
        print()

    def exibir_tabela_simbolos(self):
        print("=" * 65)
        print(" TABELA DE SÍMBOLOS")
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

    def exibir(self, prefixo="", ultimo=True, raiz=True):
        rotulo = f"{self.tipo} ({self.valor})" if self.valor is not None else self.tipo
        if raiz:
            print(rotulo)
            novo_prefixo = ""
        else:
            print(prefixo + ("└── " if ultimo else "├── ") + rotulo)
            novo_prefixo = prefixo + ("    " if ultimo else "│   ")
        for i, filho in enumerate(self.filhos):
            filho.exibir(novo_prefixo, i == len(self.filhos) - 1, False)


# =====================================================================
# 3. ANALISADOR SINTÁTICO (DESCENDENTE RECURSIVO) + SEMÂNTICO
# =====================================================================
# Gramática (BNF) reconhecida:
#
#   <Programa>    ::= { <Declaracao> | <Atribuicao> | <Funcao> }
#   <Declaracao>  ::= <tipo> <identificador> [ "=" <Expressao> ] ";"
#   <Funcao>      ::= <tipo> <identificador> "(" ... ")"       (apenas o cabeçalho)
#   <Atribuicao>  ::= <identificador> "=" <Expressao> ";"
#   <Expressao>   ::= <termo> { ( "+" | "-" | "*" | "/" | "%" ) <termo> }
#   <termo>       ::= <identificador> | <numero> | <string> | <caractere>
#                   | "(" <Expressao> ")" | "-" <numero>
#
# Qualquer instrução fora dessa gramática (printf, if, while, return...) é
# ignorada com um AVISO, em vez de derrubar o programa.

class AnalisadorSintatico:
    def __init__(self, tokens, lexico):
        self.tokens = tokens
        self.lexico = lexico
        self.pos = 0
        self.token_atual = self.tokens[0] if self.tokens else None
        self.erros_sintaticos = []
        self.erros_semanticos = []
        self.avisos = []

    # ---------------- utilidades de navegação ----------------

    def avancar(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.token_atual = self.tokens[self.pos]
        else:
            self.token_atual = None

    def proximo(self):
        return self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None

    def ultima_linha(self):
        return self.tokens[-1].linha if self.tokens else 1

    def casar(self, tipo_esperado, lexema_esperado=None):
        esperado = f"'{lexema_esperado}'" if lexema_esperado else tipo_esperado
        if self.token_atual is None:
            raise SyntaxError(
                f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Fim inesperado do arquivo. Esperado {esperado}.")
        if self.token_atual.tipo == tipo_esperado:
            if lexema_esperado is None or self.token_atual.lexema == lexema_esperado:
                t = self.token_atual
                self.avancar()
                return t
        raise SyntaxError(
            f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Esperado {esperado}, "
            f"obtido '{self.token_atual.lexema}'.")

    def sincronizar(self):
        """Recuperação de erro: pula até depois do próximo ';' (ou até uma chave)."""
        while self.token_atual is not None:
            if self.token_atual.tipo == 'PONTO_E_VIRGULA':
                self.avancar()
                return
            if self.token_atual.tipo in ('CHAVE_ESQ', 'CHAVE_DIR'):
                return
            self.avancar()

    def ignorar_instrucao(self):
        """Pula uma instrução que a gramática simplificada não cobre."""
        inicio = self.token_atual
        self.avisos.append(
            f"[AVISO] Linha {inicio.linha}: instrução iniciada em '{inicio.lexema}' "
            f"está fora da gramática simplificada e foi ignorada.")
        while self.token_atual is not None:
            if self.token_atual.tipo == 'PONTO_E_VIRGULA':
                self.avancar()
                return
            if self.token_atual.tipo in ('CHAVE_ESQ', 'CHAVE_DIR'):
                return
            self.avancar()

    # ---------------- Tabela de Símbolos / semântica ----------------

    def buscar_simbolo(self, lexema):
        for s in self.lexico.tabela_simbolos:
            if s['lexema'] == lexema and s['categoria'] == 'IDENTIFICADOR':
                return s
        return None

    def registrar_tipo(self, tok_id, tipo, verificar_redeclaracao=True):
        simbolo = self.buscar_simbolo(tok_id.lexema)
        if simbolo is None:
            return
        if verificar_redeclaracao and simbolo['tipo_dado'] is not None:
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Variável '{tok_id.lexema}' declarada novamente na linha "
                f"{tok_id.linha} (já declarada como {simbolo['tipo_dado']}).")
            return
        if simbolo['tipo_dado'] is None:
            simbolo['tipo_dado'] = tipo

    def verificar_declarada(self, tok):
        simbolo = self.buscar_simbolo(tok.lexema)
        if simbolo is None or simbolo['tipo_dado'] is None:
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Variável '{tok.lexema}' utilizada na linha {tok.linha} "
                f"não foi declarada previamente.")

    def tipo_da_expressao(self, no):
        if no.tipo == 'NUM':
            return 'float' if '.' in no.valor else 'int'
        if no.tipo == 'STRING':
            return 'string'
        if no.tipo == 'CHAR':
            return 'char'
        if no.tipo == 'ID':
            simbolo = self.buscar_simbolo(no.valor)
            return simbolo['tipo_dado'] if simbolo else None
        if no.tipo == 'Expressao':
            tipos = [self.tipo_da_expressao(f) for f in no.filhos]
            if 'string' in tipos:
                return 'string'
            if None in tipos:
                return None
            if 'float' in tipos or 'double' in tipos:
                return 'float'
            return 'int'
        return None

    def verificar_tipos(self, tok_id, no_expr):
        """Compatibilidade de tipos em atribuições (Opção 1 do barema)."""
        simbolo = self.buscar_simbolo(tok_id.lexema)
        if simbolo is None or simbolo['tipo_dado'] is None:
            return  # já reportado como variável não declarada
        tipo_var = simbolo['tipo_dado']
        tipo_val = self.tipo_da_expressao(no_expr)
        if tipo_val is None:
            return
        if tipo_val == 'string':
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha {tok_id.linha}: "
                f"Não é possível atribuir String a um tipo {tipo_var}.")
        elif tipo_val in ('float', 'double') and tipo_var in ('int', 'char'):
            self.avisos.append(
                f"[AVISO] Linha {tok_id.linha}: atribuição de {tipo_val} a um tipo {tipo_var} "
                f"pode perder precisão.")

    # ---------------- regras da gramática ----------------

    def parse(self):
        no_programa = NoAST("Programa")
        while self.token_atual is not None:
            t = self.token_atual
            try:
                if t.tipo == 'PALAVRA_RESERVADA' and t.lexema in TIPOS_DADO:
                    no_programa.adicionar_filho(self.declaracao())
                elif t.tipo == 'IDENTIFICADOR' and self.proximo() is not None \
                        and self.proximo().tipo == 'OP_ATRIB':
                    no_programa.adicionar_filho(self.atribuicao())
                elif t.tipo in ('CHAVE_ESQ', 'CHAVE_DIR', 'PONTO_E_VIRGULA'):
                    self.avancar()
                else:
                    self.ignorar_instrucao()
            except SyntaxError as e:
                # Registra o erro e continua a análise a partir da próxima instrução
                self.erros_sintaticos.append(str(e))
                self.sincronizar()
        return no_programa

    def declaracao(self):
        tok_tipo = self.casar('PALAVRA_RESERVADA')
        tok_id = self.casar('IDENTIFICADOR')

        if self.token_atual is not None and self.token_atual.tipo == 'PARENTESE_ESQ':
            return self.funcao(tok_tipo, tok_id)

        self.registrar_tipo(tok_id, tok_tipo.lexema)

        no = NoAST("Declaracao")
        no.adicionar_filho(NoAST("TIPO", tok_tipo.lexema))
        no.adicionar_filho(NoAST("ID", tok_id.lexema))

        # Declaração com valor inicial: int x = 5;
        if self.token_atual is not None and self.token_atual.tipo == 'OP_ATRIB':
            tok_op = self.casar('OP_ATRIB', '=')
            no_expr = self.expressao()
            self.verificar_tipos(tok_id, no_expr)
            no.adicionar_filho(NoAST("OP_ATRIB", tok_op.lexema))
            no.adicionar_filho(no_expr)

        self.casar('PONTO_E_VIRGULA', ';')
        return no

    def funcao(self, tok_tipo, tok_id):
        """Reconhece só o cabeçalho: int main(int argc, char c)"""
        self.registrar_tipo(tok_id, tok_tipo.lexema)
        self.casar('PARENTESE_ESQ', '(')
        while self.token_atual is not None and self.token_atual.tipo != 'PARENTESE_DIR':
            t = self.token_atual
            self.avancar()
            if t.tipo == 'PALAVRA_RESERVADA' and t.lexema in TIPOS_DADO \
                    and self.token_atual is not None and self.token_atual.tipo == 'IDENTIFICADOR':
                self.registrar_tipo(self.token_atual, t.lexema, verificar_redeclaracao=False)
        self.casar('PARENTESE_DIR', ')')

        no = NoAST("Funcao", tok_id.lexema)
        no.adicionar_filho(NoAST("TIPO", tok_tipo.lexema))
        return no

    def atribuicao(self):
        tok_id = self.casar('IDENTIFICADOR')
        self.verificar_declarada(tok_id)

        tok_op = self.casar('OP_ATRIB', '=')
        no_expr = self.expressao()
        self.verificar_tipos(tok_id, no_expr)
        self.casar('PONTO_E_VIRGULA', ';')

        no = NoAST("Atribuicao")
        no.adicionar_filho(NoAST("ID", tok_id.lexema))
        no.adicionar_filho(NoAST("OP_ATRIB", tok_op.lexema))
        no.adicionar_filho(no_expr)
        return no

    def expressao(self):
        no = self.termo()
        while self.token_atual is not None and self.token_atual.tipo == 'OP_ARITMETICO':
            tok_op = self.casar('OP_ARITMETICO')
            no_dir = self.termo()
            novo = NoAST("Expressao", tok_op.lexema)
            novo.adicionar_filho(no)
            novo.adicionar_filho(no_dir)
            no = novo
        return no

    def termo(self):
        t = self.token_atual
        if t is None:
            raise SyntaxError(
                f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Fim inesperado do arquivo. "
                f"Esperado identificador ou número.")

        if t.tipo == 'IDENTIFICADOR':
            self.casar('IDENTIFICADOR')
            self.verificar_declarada(t)
            return NoAST("ID", t.lexema)
        if t.tipo == 'NUMERO':
            self.casar('NUMERO')
            return NoAST("NUM", t.lexema)
        if t.tipo == 'STRING':
            self.casar('STRING')
            return NoAST("STRING", t.lexema)
        if t.tipo == 'CARACTERE':
            self.casar('CARACTERE')
            return NoAST("CHAR", t.lexema)
        if t.tipo == 'PARENTESE_ESQ':
            self.casar('PARENTESE_ESQ', '(')
            no = self.expressao()
            self.casar('PARENTESE_DIR', ')')
            return no
        if t.tipo == 'OP_ARITMETICO' and t.lexema == '-' \
                and self.proximo() is not None and self.proximo().tipo == 'NUMERO':
            self.casar('OP_ARITMETICO')
            num = self.casar('NUMERO')
            return NoAST("NUM", '-' + num.lexema)

        raise SyntaxError(f"[ERRO SINTÁTICO] Linha {t.linha}: Termo inválido '{t.lexema}'.")


# =====================================================================
# EXECUÇÃO PRINCIPAL
# =====================================================================

def ler_arquivo(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8-sig') as f:
            return f.read()
    except UnicodeDecodeError:
        # arquivo salvo em ANSI/Windows-1252
        with open(caminho, 'r', encoding='latin-1') as f:
            return f.read()



def main():
    if len(sys.argv) < 2:
        print("Uso: python compilador.py <arquivo_fonte.c>")
        sys.exit(1)

    caminho_arquivo = sys.argv[1]

    try:
        codigo = ler_arquivo(caminho_arquivo)
    except Exception as e:
        print(f"Erro ao abrir arquivo: {e}")
        sys.exit(1)

    # 1. ANÁLISE LÉXICA
    analisador_lexico = AnalisadorLexico(codigo)
    analisador_lexico.tokenizar()
    analisador_lexico.exibir_tokens()
    analisador_lexico.exibir_erros_lexicos()

    # 2. ANÁLISE SINTÁTICA
    analisador_sintatico = AnalisadorSintatico(
        analisador_lexico.tokens,
        analisador_lexico
    )

    ast = analisador_sintatico.parse()

    analisador_lexico.exibir_tabela_simbolos()

    print("=" * 60)
    print(" ÁRVORE SINTÁTICA ABSTRATA - AST (ETAPA II - SINTÁTICA)")
    print("=" * 60)

    if analisador_sintatico.erros_sintaticos:
        for erro in analisador_sintatico.erros_sintaticos:
            print(erro)
        print("-" * 60)
    else:
        print("[SUCESSO] Nenhum erro sintático encontrado.")

    ast.exibir()
    print()

    # 3. ANÁLISE SEMÂNTICA
    print("=" * 60)
    print(" VALIDAÇÃO SEMÂNTICA (ETAPA III - SEMÂNTICA)")
    print("=" * 60)

    # Não considerar a análise semântica concluída
    # quando existem erros nas etapas anteriores.
    if analisador_lexico.erros_lexicos or analisador_sintatico.erros_sintaticos:
        print(
            "[AVISO] Análise semântica não concluída "
            "devido a erros nas etapas anteriores."
        )

    elif analisador_sintatico.erros_semanticos:
        for erro in analisador_sintatico.erros_semanticos:
            print(erro)

    else:
        print("[SUCESSO] Nenhuma inconsistência semântica detectada.")

    if analisador_sintatico.avisos:
        print("-" * 60)
        for aviso in analisador_sintatico.avisos:
            print(aviso)

    # RESULTADO FINAL
    print("=" * 60)
    print(" RESULTADO FINAL DA COMPILAÇÃO")
    print("=" * 60)

    if (analisador_lexico.erros_lexicos
            or analisador_sintatico.erros_sintaticos
            or analisador_sintatico.erros_semanticos):

        print("[REPROVADO] O código contém erros e precisa ser corrigido.")

    else:
        print("[APROVADO] Nenhum erro encontrado nas etapas analisadas.")

    print("=" * 60)


if __name__ == '__main__':
    main()
