# Developed for project 10 of nand2tetris course
class SymbolTable(dict):
    def __init__(self, class_name, parent_table=None):
        print('new symbol table: {}'.format(class_name))
        self.parent_table = parent_table
        if parent_table:
            self.update(parent_table)
            print('inherited table: {}'.format(parent_table.name))
            print('inherited keys: {}'.format(parent_table.keys()))
        self.name = class_name
        return None

    class Symbol():
        def __init__(self, name, type, kind, parent, var_num):
            self.name = name
            self.type = type
            self.kind = kind
            self.parent = parent
            self.var_num = var_num

        def is_in_class(self, class_name):
            return self.parent == class_name

    def is_in_class(self, symbol):
        return symbol.parent == self.name

    def new_symbol(self, var_name, type, kind, parent=None):
        if not parent: parent = self.name
        var_num = len([symbol for symbol in self if self[symbol].kind == kind])
        self[var_name] = self.Symbol(var_name, type, kind, parent, var_num)
        return None
