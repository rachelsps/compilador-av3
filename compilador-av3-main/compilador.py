import sys
import re

# pro terminal do windows mostrar a arvore e os acentos direito
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TIPOS_DADO = ('int', 'float', 'char', 'double', 'long', 'short', 'signed', 'unsigned')
MODIFICADORES = ('const', 'static')
PALAVRAS_RESERVADAS = (
    'int', 'float', 'char', 'double', 'long', 'short', 'signed', 'unsigned', 'void',
    'const', 'static', 'extern', 'register', 'volatile', 'auto',
    'struct', 'union', 'enum', 'typedef', 'sizeof',
    'return', 'if', 'else', 'while', 'for', 'do', 'switch', 'case', 'default',
    'break', 'continue', 'goto',
)
OPERADORES_RESULTADO_INT = ('==', '!=', '<', '>', '<=', '>=', '&&', '||')

# ---------- analisador léxico ----------
# a ordem importa, o primeiro padrão que casar ganha
# os ERRO_* pegam o que sobrar pra nenhum caractere sumir sem avisar

TOKEN_TYPES = [
    ('COMENTARIO_LINHA',   r'//[^\n]*'),
    ('COMENTARIO_BLOCO',   r'/\*[\s\S]*?\*/'),
    ('ERRO_COMENTARIO',    r'/\*[\s\S]*'),                      # comentário sem fechar
    ('PREPROCESSADOR',     r'\#[^\n]*'),                        # #include, #define...
    ('STRING',             r'"(?:\\.|[^"\\\n])*"'),
    ('ERRO_STRING',        r'"[^\n]*'),                         # string sem fechar
    ('CARACTERE',          r"'(?:\\.|[^'\\\n])'"),
    # numero: inteiro, decimal, hexa, 1e5, 3.5f, 10L...
    ('NUMERO',             r'(?:0[xX][0-9a-fA-F]+|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)'
                           r'[uUlLfF]*(?![a-zA-Z0-9_])'),
    ('ERRO_IDENTIFICADOR', r'\d+[a-zA-Z_][a-zA-Z0-9_]*'),      # ex: 2abc
    ('PALAVRA_RESERVADA',  r'\b(?:' + '|'.join(PALAVRAS_RESERVADAS) + r')\b'),
    ('OP_ATRIB_COMPOSTA',  r'<<=|>>=|\+=|-=|\*=|/=|%=|&=|\|=|\^='),
    ('SETA',               r'->'),
    ('OP_INCREMENTO',      r'\+\+|--'),
    ('OP_DESLOC',          r'<<|>>'),
    ('OP_RELACIONAL',      r'==|!=|<=|>=|<|>'),
    ('OP_LOGICO',          r'&&|\|\||!'),
    ('OP_BIT',             r'[&|^~]'),
    ('OP_ATRIB',           r'='),
    ('OP_ARITMETICO',      r'[+\-*/%]'),
    ('PONTO_E_VIRGULA',    r';'),
    ('VIRGULA',            r','),
    ('PARENTESE_ESQ',      r'\('),
    ('PARENTESE_DIR',      r'\)'),
    ('CHAVE_ESQ',          r'\{'),
    ('CHAVE_DIR',          r'\}'),
    ('COLCHETE_ESQ',       r'\['),
    ('COLCHETE_DIR',       r'\]'),
    ('DOIS_PONTOS',        r':'),
    ('INTERROGACAO',       r'\?'),
    ('PONTO',              r'\.'),
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
        self.tabela_simbolos = []   # guarda na ordem em que aparecem
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
                # conta as quebras de linha de dentro do comentario pra linha nao ficar errada
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
                if tipo == 'ERRO_COMENTARIO':
                    qtd = lexema.count('\n')
                    if qtd:
                        linha += qtd
                        pos_inicio_linha = match.start() + lexema.rfind('\n') + 1
                continue

            self.tokens.append(Token(tipo, lexema, linha, coluna))

            # tabela de simbolos (sem repetir)
            if tipo in ('IDENTIFICADOR', 'PALAVRA_RESERVADA'):
                if not any(item['lexema'] == lexema for item in self.tabela_simbolos):
                    self.tabela_simbolos.append({
                        'ordem': len(self.tabela_simbolos) + 1,
                        'lexema': lexema,
                        'categoria': tipo,
                        'tipo_dado': None   # o parser preenche quando declara
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
        print("=" * 70)
        print(" TABELA DE SÍMBOLOS")
        print("=" * 70)
        print(f"{'ORDEM':<6} | {'LEXEMA':<18} | {'CATEGORIA':<20} | {'TIPO':<14}")
        print("-" * 70)
        for item in self.tabela_simbolos:
            tipo_str = item['tipo_dado'] if item['tipo_dado'] else '-'
            print(f"{item['ordem']:<6} | {item['lexema']:<18} | {item['categoria']:<20} | {tipo_str:<14}")
        print()


# ---------- AST ----------

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


class AnalisadorSintatico:
    def __init__(self, tokens, lexico):
        self.tokens = tokens
        self.lexico = lexico
        self.pos = 0
        self.token_atual = self.tokens[0] if self.tokens else None
        self.erros_sintaticos = []
        self.erros_semanticos = []
        self.avisos = []
        self.escopos = [{}]            # pilha de escopos
        self.params_pendentes = {}     # parametros da funcao que vai abrir o corpo

    # --- andar pelos tokens ---

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

    def eh(self, tipo, lexema=None):
        t = self.token_atual
        return t is not None and t.tipo == tipo and (lexema is None or t.lexema == lexema)

    def eh_tipo(self):
        t = self.token_atual
        return (t is not None and t.tipo == 'PALAVRA_RESERVADA'
                and (t.lexema in TIPOS_DADO or t.lexema in MODIFICADORES))

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
        # se der erro, pula até o proximo ';' (ou até uma chave) pra continuar
        while self.token_atual is not None:
            if self.token_atual.tipo == 'PONTO_E_VIRGULA':
                self.avancar()
                return
            if self.token_atual.tipo in ('CHAVE_ESQ', 'CHAVE_DIR'):
                return
            self.avancar()

    def ignorar_instrucao(self):
        # pula o que a gramática não cobre, mas avisa
        inicio = self.token_atual
        self.avisos.append(
            f"[AVISO] Linha {inicio.linha}: instrução iniciada em '{inicio.lexema}' "
            f"está fora da gramática simplificada e foi ignorada.")
        while self.token_atual is not None:
            if self.token_atual.tipo == 'PONTO_E_VIRGULA':
                self.avancar()
                return []
            if self.token_atual.tipo in ('CHAVE_ESQ', 'CHAVE_DIR'):
                return []
            self.avancar()
        return []

    # --- tabela de símbolos / semântica ---

    def buscar_simbolo(self, lexema):
        # entrada da tabela do léxico (so pra mostrar o tipo na tabela)
        for s in self.lexico.tabela_simbolos:
            if s['lexema'] == lexema and s['categoria'] == 'IDENTIFICADOR':
                return s
        return None

    def buscar_info(self, nome):
        # procura do escopo mais de dentro pro mais de fora
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        return None

    def declarar(self, tok_id, tipo, vetor=False, funcao=False):
        escopo = self.escopos[-1]
        nome = tok_id.lexema
        if nome in escopo:
            if funcao and escopo[nome].get('funcao'):
                return  # prototipo e depois a definicao, pode
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Variável '{nome}' declarada novamente na linha "
                f"{tok_id.linha} (já declarada como {escopo[nome]['tipo']}).")
            return
        escopo[nome] = {'tipo': tipo, 'vetor': vetor, 'funcao': funcao}
        self.atualizar_tabela(nome, tipo)

    def atualizar_tabela(self, nome, tipo):
        simbolo = self.buscar_simbolo(nome)
        if simbolo is not None and simbolo['tipo_dado'] is None:
            simbolo['tipo_dado'] = tipo

    def verificar_declarada(self, tok):
        if self.buscar_info(tok.lexema) is None:
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Variável '{tok.lexema}' utilizada na linha {tok.linha} "
                f"não foi declarada previamente.")

    @staticmethod
    def categoria(tipo):
        if tipo is None:
            return None
        if tipo.endswith('*'):
            return 'ponteiro'
        palavras = tipo.split()
        if 'char' in palavras:
            return 'char'
        if 'float' in palavras or 'double' in palavras:
            return 'float'
        return 'int'

    def tipo_da_expressao(self, no):
        if no.tipo == 'NUM':
            v = no.valor.lower().lstrip('-')
            if v.startswith('0x'):
                return 'int'
            if '.' in v or 'e' in v or v.endswith('f'):
                return 'float'
            return 'int'
        if no.tipo == 'STRING':
            return 'string'
        if no.tipo == 'CHAR':
            return 'char'
        if no.tipo == 'ID':
            info = self.buscar_info(no.valor)
            if info is None:
                return None
            if info['vetor'] and not no.filhos:
                return None
            cat = self.categoria(info['tipo'])
            return None if cat == 'ponteiro' else cat
        if no.tipo == 'Unario':
            if no.valor in ('&', '*'):
                return None
            if no.valor == '!':
                return 'int'
            return self.tipo_da_expressao(no.filhos[0])
        if no.tipo == 'Expressao':
            if no.valor in OPERADORES_RESULTADO_INT:
                return 'int'
            tipos = [self.tipo_da_expressao(f) for f in no.filhos]
            if 'string' in tipos:
                return 'string'
            if None in tipos:
                return None
            if 'float' in tipos:
                return 'float'
            return 'int'
        return None

    def verificar_tipos(self, tok_id, no_expr, na_declaracao=False):
        # opção 1 do barema: tipo do valor x tipo da variável
        info = self.buscar_info(tok_id.lexema)
        if info is None:
            return  # ja deu erro de nao declarada
        tipo_var = info['tipo']
        cat = self.categoria(tipo_var)
        if cat == 'ponteiro':
            return
        tipo_val = self.tipo_da_expressao(no_expr)
        if tipo_val is None:
            return
        if tipo_val == 'string':
            if na_declaracao and info['vetor'] and cat == 'char':
                return  # char nome[10] = "ana"; pode em C
            self.erros_semanticos.append(
                f"[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha {tok_id.linha}: "
                f"Não é possível atribuir String a um tipo {tipo_var}.")
        elif tipo_val == 'float' and cat in ('int', 'char'):
            self.avisos.append(
                f"[AVISO] Linha {tok_id.linha}: atribuição de {tipo_val} a um tipo {tipo_var} "
                f"pode perder precisão.")

    # --- regras da gramática ---

    def parse(self):
        no_programa = NoAST("Programa")
        while self.token_atual is not None:
            if self.eh('CHAVE_DIR'):
                self.erros_sintaticos.append(
                    f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: "
                    f"Chave '}}' sem '{{' correspondente.")
                self.avancar()
                continue
            for n in self.instrucao_segura():
                no_programa.adicionar_filho(n)
        return no_programa

    def instrucao_segura(self):
        # roda uma instrução, se der erro sintático guarda e segue
        antes = self.pos
        try:
            return self.instrucao()
        except SyntaxError as e:
            self.erros_sintaticos.append(str(e))
            self.sincronizar()
            if self.pos == antes and self.token_atual is not None:
                self.avancar()
            return []

    def instrucao(self):
        # devolve uma lista de nós
        t = self.token_atual
        prox = self.proximo()

        if t.tipo == 'PONTO_E_VIRGULA':
            self.avancar()
            return []
        if t.tipo == 'CHAVE_ESQ':
            return [self.bloco()]
        if t.tipo == 'OP_INCREMENTO':
            return [self.incremento()]

        if t.tipo == 'PALAVRA_RESERVADA':
            if t.lexema in TIPOS_DADO or t.lexema in MODIFICADORES or t.lexema == 'void':
                return self.declaracao()
            if t.lexema in ('if', 'while', 'for'):
                return [self.controle()]
            if t.lexema == 'do':
                return [self.faca_enquanto()]
            if t.lexema == 'return':
                return [self.retorno()]
            if t.lexema in ('break', 'continue'):
                self.avancar()
                self.casar('PONTO_E_VIRGULA', ';')
                return [NoAST(t.lexema.capitalize())]
            if t.lexema == 'else':
                self.erros_sintaticos.append(
                    f"[ERRO SINTÁTICO] Linha {t.linha}: 'else' sem 'if' correspondente.")
                self.avancar()
                return []

        if t.tipo == 'IDENTIFICADOR' and prox is not None:
            if prox.tipo in ('OP_ATRIB', 'OP_ATRIB_COMPOSTA', 'COLCHETE_ESQ'):
                return [self.atribuicao()]
            if prox.tipo == 'OP_INCREMENTO':
                return [self.incremento()]
            if prox.tipo == 'PARENTESE_ESQ':
                tok_f = self.casar('IDENTIFICADOR')
                no = self.chamada(tok_f)
                self.casar('PONTO_E_VIRGULA', ';')
                return [no]

        return self.ignorar_instrucao()

    def bloco(self, params=None):
        tok_abre = self.casar('CHAVE_ESQ', '{')
        self.escopos.append(dict(params) if params else {})
        no = NoAST("Bloco")
        try:
            while True:
                if self.token_atual is None:
                    raise SyntaxError(
                        f"[ERRO SINTÁTICO] Linha {tok_abre.linha}: "
                        f"Chave '{{' aberta nesta linha não foi fechada.")
                if self.eh('CHAVE_DIR'):
                    self.avancar()
                    break
                for n in self.instrucao_segura():
                    no.adicionar_filho(n)
        finally:
            self.escopos.pop()
        return no

    def corpo(self):
        # corpo do if/else/while/for: bloco {} ou uma instrução só
        if self.token_atual is None:
            raise SyntaxError(
                f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: "
                f"Fim inesperado do arquivo. Esperado instrução ou bloco.")
        if self.eh('CHAVE_ESQ'):
            return [self.bloco()]
        return self.instrucao()

    def declaracao(self):
        # declaração de variável ou cabeçalho de função
        primeiro = self.token_atual
        palavras = []
        while (self.token_atual is not None
               and self.token_atual.tipo == 'PALAVRA_RESERVADA'
               and (self.token_atual.lexema in TIPOS_DADO
                    or self.token_atual.lexema in MODIFICADORES
                    or self.token_atual.lexema == 'void')):
            palavras.append(self.token_atual.lexema)
            self.avancar()
        if not any(p in TIPOS_DADO or p == 'void' for p in palavras):
            raise SyntaxError(
                f"[ERRO SINTÁTICO] Linha {primeiro.linha}: Esperado tipo de dado antes de "
                f"'{self.token_atual.lexema if self.token_atual else 'fim do arquivo'}'.")
        base = ' '.join(palavras)

        nos = []
        primeiro_declarador = True
        while True:
            ponteiros = 0
            while self.eh('OP_ARITMETICO', '*'):
                self.avancar()
                ponteiros += 1
            tok_id = self.casar('IDENTIFICADOR')
            tipo_decl = base + '*' * ponteiros

            if primeiro_declarador and self.eh('PARENTESE_ESQ'):
                return [self.funcao(tipo_decl, tok_id)]
            primeiro_declarador = False

            if 'void' in palavras and ponteiros == 0:
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {tok_id.linha}: "
                    f"Variável '{tok_id.lexema}' não pode ser do tipo void.")

            vetor = False
            no_vetor = None
            if self.eh('COLCHETE_ESQ'):
                self.avancar()
                tamanho = None
                if self.eh('NUMERO'):
                    tamanho = self.token_atual.lexema
                    self.avancar()
                self.casar('COLCHETE_DIR', ']')
                vetor = True
                no_vetor = NoAST("VETOR", tamanho)

            self.declarar(tok_id, tipo_decl, vetor)

            no = NoAST("Declaracao")
            no.adicionar_filho(NoAST("TIPO", tipo_decl))
            no.adicionar_filho(NoAST("ID", tok_id.lexema))
            no.adicionar_filho(no_vetor)

            # com valor inicial: int x = 5;
            if self.eh('OP_ATRIB'):
                tok_op = self.casar('OP_ATRIB', '=')
                if self.eh('CHAVE_ESQ'):
                    no_expr = self.lista_inicial()
                else:
                    no_expr = self.expressao()
                self.verificar_tipos(tok_id, no_expr, na_declaracao=True)
                no.adicionar_filho(NoAST("OP_ATRIB", tok_op.lexema))
                no.adicionar_filho(no_expr)

            nos.append(no)
            if self.eh('VIRGULA'):
                self.avancar()
                continue
            break

        self.casar('PONTO_E_VIRGULA', ';')
        return nos

    def lista_inicial(self):
        # o {1, 2, 3} de int v[3] = {1, 2, 3};
        self.casar('CHAVE_ESQ', '{')
        no = NoAST("LISTA")
        while not self.eh('CHAVE_DIR'):
            if self.token_atual is None:
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Fim inesperado do arquivo. Esperado '}}'.")
            no.adicionar_filho(self.expressao())
            if self.eh('VIRGULA'):
                self.avancar()
            elif not self.eh('CHAVE_DIR'):
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Esperado ',' ou '}}', "
                    f"obtido '{self.token_atual.lexema}'.")
        self.casar('CHAVE_DIR', '}')
        return no

    def funcao(self, tipo_str, tok_id):
        # funcao ou prototipo (o prototipo termina em ;)
        self.declarar(tok_id, tipo_str, funcao=True)
        self.casar('PARENTESE_ESQ', '(')

        no = NoAST("Funcao", tok_id.lexema)
        no.adicionar_filho(NoAST("TIPO", tipo_str))
        params = {}

        while not self.eh('PARENTESE_DIR'):
            if self.token_atual is None:
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Fim inesperado do arquivo. Esperado ')'.")
            palavras = []
            while (self.token_atual is not None
                   and self.token_atual.tipo == 'PALAVRA_RESERVADA'
                   and (self.token_atual.lexema in TIPOS_DADO
                        or self.token_atual.lexema in MODIFICADORES
                        or self.token_atual.lexema == 'void')):
                palavras.append(self.token_atual.lexema)
                self.avancar()
            if not palavras:
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Esperado tipo do parâmetro, "
                    f"obtido '{self.token_atual.lexema}'.")
            ponteiros = 0
            while self.eh('OP_ARITMETICO', '*'):
                self.avancar()
                ponteiros += 1
            tipo_p = ' '.join(palavras) + '*' * ponteiros

            if self.eh('IDENTIFICADOR'):
                tok_p = self.casar('IDENTIFICADOR')
                vetor = False
                while self.eh('COLCHETE_ESQ'):
                    self.avancar()
                    if self.eh('NUMERO'):
                        self.avancar()
                    self.casar('COLCHETE_DIR', ']')
                    vetor = True
                params[tok_p.lexema] = {'tipo': tipo_p, 'vetor': vetor, 'funcao': False}
                self.atualizar_tabela(tok_p.lexema, tipo_p)
                no.adicionar_filho(NoAST("PARAM", f"{tipo_p} {tok_p.lexema}"))

            if self.eh('VIRGULA'):
                self.avancar()
            elif not self.eh('PARENTESE_DIR'):
                if self.token_atual is None:
                    continue
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Esperado ',' ou ')', "
                    f"obtido '{self.token_atual.lexema}'.")
        self.casar('PARENTESE_DIR', ')')

        if self.eh('CHAVE_ESQ'):
            no.adicionar_filho(self.bloco(params))
        else:
            self.casar('PONTO_E_VIRGULA', ';')   # prototipo
        return no

    def atribuicao(self):
        tok_id = self.casar('IDENTIFICADOR')
        self.verificar_declarada(tok_id)

        no = NoAST("Atribuicao")
        no.adicionar_filho(NoAST("ID", tok_id.lexema))

        if self.eh('COLCHETE_ESQ'):
            self.avancar()
            indice = NoAST("INDICE")
            indice.adicionar_filho(self.expressao())
            self.casar('COLCHETE_DIR', ']')
            no.adicionar_filho(indice)

        if self.eh('OP_ATRIB') or self.eh('OP_ATRIB_COMPOSTA'):
            tok_op = self.casar(self.token_atual.tipo)
        else:
            if self.token_atual is None:
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Fim inesperado do arquivo. Esperado '='.")
            raise SyntaxError(
                f"[ERRO SINTÁTICO] Linha {self.token_atual.linha}: Esperado '=', "
                f"obtido '{self.token_atual.lexema}'.")

        no_expr = self.expressao()
        self.verificar_tipos(tok_id, no_expr)
        self.casar('PONTO_E_VIRGULA', ';')

        no.adicionar_filho(NoAST(tok_op.tipo, tok_op.lexema))
        no.adicionar_filho(no_expr)
        return no

    def incremento(self):
        # x++; x--; ++x; --x;
        prefixo = self.eh('OP_INCREMENTO')
        tok_op = self.casar('OP_INCREMENTO') if prefixo else None
        tok_id = self.casar('IDENTIFICADOR')
        self.verificar_declarada(tok_id)
        if not prefixo:
            tok_op = self.casar('OP_INCREMENTO')
        self.casar('PONTO_E_VIRGULA', ';')
        no = NoAST("Incremento")
        no.adicionar_filho(NoAST("ID", tok_id.lexema))
        no.adicionar_filho(NoAST("OP_INCREMENTO", tok_op.lexema))
        return no

    def retorno(self):
        self.casar('PALAVRA_RESERVADA', 'return')
        no = NoAST("Retorno")
        if not self.eh('PONTO_E_VIRGULA'):
            no.adicionar_filho(self.expressao())
        self.casar('PONTO_E_VIRGULA', ';')
        return no

    def ler_cabecalho(self):
        # le o que ta dentro dos parenteses do if/while/for (o '(' ja foi consumido)
        # confere se as variaveis foram declaradas e devolve o texto da condição
        profundidade = 1
        partes = []
        while True:
            t = self.token_atual
            if t is None:
                raise SyntaxError(
                    f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Parêntese '(' não foi fechado.")
            if t.tipo == 'PARENTESE_ESQ':
                profundidade += 1
            elif t.tipo == 'PARENTESE_DIR':
                profundidade -= 1
                if profundidade == 0:
                    self.avancar()
                    break
            elif t.tipo == 'IDENTIFICADOR':
                prox = self.proximo()
                if not (prox is not None and prox.tipo == 'PARENTESE_ESQ'):
                    self.verificar_declarada(t)
            partes.append(t.lexema)
            self.avancar()
        return ' '.join(partes)

    def controle(self):
        # if / while / for
        tok_kw = self.casar('PALAVRA_RESERVADA')
        nomes = {'if': 'If', 'while': 'While', 'for': 'For'}
        no = NoAST(nomes[tok_kw.lexema])
        self.casar('PARENTESE_ESQ', '(')

        escopo_for = tok_kw.lexema == 'for'
        if escopo_for:
            self.escopos.append({})   # a variavel do for so vale dentro dele
        try:
            if escopo_for and self.eh_tipo():
                for d in self.declaracao():   # for (int i = 0; ...
                    no.adicionar_filho(d)
            texto = self.ler_cabecalho()
            if texto:
                no.adicionar_filho(NoAST("CONDICAO", texto))

            for n in self.corpo():
                no.adicionar_filho(n)

            if tok_kw.lexema == 'if' and self.eh('PALAVRA_RESERVADA', 'else'):
                self.avancar()
                no_else = NoAST("Else")
                for n in self.corpo():
                    no_else.adicionar_filho(n)
                no.adicionar_filho(no_else)
        finally:
            if escopo_for:
                self.escopos.pop()
        return no

    def faca_enquanto(self):
        # do { ... } while (cond);
        self.casar('PALAVRA_RESERVADA', 'do')
        no = NoAST("DoWhile")
        for n in self.corpo():
            no.adicionar_filho(n)
        self.casar('PALAVRA_RESERVADA', 'while')
        self.casar('PARENTESE_ESQ', '(')
        texto = self.ler_cabecalho()
        self.casar('PONTO_E_VIRGULA', ';')
        no.adicionar_filho(NoAST("CONDICAO", texto))
        return no

    # --- expressões ---
    # precedência: do que liga menos pro que liga mais
    NIVEIS = [('||',), ('&&',), ('==', '!='), ('<', '>', '<=', '>='), ('+', '-'), ('*', '/', '%')]
    TIPOS_OPERADOR = ('OP_ARITMETICO', 'OP_RELACIONAL', 'OP_LOGICO')

    def expressao(self, nivel=0):
        if nivel == len(self.NIVEIS):
            return self.termo()
        no = self.expressao(nivel + 1)
        while (self.token_atual is not None
               and self.token_atual.tipo in self.TIPOS_OPERADOR
               and self.token_atual.lexema in self.NIVEIS[nivel]):
            tok_op = self.casar(self.token_atual.tipo)
            no_dir = self.expressao(nivel + 1)
            novo = NoAST("Expressao", tok_op.lexema)
            novo.adicionar_filho(no)
            novo.adicionar_filho(no_dir)
            no = novo
        return no

    def chamada(self, tok_f):
        # nome(arg1, arg2), o identificador ja foi consumido
        self.casar('PARENTESE_ESQ', '(')
        no = NoAST("Chamada", tok_f.lexema)
        if not self.eh('PARENTESE_DIR'):
            while True:
                no.adicionar_filho(self.expressao())
                if self.eh('VIRGULA'):
                    self.avancar()
                    continue
                break
        self.casar('PARENTESE_DIR', ')')
        return no

    def termo(self):
        t = self.token_atual
        if t is None:
            raise SyntaxError(
                f"[ERRO SINTÁTICO] Linha {self.ultima_linha()}: Fim inesperado do arquivo. "
                f"Esperado identificador ou número.")

        if t.tipo == 'IDENTIFICADOR':
            prox = self.proximo()
            self.casar('IDENTIFICADOR')
            if prox is not None and prox.tipo == 'PARENTESE_ESQ':
                return self.chamada(t)
            self.verificar_declarada(t)
            no = NoAST("ID", t.lexema)
            while self.eh('COLCHETE_ESQ'):
                self.avancar()
                indice = NoAST("INDICE")
                indice.adicionar_filho(self.expressao())
                self.casar('COLCHETE_DIR', ']')
                no.adicionar_filho(indice)
            return no
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
        if (t.tipo == 'OP_ARITMETICO' and t.lexema in ('-', '+', '*')) \
                or (t.tipo == 'OP_LOGICO' and t.lexema == '!') \
                or (t.tipo == 'OP_BIT' and t.lexema in ('~', '&')):
            self.avancar()
            no = NoAST("Unario", t.lexema)
            no.adicionar_filho(self.termo())
            return no

        raise SyntaxError(f"[ERRO SINTÁTICO] Linha {t.linha}: Termo inválido '{t.lexema}'.")


# ---------- main ----------

def ler_arquivo(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8-sig') as f:
            return f.read()
    except UnicodeDecodeError:
        # arquivo salvo em ANSI
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

    if not caminho_arquivo.lower().endswith('.c'):
        print("[AVISO] Este analisador foi feito para código C (arquivos .c).\n")

    # léxica
    analisador_lexico = AnalisadorLexico(codigo)
    analisador_lexico.tokenizar()
    analisador_lexico.exibir_tokens()
    analisador_lexico.exibir_erros_lexicos()

    # sintática
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

    # semântica
    print("=" * 60)
    print(" VALIDAÇÃO SEMÂNTICA (ETAPA III - SEMÂNTICA)")
    print("=" * 60)

    erros_anteriores = bool(analisador_lexico.erros_lexicos
                            or analisador_sintatico.erros_sintaticos)

    if analisador_sintatico.erros_semanticos:
        for erro in analisador_sintatico.erros_semanticos:
            print(erro)
    else:
        print("[SUCESSO] Nenhuma inconsistência semântica detectada.")

    if erros_anteriores:
        print("[AVISO] Análise semântica parcial: há erros léxicos/sintáticos, "
              "então trechos do código podem não ter sido verificados.")

    if analisador_sintatico.avisos:
        print("-" * 60)
        for aviso in analisador_sintatico.avisos:
            print(aviso)

    # resultado
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