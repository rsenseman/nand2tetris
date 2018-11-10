# Developed for project 10 of nand2tetris course
from JackParser import Parser
from JackTokenizer import Tokenizer

from pathlib import Path
import sys

if __name__ == '__main__':
    input_arg = sys.argv[1]

    input_path = Path(input_arg).resolve()

    files = input_path.glob('*.jack')
    for file in files:
        print(file)
        output_path = str(file.with_name(file.stem + '.xml'))

        tokenizer = Tokenizer(input_file=str(file)).tokenize()

        parser = Parser(tokenizer)
        parser.parse_to_file(output_path)
