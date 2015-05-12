# Peacock API
## _class_ Peacock(Thread)

The Peacock object is the public interface to this framework, and
has a Flask-esque interface. Once created, it takes over writing and 
key handling from the specified TTY, so its `read()` and `write()` methods
should be used in their place.

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


### on(_key_)
Add "on-key" handlers to this app. Called with a key, (soon to support multi-key sequences), and returns a decorator that consumes a function, and binds the original key sequence to be handled by the given function. The function will be called with: 

* str - the text of the line that the cursor is in
* int - the current x position of the cursor in that line 

```python
app = Peacock()
@app.on("ctrl+x")
def delete_to_beginning(cur_line, x):
	# Deletes the text before the cursor 
	app.delete(x)
```

 Parameter | Type | Purpose
-----------|------|--------
 __key__ | _str_  | The key to bind behavior to.

### handle(_key_)
Executes whatever action is associated with the given key. This can be used to trigger execution of a bound behavior, and collect a result if the bound method returns a vlaue.

 Parameter | Type | Purpose
-----------|------|--------
 __key__ | _str_ | The key to trigger.
 
### move\_cursor(_rows=0, cols=0_)
 Moves the cursor the given number of rows, THEN the given number of columns. This does NOT move the cursor to the given coordinate (rows, cols), but instead moves relatively. Any values that are too large or too small are clipped to the max possible given the constraints (i.e. x within 0 to length of line, y within 0 to length of buffer).

 Parameter | Type | Purpose
-----------|------|--------
 __rows__ | _int_ | The number of rows to offset the current cursor position by. This value may be negative to move the cursor upwards.
 __cols__ | _int_ | The number of columns to offset the current cursor position by. This value may be negative to move the cursor backwards.

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
