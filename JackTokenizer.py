# Developed for project 10 of nand2tetris course
from pathlib import Path
import sys

keywords = {
    'class',
    'constructor',
    'function',
    'method',
    'field',
    'static',
    'var',
    'int',
    'char',
    'boolean',
    'void',
    'true',
    'false',
    'null',
    'this',
    'let',
    'do',
    'if',
    'else',
    'while',
    'return'
}
symbols = set('{\}().,;+-*/&|<>=~[]')
symbol_substitutions = {
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    '&': '&amp;'
}

class Tokenizer:
    def __init__(self, input_file=None):
        self.input = None
        self.output = None
        self.stored_value = ''
        self.string_stop = None

        if input_file:
            self._open_stream(input_file)

        return None

    def _open_stream(self, filename):
        self.input = open(filename, 'r', encoding='utf-8')
        return None

    def _write_stream(self, filename):
        self.output = open(filename, 'w', encoding='utf-8')
        return None

    def tokenize(self, output_file=None):
        ''' tokenize the input stream. If an output filename is provided, save
        results to the file. Otherwise return a generator for Parser use.
        '''
        if output_file:
            self._write_stream(output_file)
            self._tokenize_to_file()
            return None
        else:
            return self._tokenization_iterator()

    def _tokenize_to_file(self):
        assert (self.output), \
            "Output must be defined to write to file"

        for token in self._tokenization_iterator():
            self.output.write(token)

        self.output.close()
        return None

    def _tokenization_iterator(self):
        yield '<tokens>\n'

        while True:
            # print('entering while loop')
            token, token_type = self._get_next_token()
            if token_type == 'EOF':
                break

            token_string = '\t<{}> {} </{}>\n'.format(token_type,
                                                      token,
                                                      token_type
                                                      )
            # print('writing {} {}'.format(token, token_type))
            yield token_string

        self.input.close()
        yield '</tokens>\n'

    def _get_next_token(self):
        terminators = {' ', '\n', ''}
        token = ''
        while True:
            # if there is a stored value, retreived during look-ahead, add that
            # to token first. Otherwise read a new value. If that new value
            # is the empty string, signifying the end of the file, return
            # 'EOF' as the token type

            if self.stored_value:
                # print(self.stored_value)
                token += self.stored_value[0]
                self.stored_value = self.stored_value[1:]
            else:
                token += self.input.read(1)
                # print(token)
                # should only hit EOF after } symbol, so there should
                # be nothing left to consume
                if token == '':
                    return (None, 'EOF')

            token = token.lstrip()
            # print(repr(token))
            if token in terminators:
                token = ''
                continue

            # if the token is a quotation mark,
            # read until the next quotation mark
            # check for EOF to avoid infinite loop
            elif token == '"':
                # strip quotation mark before continuuing
                token = ''
                while True:
                    new_char = self.input.read(1)
                    assert new_char != '', 'EOF reach while compiling string, \
                        expected closing "'

                    # if new_char is the closing quotation mark, return before
                    # appending
                    if new_char == '"':
                        return (token, 'stringConstant')

                    token += new_char
            elif token in keywords:
                return (token, 'keyword')
            elif token in symbols:
                # if token is a slash, see if it's a comment
                if token == '/':
                    new_char = self.input.read(1)
                    # if it's a comment, consume rest of line
                    # otherwise store the next character and return '/' as a symbol
                    if new_char == '/':
                        self.input.readline()
                        token = ''
                        continue
                    # it it's a multi-line comment, consume lines until end of
                    # comment of end of file
                    elif new_char == '*':
                        new_char += self.input.read(1)
                        if new_char == '**':
                            while True:
                                comment_line = self.input.readline()
                                if comment_line == '':
                                    return (None, 'EOF')
                                elif comment_line.strip()[-2:] == '*/':
                                    break
                            # reset token to empty string, continue to top
                            # of while loop
                            token = ''
                            continue
                        else:
                            self.stored_value = new_char
                    else:
                        self.stored_value = new_char
                # if symbol is not a slash, make sure it is not a reserved
                # character
                elif token in symbol_substitutions:
                    # if token is a reserved symbol, replace it with the appropriate
                    # replacement
                    token = symbol_substitutions[token]
                return (token, 'symbol')
            # if token runs into a symbol, it is an identifier. Store the
            # symbol to be handled later
            elif token[-1] in symbols.union(terminators):
                self.stored_value += token[-1]
                token = token[:-1]

                if token.isdigit():
                    return (token, 'integerConstant')
                else:
                    assert ~(token[0].isdigit()), 'identifier may not start with \
                        digit'
                    return (token, 'identifier')
        return None


if __name__ == '__main__':
    input_arg = sys.argv[1]

    input_path = Path(input_arg).resolve()
    output_path = input_path.with_name(input_path.stem + 'Trs.xml')

    tokenizer = Tokenizer(input_file=input_path)
    tokenizer.tokenize(output_path)
