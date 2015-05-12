from inspect import getsource
from importlib import import_module
from pygments.lexers import get_lexer_for_filename
from pygments.token import Token
from re import sub
import sys
sys.path.append("/Users/jamesmcnamara/workspace/sandbox/python/peacock")
from peacock import Peacock, write, format


app = Peacock()

syntax_highlighting = {
        Token.Keyword:"yellow,bold", 
        Token.Literal:"magenta", 
        Token.Text:"", 
        Token.Error:"green", 
        Token.Punctuation:"", 
        Token.Name:"cyan", 
        Token.Comment:"green", 
        Token.Operator:"", 
        Token.Escape:"", 
        Token.Generic:"", 
        Token.Other: "",
        Token: ""

    }

def parse(filename, func):
    mod_name = filename[:filename.rfind(".")]
    mod = import_module(mod_name, package=__package__)
    code = getsource(getattr(mod, func))
    lexer = get_lexer_for_filename(filename)
    output = ""
    args = []
    for tok, text in lexer.get_tokens(code):
        text = sub("(?<!\\ )\{", "{{", text)
        text = sub("(?<!\\ )\}", "}}", text)
        while tok not in syntax_highlighting: 
            tok = tok.parent
        color = syntax_highlighting[tok]
        if color == '':
            output += text
        else:
            output += "{|" + color + "}"
            args.append(text)
    return format(output, *args)

@app.init()
def init():
    app.write(format("Welcome to the {|rainbow}, the terminal method editor", 
                     "MethEd"))

@app.clear
@app.on("ctrl+r")
def read_file(current_line, cursor_pos):
    file_name = app.input()
    method = app.get_option_from_list(get_methods(file_name))
    data = parse(filename, method)
    app.write(data)


app.exit_on("ctrl+d")
app.run(interactive=True)
