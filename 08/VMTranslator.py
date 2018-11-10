# Developed for nand2tetris course, to translate VM code into Hack Assembly code
import os
import sys
from pathlib import Path


class Parser:
    def __init__(self):
        pass

    class Line:
        def __init__(self):
            self.command_type = ''
            self.arg1 = None
            self.arg2 = None

        def __repr__(self):
            return '\n'.join([
                'command_type: ' + self.command_type,
                'arg1: ' + (self.arg1 if self.arg1 else 'None'),
                'arg2: ' + (self.arg2 if self.arg2 else 'None')
            ])

    def parse(self, line_in):
        # store line properties in new line object
        fields = line_in.split(' ')
        new_line = self.Line()

        defined_commands = [
            'push',
            'pop',
            'label',
            'goto',
            # 'if', it appears that if is always acommpanied by "-goto"
            'function',
            'return',
            'call'
        ]

        arithmetic_commands = [
            'add',
            'sub',
            'neg',
            'eq',
            'gt',
            'lt',
            'and',
            'or',
            'not'
        ]

        # make sure the command is something we are prepared for
        valid_commands = defined_commands + arithmetic_commands + ['if-goto']
        assert (fields[0] in valid_commands), "Invalid command"

        if fields[0] in defined_commands:
            new_line.command_type = fields[0]
        elif fields[0] == 'if-goto':
            new_line.command_type = 'if'
        elif fields[0] in arithmetic_commands:
            new_line.command_type = 'arithmetic'
            new_line.arg1 = fields[0]
            new_line.arg2 = None
            return new_line
        # else:
        #     new_line.command_type = 'arithmetic'

        # if the command has additional arguments, store them
        if len(fields) > 1:
            new_line.arg1 = fields[1]
        if len(fields) > 2:
            new_line.arg2 = fields[2]
        return new_line


