# Peacock API
## _class_ Peacock(Thread)

The Peacock object is the public interface to this framework, and
has a [Flask](flask.pocoo.org)-esque interface. 

The Peacock object has an event loop where it listens for key events, and fires attached events. Additionally, the object has IO methods that allow you to create rich interactivity. Once created, it takes over writing and key handling from the specified TTY, so its `read()` and `write()` methods
should be used in their place.

Peacock apps are "moded" applications (users of applications like Vim will find this familiar). Key-handlers can be all attached to a single mode, or the app can create seperate modes, in which the same key sequences perform different actions. See [Modes](#_class_ Mode) for more information.

Perhaps an example will be more illustrative.

```python
""" Extremely simple Vim clone"""
app = Peacock()

# All apps by default have an "insert" and a "read" mode, with the 
# default being "insert"
normal = Mode("normal", keyboard=app.keyboard)

app.add_mode(normal)

# When no mode is specified, key bindings are attached to "insert" mode
@app.on("esc")
def enter_normal(app, *args):
	app.set_mode("normal")
	
# Modes also support the on decorator, and since they contain no reference
# to a particular app, can be shared across apps easily
@normal.on("y")
def yank_line(app, curr_line, x):
	normal.clipboard = curr_line

@normal.on("p")
def paste(app, *args):
	app.write(normal.clipboard)
	
@normal.on("I")
def enter_insert(app, *args):
	app.set_mode("insert")

```

### \_\_init\_\_(_echo=True, running=True, insert=True, line\_length=120, out=sys.stdout, debug=False_)
Constructs a Peacock object, and starts it running

| Parameter | Type | Purpose|
|-----------|------|--------|
| __echo__  | _bool_  |Are keys echoed to the terminal as they're typed
| __running__ | _bool_ | Does this app start running when initialized. (as of now `False` values are not supported)
| __insert__ | _bool_ | Should keys be inserted in front of the cursor, or should they overwrite text as they are typed
| __line\_length__ | _int_  | How many characters should be allowed in each line
| __out__ | _file_ |  What file descriptor to interact with. Shoul be a TTY or PTY that is connected to a terminal-emulator that supports ANSI control sequences
| __debug__ | _bool_ |  Doesn't actually do anything

## Mode Methods
### add\_mode(_mode, name=None_)
Adds the given mode to this app.

| Parameter | Type | Purpose|
|-----------|------|--------|
 __mode__	  |_Mode_ | The mode to add
 __name__   |_str_  | A name to assoicate to this mode (defaults to `mode.name`	
 
### set\_mode(_name_)
Activates the mode with the given name.

| Parameter | Type | Purpose|
|-----------|------|--------|
 __name__   |_str_  | The name  of a `Mode` to set as the active mode for this app


## Event Handler Methods

### on(_key, mode="insert"_)
Add "on-key" handlers to the given mode. Raises `ModeException` if 
the specified mode has not been registered with the app. 
Called with a key, (soon to support multi-key sequences), and 
returns a decorator that consumes a function, and binds the original 
key sequence to be handled by the given function in the given mode. 
By default, the function will be called with: 

* `Peacock` - a reference to the currently running app
* `str` - the text of the line that the cursor is in
* `int` - the current x position of the cursor in that line 

E.g.:

```python
app = Peacock()
@app.on("ctrl+x")
def delete_to_beginning(app, cur_line, x):
	# Deletes the text before the cursor when in insert mode 
   app.delete(x)
```   
However, by subclassing `Mode` and overriding the `handle` method, 
the key-handler function signatures can be arbitrarily customized
            
 Parameter | Type | Purpose
-----------|------|--------
 __key__ | _str_  | The key to bind behavior to.
__mode__ | _str_  | The mode to add the key-handler to

### handle(_key_)
Executes whatever action is associated with the given key by dispatching it to the first mode in the mode tree that supports a handler. This can be used to trigger execution of a bound behavior, and collect a result if the bound method returns a vlaue.

 Parameter | Type | Purpose
-----------|------|--------
 __key__ | _str_ | The key to trigger.

## IO Methods

### write(_msg_)
Writes msg to 'out' at the current cursor position. This is the
interface that should be used for all output to 'out' in lieu
of 'print', as it updates the internal representation.

 Parameter | Type | Purpose
-----------|------ |--------
 __msg__	  | _str_ | What text should be written to `out`
 
### delete(_chars_)
Delete's `chars` characters from behind the current cursor position and moves all text back.

 Parameter | Type | Purpose
-----------|-------|--------
 __chars__ | _int_ | The number of characters to delete behind the cursor
 
### reset()
Revert's the app, terminal and buffer back to its initial state.

## Cursor Methods

### save_cursor()
Returns a function which when called, returns the cursor to the _(x, y)_ position it was at when the function was created. The returned function can be
used as many times as you like.
 
### move\_cursor(_rows=0, cols=0_)
 Moves the cursor the given number of rows, THEN the given number of columns. This does NOT move the cursor to the given coordinate (rows, cols), but instead moves relatively. Any values that are too large or too small are clipped to the max possible given the constraints (i.e. x within 0 to length of line, y within 0 to length of buffer).

 Parameter | Type | Purpose
-----------|------|--------
 __rows__ | _int_ | The number of rows to offset the current cursor position by. This value may be negative to move the cursor upwards.
 __cols__ | _int_ | The number of columns to offset the current cursor position by. This value may be negative to move the cursor backwards.

### move\_cursor\_to(_x=0, y=0_)
Moves the cursor to the "absolute" x, y position. However, values are still clipped between 0 and line length for _x_, and 0 and buffer length for _y_.

 Parameter | Type | Purpose
-----------|------|--------
 __x__ | _int_ | The x-coordinate to move the cursor to. Any value larger than the length of the _y_ th line will move the cursor to EOL, and any negative values will move it to 0. 
 __y__ | _int_ | The y-coordinate to move the cursor to. Any value larger than the length of the buffer will move the cursor to EOF, and any negative values will move it to 0. 
### move\_cursor\_to\_x(_x=0_)
Moves the cursor to the "absolute" x position in the current line. However, values are still clipped between 0 and line length.

 Parameter | Type | Purpose
-----------|------|--------
 __x__ | _int_ | The x-coordinate to move the cursor to. Any value larger than the length of the current line will move the cursor to EOL, and any negative values will move it to 0. 
 
### move\_cursor\_to\_eol(_rows=0_)
Moves the cursor to the end of the line of the line that is `rows` displaced
from the current position. Still capped between 0 length buffer. So `app.move_cursor_to_eol(-3)` moves it to EOL of the 3 lines before the current position.

 Parameter | Type | Purpose
-----------|------|--------
 __rows__ | _int_ | The relative line to move the cursor to the end of. Any value larger than the relative size of the buffer, will move it to the beginning or end of the buffer, depending on sign.
 
### move\_cursor\_to\_beginning(_rows=0_)
Moves the cursor to the beginning of the line of the line that is `rows` displaced from the current position. Still capped between 0 length buffer. So `app.move_cursor_to_beginning(-3)` moves it to beginning of the 3 lines before the current position.

 Parameter | Type | Purpose
-----------|------|--------
 __rows__ | _int_ | The relative line to move the cursor to the beginning of. Any value larger than the relative size of the buffer, will move it to the beginning or end of the buffer, depending on sign.

### stop()
Stops the app from running and clears out terminal text.

##_class_ Mode
`Modes` are what key-handlers are attached to in a `Peacock` application.
A mode is simply an object which can have key-handlers attached to it,
and has the ability to dispatch a call to one of those handlers, with 
whatever arguments the developer chooses (the default is a reference 
to the calling Peacock applications, the current cursor line, and the 
x-position of the cursor in that line). A single Peacock application 
can have many modes. Users of applications like Vim will be familiar 
with the concept of moded applications.

### \_\_init\_\_(_name, keyboard, handlers=None, parent=None_)

Modes are created with a name, and a keyboard reference, so that it
can determine what keys are valid. Optionally, pre-defined handlers
can be added to the mode. 

Also optionally, apps can have a parent.
In the Peacock event-loop, if the current app does not have a key
handler for a pressed key, the parent field will be searched 
recursively until a handler or the root is found. This can be used
to allow intimately related modes.

NOTE: Modes do NOT have a reference to a Peacock app. This allows
modes to be easily shared (as well as tested).

Parameter | Type | Purpose
-----------|------|--------
__name__ | _str_  | the name that apps will use to refer to this mode
__keyboard__ | _Keyboard_ | a Keyboard subclass that will be used to determine if key-sequences are valid
__handlers__ | _dict_ | default key handlers to add to this app (_str -> ((Peacock, *args) -> Any)_
__parent__ | _Mode_ | The mode that should be treated as this mode's parent. Whenever there is a miss for a key handler in this app, the parents will be searched

### on(_key_)
Add "on-key" handlers to this mode. Called with a key, (soon to support multi-key sequences), and returns a decorator that consumes a function, and binds the original key sequence to be handled by the given function. The function will be called with:

* Peacock - the currently running app
* str - the text of the line that the cursor is in
* int - the current x position of the cursor in that line 

However, by overriding the [handle](### handle) method, this function signature can be customized.

Parameter | Type | Purpose
-----------|------|--------
__key__ | _str_  | The key to bind behavior to.

### handle(_key, app_)
Executes whatever action is associated with the given key
In the event loop, the handlers dictionary is already checked for
the given key, so when subclassing, you do not need to include a test for membership.

__NOTE__: If you wish to customize the function signature for your key
handlers, this is the method to override.

 Parameter | Type | Purpose
-----------|------|--------
 __key__ | _str_ | The key to trigger.
__app__ | _Peacock_ | The current running app