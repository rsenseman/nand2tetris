import sys

symbols = {
    'SP': 0,
    'LCL': 1,
    'ARG': 2,
    'THIS': 3,
    'THAT': 4,
    'R0': 0,
    'R1': 1,
    'R2': 2,
    'R3': 3,
    'R4': 4,
    'R5': 5,
    'R6': 6,
    'R7': 7,
    'R8': 8,
    'R9': 9,
    'R10': 10,
    'R11': 11,
    'R12': 12,
    'R13': 13,
    'R14': 14,
    'R15': 15,
    'SCREEN': 16384,
    'KBD': 24576
}

num_predefined_symbols = len(symbols)

jump_commands = {
    '': '000',
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111'
}


def make_destination_command(dest_code):
    ''' Take a destination code in the form ADM and return
    a code in the form 101
    '''
    return ''.join([str(int(code in dest_code)) for code in 'ADM'])


calc_commands = {
    '0': '0101010',
    '1': '0111111',
    '-1': '0111010',
    'D': '0001100',
    'A': '0110000',
    'M': '1110000',
    '!D': '0001101',
    '!A': '0110001',
    '!M': '1110001',
    '-D': '0001111',
    '-A': '0110011',
    '-M': '1110011',
    'D+1': '0011111',
    'A+1': '0110111',
    'M+1': '1110111',
    'D-1': '0001110',
    'A-1': '0110010',
    'M-1': '1110010',
    'D+A': '0000010',
    'D+M': '1000010',
    'D-A': '0010011',
    'D-M': '1010011',
    'A-D': '0000111',
    'M-D': '1000111',
    'D&A': '0000000',
    'D&M': '1000000',
    'D|A': '0010101',
    'D|M': '1010101'
}


def read_file():
    ''' Retrieve file specified on the command line and return as a list of
    lines needed for assembly
    '''
    # read file from command line
    file = sys.argv[1]
    with open(file) as f:
        asm = f.read()

    # split file into individual lines. Get rid of whitespace, comment-only
    # lines, and trailing comments
    lines = asm.split('\n')
    lines = [l.strip() for l in lines if l]
    lines = [l.split(' ')[0] for l in lines if l[:2] != '//']

    return lines, file


def assign_variables(var_list, memory_used):
    ''' After all variables are know, assign them memory locations starting
        at 16.
    '''
    current_location = 16
    for var in var_list:
        if symbols.get(var):
            continue

        while current_location in memory_used:
            current_location+=1

        memory_used.add(current_location)
        symbols[var] = current_location
        current_location+=1

    return None


def collect_symbols(asm_list):
    ''' In the first pass through the program, collect all symbols that need
        numeric value assignment. Bookmark variables like @LOOP are assigned
        values when there line is discovered. Memory variables like @i held
        in a list for assignment in assign_variables.

        This function was initially created to assign memory locations that
        avoid collision with previously assigned memory, but that turned out
        to be incompatible with the project specification. If collision
        avoidance is unnecessary, as is the case, memory_used can be done away
        with and memory variables can be assigned on discovery in the same
        manner as bookmark variables
    '''
    line_count = 0
    memory_used = set(symbols.values())
    var_list = []
    for line in asm_list:
        # each line is either a) an a-command b) a bookmark or c) a c-command

        # if the line is an a-command or a c-command, increment the
        # line counter

        if line[0] == '@':
            line_count+=1
            # if numeric address, store value in memory_used
            address = line[1:].split(' ')[0]

            # lines used to avoid collision commented out
            # if line[1].isdigit():
            #   address = int(address)
            #   memory_used.add(address)

            # if variable, store in list and assign in assign_variables
            if line[1].islower():
                if address in set(var_list):
                    continue
                else:
                    var_list.append(address)

        # If bookmark line, do not increment line count, store line location
        elif line[0] == '(':
            bookmark = line[1:-1]
            symbols[bookmark] = line_count

        # if c-command, increment line count
        else:
            line_count+=1

    # get rid of pre-defined sybols or mis-cased symbols
    var_list = [var for var in var_list if var not in symbols]
    assign_variables(var_list, memory_used)

    return None


def assemble(asm_list):
    command_list = []
    # for each line of assembly, translate to machine code
    for line in asm_list:
        # skip comments and bookmarks
        if line[:2] == '//' or line[0] == '(':
            continue
        # a-command
        if line[0] == '@':
            # if numeric adress
            address = line[1:].split(' ')[0]
            if line[1].isdigit():
                address = int(address)
                command_list.append(f'{address:b}'.zfill(16))
            # if variable
            else:
                command_list.append('{:b}'.format(symbols[address]).zfill(16))
        # c-command
        else:
            # make jump code
            jump_split = line.split(';')
            jump_code = jump_split[-1].strip() if len(jump_split) > 1 else ''
            jump_code = jump_commands[jump_code]
            line=jump_split[0]

            # make destination code
            dest_split = line.split('=')
            dest_code = dest_split[0].strip() if len(dest_split) > 1 else ''
            dest_code = make_destination_command(dest_code)
            line=dest_split[-1]

            # make calculation code
            calc_code = calc_commands[line]

            command = '111' + calc_code + dest_code + jump_code
            command_list.append(command)

    return command_list


def write_file(commands, filename):
    # combine all commands with newline seperator
    big_word = '\n'.join(all_commands)

    # write file to same path as input path
    with open(filename.split('.asm')[0] + '.hack', 'w') as f:
        f.write(big_word)


if __name__ == '__main__':
    asm_list, filename = read_file()
    collect_symbols(asm_list)
    all_commands = assemble(asm_list)
    write_file(all_commands, filename)