class CodeWriter:
    def __init__(self):
        self.num_bookmarks = 0
        self.num_calls = 0
        self.num_returns = 0
        self.bootstrapped = False
        self.static_name = 'f'

    def write_code(self, line):
        self.lines = []
        # if this is the first time write_code is called,
        # generate bootstrap code (unless self.bootstrapped has been manually
        # set)
        if not self.bootstrapped:
            self._generate_bootstrap_code()
        # insert comment line before translated code
        comment_line = '// {} {} {}'.format(
            line.command_type,
            line.arg1,
            line.arg2
        )
        self.lines.append(comment_line)
        # use _code_switch to decide which translate function to use
        # then, use retrieved translate function to translate line
        translate = self._code_switch(line.command_type)
        translate(line)

        return '\n'.join(self.lines)

    def _write_custom_line(self, command_type, arg1, arg2):
        '''create new line from passed arguments'''
        line = Parser.Line()
        line.command_type = command_type
        line.arg1 = arg1
        line.arg2 = arg2
        self.write_code(line)
        return None

    def _generate_bootstrap_code(self):
        self.bootstrapped = True
        # call Sys.init
        self._write_custom_line('call',  'Sys.init', '0')

        # add SP initialization before calling Sys.init
        self.lines = [
            '// bootstrap code',
            '@256',
            'D=A',
            '@SP',
            'M=D'
        ] + self.lines

        # add infinite loop to catch the program flow in the case that
        # Sys.init returns
        self.lines.extend([
            '(INF_LOOP_POST_INIT)',
            '@INF_LOOP_POST_INIT',
            '0;JMP'
        ])

        return None

    def _code_switch(self, command):
        '''retrieve appropriate translation function given command type'''
        return getattr(self, '_'+command)

    def _arithmetic(self, line):
        operation = line.arg1

        # move pointer to end of stack
        self.lines.extend([
            '@SP',
            'A=M-1'
        ])

        if operation in ['add', 'sub', 'and', 'or']:
            self._make_arithmetic_command(operation)
        elif operation in ['eq', 'lt', 'gt']:
            self._make_comparison_command(operation)
        elif operation in ['neg', 'not']:
            self._make_invert_command(operation)

        return None

    def _make_invert_command(self, operation):
        func_map = {
            'neg': '-',
            'not': '!',
        }
        self.lines.extend([
            'M={}M'.format(func_map[operation]),
            'D=A+1',
            '@SP',
            'M=D',
        ])

    def _make_arithmetic_command(self, operation):
        func_map = {
            'add': '+',
            'sub': '-',
            'and': '&',
            'or': '|'
        }
        self.lines.extend([
            'D=M',
            'A=A-1',
            'M=M{}D'.format(func_map[operation]),
            'D=A+1',
            '@SP',
            'M=D'
        ])

    def _make_comparison_command(self, operation):
        # increment num_bookmarks to avoid bookmark collision
        self.num_bookmarks += 1

        func_map = {
            'eq': 'JNE',
            'gt': 'JLE',
            'lt': 'JGE'
        }

        # Save y-value and move pointer to x-value
        self.lines.extend([
            'D=M',
            'A=A-1'
        ])
        # make channels for failed and passed comparisons
        # can this be made into a single loop to prevent code replication?
        self.lines.extend([
            'D=M-D',
            '@FAIL{}'.format(self.num_bookmarks),
            'D;{}'.format(func_map[operation])
        ])

        # if the two are equal, continue and then skip past fail path
        # if the two are equal, get back to x address and set M=True
        self.lines.extend([
            '@SP',
            'A=M',
            'A=A-1',
            'A=A-1',
            'M=-1',
            '@POSTCOMP{}'.format(self.num_bookmarks),
            '0;JMP'
        ])

        # if comparison fails, get back to x address and set M=False
        self.lines.extend([
            '(FAIL{})'.format(self.num_bookmarks),
            '@SP',
            'A=M',
            'A=A-1',
            'A=A-1',
            'M=0'
        ])

        # After setting M appropriately, set SP to next address
        self.lines.extend([
            '(POSTCOMP{})'.format(self.num_bookmarks),
            '@SP',
            'M=M-1'
        ])
        return None

    def _push(self, line):
        source, val = line.arg1, line.arg2

        # use lower functions to retrieve value and store it in D
        if source == 'constant':
            self._push_constant(val)
        elif source in ['local', 'argument', 'this', 'that']:
            self._push_method_level(source, val)
        else:
            self._push_pointer(source, val)

        # after the value is retrieved from the source and stored in D,
        # put on top of stack and increment pointer
        self.lines.extend([
            '@SP',
            'A=M',
            'M=D',
            '@SP',
            'M=M+1'
        ])
        return None

    def _push_constant(self, val):
        self.lines.extend([
            '@{}'.format(val),
            'D=A'
        ])
        return None

    def _push_method_level(self, source, val):
        source_dict = {
            'local': 'LCL',
            'argument': 'ARG',
            'this': 'THIS',
            'that': 'THAT'
        }

        # follow pointer to retrieve value
        self.lines.extend([
            '@{}'.format(val),
            'D=A',
            '@{}'.format(source_dict[source]),
            'A=M+D',
            'D=M'
        ])
        return None

    def _push_pointer(self, source, val):

        # use source to swith between pointer source
        if source == 'pointer':
            # use val to select pointer source
            # valid values for val are 0 and 1
            pointer_source = ['THIS', 'THAT'][int(val)]
        elif source == 'temp':
            pointer_source = 5 + int(val)
        # push static
        else:
            pointer_source = '{}.{}'.format(self.static_name, val)

        self.lines.extend([
            '@{}'.format(pointer_source),
            'D=M'
        ])
        return None

    def _pop(self, line):
        # retrieve value from top of stack
        self.lines.extend([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',
        ])

        # if no line, pop is used to remove value from top of stack
        # if line, pop should store the value in the specified destination
        if line:
            destination, val = line.arg1, line.arg2
            if destination in ['pointer', 'temp', 'static']:
                self._pop_pointer(destination, val)
            elif destination in ['local', 'argument', 'this', 'that']:
                self._pop_method_level(destination, val)
        return None

    def _pop_pointer(self, destination, val):
        # use source to swith between pointer destinations
        if destination == 'pointer':
            destination = ['THIS', 'THAT'][int(val)]
        elif destination == 'temp':
            destination = 5 + int(val)
        else:
            destination = '{}.{}'.format(self.static_name, val)

        self.lines.extend([
            '@{}'.format(destination),
            'M=D'
        ])

    def _pop_method_level(self, destination, val):
        pop_dict = {
            'local': 'LCL',
            'argument': 'ARG',
            'this': 'THIS',
            'that': 'THAT'
        }
        address_increment = ['A=A+1'] * int(val)

        self.lines.extend([
            '@{}'.format(pop_dict[destination]),
            'A=M'
        ] +
            address_increment +
            [
            'M=D'
        ])

        return None

    def _label(self, line):
        label = line.arg1
        self.lines.extend([
            '({})'.format(label)
        ])
        return None

    def _goto(self, line):
        destination = line.arg1

        self.lines.extend([
            '@{}'.format(destination),
            '0;JMP'
        ])
        return None

    def _if(self, line):
        destination = line.arg1
        # use _pop to store top value on stack in D and decrement SP
        self._pop(None)
        self.lines.extend([
            '@{}'.format(destination),
            'D;JNE'
        ])
        return None

    def _function(self, line):
        name, num_local = line.arg1, line.arg2
        # for num_local, initialize to 0 and increment pointer
        increment_to_new_sp = ['M=0\nA=A+1' for i in range(int(num_local))]
        self.lines.extend([
            '({})'.format(name),
            '@SP',
            'A=M'
            ] +
            increment_to_new_sp +
            [
            'D=A',
            '@SP',
            'M=D'
        ])
        return None

    def _return(self, line):
        # get value from top of stack and put it in ARG[0]
        # then set SP to *ARG[1]
        self.lines.extend([
            '@SP',
            'A=M-1',
            'D=M',
            '@ARG',
            'A=M',
            'M=D',
            'D=A+1',
            '@SP',
            'M=D'
        ])

        # push the return address to retrieve after pointers are reset
        # leave stack pointer pointing at return address
        self.lines.extend([
            '@LCL',
            'A=M'] +
            ['A=A-1' for i in range(5)] +
            [
            'D=M',
            '@SP',
            'A=M',
            'M=D'
        ])

        # reset other pointers in reverse stack order: THAT, THIS, ARG, LCL
        for i, source in enumerate(['THAT', 'THIS', 'ARG', 'LCL']):
            self.lines.extend([
                '@LCL',
                'A=M'
                ] +
                ['A=A-1' for i in range(i+1)] +
                [
                'D=M',
                '@{}'.format(source),
                'M=D'
            ])

        # get return address from top+1 of stack, go to return address
        self.lines.extend([
            '@SP',
            'A=M',
            'A=M',
            '0;JMP'
        ])
        return None

    def _call(self, line):
        name, num_args = line.arg1, int(line.arg2)
        # if there are no args, set num. args to 1 to leave room on stack
        # for the return address
        if num_args == 0:
            self._write_custom_line('push',  'constant', '0')
            num_args = 1

        # provide returnAddress. store on top of stack and
        self.lines.extend([
            '@CALL{}'.format(self.num_calls),
            'D=A',
            '@SP',
            'A=M',
            'M=D',
            '@SP',
            'M=M+1',
        ])

        # store pointers on top of stack
        for source in ['LCL', 'ARG', 'THIS', 'THAT']:
            self._get_and_stack_pointer(source)

        # set new pointers for ARG and LCL
        decrement_to_args = ['D=D-1' for i in range(num_args + 5)]
        self.lines.extend([
            'D=M',
            '@LCL',
            'M=D',
            '@ARG'
            ] +
            decrement_to_args +
            [
            'M=D'
        ])

        # if function is sys.init, decrement SP
        # this is workaround to pass nand2tetris test scripts
        if name == 'Sys.init':
            self.lines.extend([
                '@SP',
                'M=M-1',
                '@LCL',
                'M=M-1'
            ])

        # Jump to function
        self.lines.extend([
            '@{}'.format(name),
            '0;JMP'
        ])

        # Establish bookmark to whence the return function will jump
        self.lines.extend([
            '(CALL{})'.format(self.num_calls)
        ])
        self.num_calls += 1
        return None

    def _get_and_stack_pointer(self, source):
        self.lines.extend([
            '@{}'.format(source),
            'D=M',
            '@SP',
            'A=M',
            'M=D',
            '@SP',
            'M=M+1'
        ])


