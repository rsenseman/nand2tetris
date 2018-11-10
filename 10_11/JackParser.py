# Developed for project 10 of nand2tetris course
from pathlib import Path
import re
import sys
from JackTokenizer import Tokenizer
from SymbolTable import SymbolTable
from JackTokenizer import Tokenizer
from xml.etree.ElementTree import ElementTree, Element, SubElement, XML, dump, tostring, tostringlist
import xml.dom.minidom as minidom

subroutines = {'constructor', 'method', 'function'}
types = {'char', 'boolean', 'int'}
builtin_constants = {'false', 'true', 'null'}

class Parser:
    def __init__(self, tokenizer):
        self.token_iter = self._process_tokenizer(tokenizer)
        self.input=None
        self.output = None
        self.depth = 0
        self.symbol_table = SymbolTable('global')
        self.tree = ElementTree()
        self.node_list = []

        return None

    def _process_tokenizer(self, tokenizer):
        # tokenizer_tokens = [token for token in tokenizer]
        # no_marks = map(lambda s: s.strip('\'').strip(), tokenizer_tokens)
        no_marks = map(lambda s: s.strip("'").strip(), tokenizer)
        token_tree = XML(''.join(no_marks))
        token_iter = token_tree.findall('.//')
        return (token for token in token_iter)

    def _open_stream(self, filename):
        self.input = open(filename, 'r', encoding='utf-8')
        return None

    def parse_to_file(self, output_path):
        for token in self.token_iter:
            self.parse(token)
        self._dump_tree(output_path)
        return None

    def parse(self, token):
        # print(token)
        value, type = self._split_token(token)

        if type == 'tokens':
            return None
        elif type == 'keyword':
            if value == 'class':
                return self._compile_class()
            elif value in {'field', 'static'}:
                return self._compile_class_var_dec(token)
            elif value in subroutines:
                return self._compile_subroutine(token)
            elif value == 'let':
                return self._compile_let()
            elif value == 'while':
                return self._compile_while()
            elif value == 'if':
                return self._compile_if()
            elif value == 'do':
                return self._compile_do()
            elif value == 'var':
                return self._compile_var_dec()
            elif value == 'return':
                return self._compile_return()
            elif value == 'this':
                return self._compile_term(value, type, True)
            elif (value in types) or (value in builtin_constants):
                return self._compile_term(value, type)
            else:
                # print(token)
                assert False, 'keyword not defined: {}'.format(value)

        elif type == 'identifier':
            return self._compile_term(value, 'identifier')

        elif type == 'symbol':
            return self._compile_term(value, type)
            # self._write_raw_token(token)

        elif 'constant' in type.lower():
            return self._compile_term(value, type)
        else:
            assert False, 'open tag not identified: {}\nFull token: {}'.format(type, token)

        return None


    def _compile_class(self):
        # self._write_open('class')
        self._open('class')

        # write class keyword
        self._add_new_token('class', 'keyword')
        # write identifier token
        self._add_next_token()
        # write open bracket
        self._add_next_token()

        token, _ = self._parse_until_closed({'}'})
        # if output:
        #     token, _ = output
        # self._write_raw_token(token)
        self._add_raw_token(token)

        self._close()
        return None

    def _compile_class_var_dec(self, token):
        self._open('classVarDec')

        self._add_raw_token(token)
        token, value = self._parse_until_closed({';'})
        self._add_raw_token(token)

        self._close()
        return None

    def _compile_subroutine(self, token):
        self._open('subroutineDec')

        # write next tokens for subroutine declaration:
        # type, returnType, name
        self._add_raw_token(token)
        self._add_next_token()
        self._add_next_token()

        self._compile_parameter_list()

        self._open('subroutineBody')
        # write opening bracket {
        self._add_next_token()
        # write variable declarations if any
        token=None
        for token in self.token_iter:
            value, type = self._split_token(token)
            if value == 'var':
                self._compile_var_dec()
            else:
                break

        # write subroutine statments
        self._compile_statements(lookahead=token)

        # close subroutineBody
        self._close()
        # close subroutineDec
        self._close()
        return None

    def _compile_parameter_list(self):
        # write open parenthesis
        self._add_next_token()
        self._open('parameterList')

        token, _ = self._parse_until_closed({')'})

        # write close parenthesis and return
        self._close()
        self._add_raw_token(token)
        return None

    def _compile_var_dec(self):
        self._open('varDec')

        self._add_new_token('var', 'keyword')
        token, value = self._parse_until_closed({';'})
        self._add_raw_token(token)

        self._close()
        return None

    def _compile_statements(self, end_set=None, lookahead=None):
        if end_set is None: end_set = {'}'}
        self._open('statements')
        if lookahead is not None:
            self.parse(lookahead)

        token, _ = self._parse_until_closed(end_set)
        # close statements
        self._close()
        self._add_raw_token(token)
        return None

    def _compile_do(self):
        self._open('doStatement')
        self._add_new_token('do', 'keyword')

        self._parse_next_token()

        # write semi-colon
        self._add_next_token()
        self._close()
        return None

    def _compile_let(self):
        self._open('letStatement')
        self._add_new_token('let', 'keyword')
        # write next tokens: identifier, =
        # or identifier[]
        self._add_next_token()
        token, value = self._add_next_token()
        if value == '[':
            token, value = self._compile_expression({']'})
            # write ']'
            self._add_raw_token(token)
            # write '='
            self._add_next_token()

        token, _ = self._compile_expression({';'})
        self._add_raw_token(token)

        self._close()
        return None

    def _compile_while(self):
        self._open('whileStatement')
        self._add_new_token('while', 'keyword')

        self._add_next_token()
        token, _ = self._compile_expression(end_set={')'})
        self._add_raw_token(token)

        self._add_next_token()
        self._compile_statements({'}'})

        self._close()
        return None

    def _compile_return(self):
        self._open('returnStatement')
        self._add_new_token('return', 'keyword')

        token, _ = self._compile_expression({';'})
        self._add_raw_token(token)

        self._close()
        return None

    def _compile_if(self):
        self._open('ifStatement')
        self._add_new_token('if', 'keyword')

        self._add_next_token()

        token, _ = self._compile_expression({')'})
        self._add_raw_token(token)

        self._add_next_token()
        self._compile_statements({'}'})

        while True:
            token = next(self.token_iter)
            value, type = self._split_token(token)

            if value in ('elif', 'else'):
                self._add_raw_token(token)
                self._compile_else()
            else:
                break

        self._close()
        self.parse(token)
        return None

    def _compile_else(self):
        self._add_next_token()
        self._compile_statements({'}'})
        return None

    def _compile_expression(self, end_set=None):
        if end_set is None: end_set=set(';,)')

        token = next(self.token_iter)
        value, type = self._split_token(token)

        if value in end_set:
            return token, value
        else:
            self._open('expression')
            # print('token: ' + token)
            token, value = self.parse(token)
            if value not in end_set:
                token, value = self._parse_until_closed(end_set)

            self._close()
        return token, value

    def _compile_term(self, value, type, is_term=False, end_set=None):
        if end_set is None: end_set=set(',;)]')
        lookahead_token = None
        lookahead_value = None

        if not is_term and self.node_list[-1].tag == 'expression':
            is_term = True

            is_first = len(self.node_list[-1].findall('./')) == 0
            is_symbol = value in '<>"&'
            is_arithmetic = value in '+*/='
            is_not_negation = value == '-' and not is_first

            if is_symbol or is_arithmetic or is_not_negation:
            # if value in {'&lt;','&gt;','&quot;','&amp;'}:
                is_term=False


        if len(self.node_list[-1].findall('./')) > 0:
            if self.node_list[-1].findall('./')[-1].text:
                if self.node_list[-1].findall('./')[-1].text in '~-':
                    is_term = True

        if is_term:
            # print('writing term')
            self._open('term')

        self._add_new_token(value, type)

        if value in set('~-'):
            lookahead_token = next(self.token_iter)
            value, type = self._split_token(lookahead_token)

            if lookahead_value == '(':
                self._compile_term('(', 'symbol')
                lookahead_token, lookahead_value = None, None
            else:
                # print(lookahead_token)
                lookahead_token, lookahead_value = self.parse(lookahead_token)
                # if output:
                #     = output
            # lookahead_value = value_match.search(lookahead_token)
            # lookahead_value = lookahead_value.group(1) if lookahead_value else None

        elif value == '(':
            lookahead_token, lookahead_value = self._compile_expression({')'})
            self._add_raw_token(lookahead_token)
            lookahead_token, lookahead_value = None, None

        elif type == 'identifier':
            lookahead_token = next(self.token_iter)
            lookahead_value, lookahead_type = self._split_token(lookahead_token)
            # If lookahead value is handled, set to None to avoid double writing

            # handle accessing an array
            if lookahead_value == '[':
                self._add_raw_token(lookahead_token)
                token, value = self._compile_expression({']'})
                self._add_raw_token(token)
                lookahead_token, lookahead_value = None, None
            # handle calling a function
            elif lookahead_value == '(':
                self._add_raw_token(lookahead_token)
                self._compile_expression_list()
                # write closing perenthesis
                lookahead_token, lookahead_value = None, None
            # handle calling a sub-routine
            elif lookahead_value == '.':
                self._add_raw_token(lookahead_token)
                self._parse_next_token()
                lookahead_token, lookahead_value = None, None

        if is_term:
            self._close()
        # print('lookahead_token: {}'.format(lookahead_token))
        # print('lookahead_value: {}'.format(lookahead_value))
        if lookahead_value:
            if lookahead_value in end_set:
                # print('returning {}, {}'.format(lookahead_token, lookahead_value))
                return lookahead_token, lookahead_value
            else:
                return self.parse(lookahead_token)
        return None, None

    def _compile_expression_list(self, end=')'):
        self._open('expressionList')
        while True:
            break_token, break_value = self._compile_expression(set(',)'))
            if break_value == end:
                break
            else:
                self._add_raw_token(break_token)

        self._close()
        self._add_new_token(end, 'symbol')
        return None


    def _parse_until_closed(self, end_set=None):
        if end_set is None: end_set = {'}'}
        for token in self.token_iter:
            # print('until closed: {}'.format(token))
            value, type = self._split_token(token)
            if value in end_set:
                # print('until closed return: {}'.format(token))
                return token, value
            else:
                output = self.parse(token)
                if output:
                    token, value = output
                    if value in end_set:
                        return token, value
                    elif value == ',':
                        self._add_raw_token(token)
        self._dump_tree()
        assert False, 'Parse until close should not reach end of method'

    def _open(self, type):
        print('open type: ' + type)
        # print('  '*self.depth + '<{}>'.format(type))
        if self.node_list:
            new_node = SubElement(self.node_list[-1], type)
        else:
            new_node = Element(type)
            self.tree._setroot(new_node)

        self.node_list.append(new_node)
        self.depth += 1

        # if new scope opened by if or while statement, open new scope
        if type in {'ifStatement', 'whileStatement'}:
            self.symbol_table = SymbolTable('ifwhile{}'.format(self.depth), self.symbol_table)

        return None

    def _close(self):
        self.depth -= 1
        last_node = self.node_list.pop()
        if (last_node.attrib.get('kind') in {'class', 'subroutine'}) or (last_node.tag in {'ifStatement', 'whileStatement'}):
            print(self.symbol_table.name + ' popped')
            for tup in [(x.name, x.type, x.kind, x.parent, x.var_num) for x in self.symbol_table.values()]:
                print(tup)
            print()
            self.symbol_table = self.symbol_table.parent_table
        return None

    def _add_new_token(self, value, token_type):
        new_element=None
        attributes = {}
        # if type is identifier, add attributes
        if token_type == 'identifier':
            # is_bering_defined disqualifiers:
            #   a) already being in the symbol table
            #   b) being in a let or do statement
            #   c) being used as an object_type to defind a new variable
            tag_set = set([node.tag for node in self.node_list])
            is_being_defined = not (
                # a
                (value in self.symbol_table) or
                # b
                (
                    ('letStatement' in tag_set) or
                    ('doStatement' in tag_set)
                ) or
                # c
                (
                    (self.node_list[-1].tag != 'class') and
                    value[0].isupper()
                )
            )
            if is_being_defined:
                attributes['kind'] = self._assign_kind()
                # print(self.symbol_table.keys())
                assert attributes['kind'], 'unrecognized kind. value: {}, type: {}, last tag: {}'.format(value, token_type, self.node_list[-1].tag)
                attributes['type'] = self._assign_type(attributes['kind'], value)
                self.symbol_table.new_symbol(value, attributes['type'], attributes['kind'])
                # if token opens new scope, create new symbol table
                # with current symbol table as the parent
                if type in {'class', 'subroutine'}:
                    self.symbol_table = SymbolTable(value, self.symbol_table)
            else:
                pass

        new_element = SubElement(self.node_list[-1], token_type, attrib=attributes)
        new_element.text = value

        print(new_element.tag, new_element.text, new_element.attrib, end='\n\n')

        return None

    def _assign_kind(self):
        parent_tag = self.node_list[-1].tag
        if parent_tag == 'class':
            return 'class'
        elif parent_tag == 'varDec':
            return 'var'
        elif parent_tag == 'classVarDec':
            class_var_category = self.node_list[-1].findall('./keyword')[0].text
            assert class_var_category in {'static', 'field'}, 'Unrecognized class_var_category: {}'.format(class_var_category)
            return class_var_category
        elif parent_tag == 'parameterList':
            return 'argument'
        elif parent_tag == 'subroutineDec':
            return 'subroutine'
        else:
            return False

    def _assign_type(self, category, value):
        print(category, value)
        if category == 'class':
            # return class name
            return value
        elif category in {'var', 'static', 'field'}:
            # second entry under parent (varDec or classVarDec) should hold var type
            # e.g. var int x, y, z;
            # e.g. var SquareGame x, y, z;
            type = self.node_list[-1].findall('./')[1].text
            return type
        elif category == 'argument':
            type = self.node_list[-1].findall('./keyword')[-1].text
            assert type in {'int', 'char', 'boolean'}, 'argument type not recognized: {}'.format(argument)
            return type
        elif category == 'subroutine':
            # it if's a subroutine, the type will be the first thing after the parent token "<subroutineDec>"
            type = self.node_list[-1].findall('./')[0].text
            assert (type in subroutines), 'Sub-routine type not recognized: {}'.format(type)
            return type
        else:
            assert False, 'category not recognized: {}'.format(category)

    def _add_raw_token(self, token):
        value, type = self._split_token(token)
        self._add_new_token(value, type)
        return None

    def _add_next_token(self):
        token = next(self.token_iter)
        value, type = self._split_token(token)
        self._add_new_token(value, type)
        return token, value

    def _parse_next_token(self):
        self.parse(next(self.token_iter))

    def _split_token(self, token):
        if token.text:
            token.text = token.text.strip()
        value, type = token.text, token.tag
        return value, type

    def _format_string(self, s):
        if s[0] == '<':
            if s[1] == '/':
                return s
            else:
                return '\n' + s
        elif s[0] == '>':
            return s
        else:
            return ' {} '.format(s)

    def _dump_tree(self, filename='/Users/rsenseman/Desktop/dump.xml'):
        with open(filename, 'w') as f:
            f.write(tostring(self.tree.getroot(), encoding='utf8').decode('utf8'))
        return None

if __name__ == '__main__':
    input_arg = sys.argv[1]

    input_path = Path(input_arg).resolve()
    output_path = input_path.with_name(input_path.stem + '_parsed.xml')

    tokenizer = Tokenizer(input_file=input_path).tokenize()

    parser = Parser(tokenizer)
    parser.parse_to_file(output_path)
