# Peacock
						             __/o'V'o\__
						          __/o \  :  / o\__
						         /o `.  \ : /  .' o\
						        _\    '. /"\ .'    /_
						       /o `-._  '\v/'  _.-` o\
						       \_     `-./ \.-`     _/
						      /o ``---._/   \_.---'' o\
						      \_________\   /_________/
						                '\_/'
						                _|_|_

Peacock is a micro-framework for terminal applications, written in Python3. Through the use of its classes and decorators, it allows you to quickly and easily build terminal apps with color and rich interactivity, such as

* Interactive menus
* Progress bars
* Custom key-bindings


## Installation
For now, the easiest way to set up Peacock, is to create a virtualenv, and clone this repo directly into the site-packages directory i.e.

```bash
virtualenv peacock
git clone https://github.com/jamesmcnamara/peacock.git peacock/libs/python3.4/site-packages/peacock
```

Don't worry, I'm working on getting distributable version into PyPI.

## Requirements
None!

## Support
Currently, Peacock only supports Python3 on OS X, however, it may work unmodified on *Nix sysems, it simply must be tested.

Python 2 support is coming, and possibly Windows in the future.

## Examples
Peacock uses a [Flask](http://flask.pocoo.org/)-style of interaction. Here's a very simple text-editing peacock app, with some custom key-binding:

```python
from peacock import Peacock, format

app = Peacock()

file_name = "/tmp/scratch.txt"

# The app.on function is used to create decorators that bind
# behavior to key-sequences
@app.on("ctrl+n")
def open_file(*args):
	global file_name
	app.save(file_name)
	file_name = app.read("What file should I open?")
	app.open(file_name)

@app.on("\")
def transpose_line(cur_line, x):
	# Each key-handler is passed the current line's text,
	# and the current cursor position in that line
	transposed_line = cur_line[x:] + cur_line[:x]
	app.delete_line()
	app.write(transposed_line)
```

## Documentation
Documentation of the public APIs for each module is included in the README for each module.

* [Peacock](https://github.com/jamesmcnamara/peacock/blob/master/PEACOCK.md)
* [Format](https://github.com/jamesmcnamara/peacock/blob/master/format/README.md)