def read_file(file):
    ''' Retrieve file specified on the command line and return as a list of
    lines to translate. Maintain comments and blank lines
    '''
    # read file from command line
    with open(str(file)) as f:
        vm = f.read()

    # split file into individual lines. Get rid of whitespace, comment-only
    # lines, and trailing comments
    lines = vm.split('\n')
    lines = [l.strip() for l in lines if l]

    return lines, file


def translate_lines(lines, writer=None):
    new_lines = []
    parser = Parser()
    if writer is None:
        writer = CodeWriter()

    for line in lines:
        if not line or line[:2] == '//':
            continue
        # print(line)
        parsed_line = parser.parse(line)
        # print(parsed_line)
        translated_line = writer.write_code(parsed_line)
        # print(translated_line)
        # print()
        new_lines.append(translated_line)

    return new_lines


def write_file(lines, filename):
    big_word = '\n'.join(lines)

    with open(str(filename), 'w') as f:
        f.write(big_word)


if __name__ == '__main__':
    arg = sys.argv[1]
    if arg[-3:] == '.vm':
        lines, file = read_file(arg)
        writer = CodeWriter()
        writer.bootstrapped = True
        translated_lines = translate_lines(lines, writer)
        file = file.split('.vm')[0] + '.asm'
    else:
        agg_writer = CodeWriter()
        path = Path(arg).resolve()
        files = [str(f) for f in path.glob('*.vm')]
        # print(files)
        translated_lines_agg = []

        if 'Sys.vm' in files:
            file = path / 'Sys.vm'
            filename = 'Sys'
            agg_writer.static_name = filename
            translated_lines_agg.append('\n// {}\n'.format(filename))
            lines, file = read_file(file)
            translated_lines = translate_lines(lines, agg_writer)
            translated_lines_agg.extend(translated_lines)

        files = sorted(file for file in files if file != 'Sys.vm')
        for file in files:
            filename = Path(file).stem
            agg_writer.static_name = filename
            translated_lines_agg.append('\n// {}\n'.format(file))
            lines, file = read_file(file)
            translated_lines = translate_lines(lines, agg_writer)
            translated_lines_agg.extend(translated_lines)

        translated_lines = translated_lines_agg

        filename = path.name + '.asm'
        file = path / filename
    print(file)
    write_file(translated_lines, file)
