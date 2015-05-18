
class Mode:
    """
        Modes are what key-handlers are attached to in a Peacock application.
        A mode is simply an object which can have key-handlers attached to it,
        and has the ability to dispatch a call to one of those handlers, with 
        whatever arguments the developer chooses (the default is a reference 
        to the calling Peacock applications, the current cursor line, and the 
        x-position of the cursor in that line). A single Peacock application 
        can have many modes. Users of applications like Vim will be familiar 
        with the concept of moded applications.
    """
    def __init__(self, name, keyboard, handlers=None, parent=None):
        """
            Modes are created with a name, and a keyboard reference, so that it
            can determine what keys are valid. Optionally, pre-defined handlers
            can be added to the mode. Also optionally, apps can have a parent.
            In the Peacock event-loop, if the current app does not have a key
            handler for a pressed key, the parent field will be searched 
            recursively until a handler or the root is found. This can be used
            to allow intimately related modes.
            NOTE: Modes do NOT have a reference to a Peacock app. This allows
            modes to be easily shared (as well as tested)
            :param name: str - the name that the app will use to refer to this
                mode
            :param keyboard: Keyboard - a Keyboard subclass that will be used 
                to determine if key-sequences are valid
            :param handlers: dict: str -> ((Peacock, *args) -> Any) - default
                key handlers to add to this app
            :param parent: Mode - the mode that should be treated as this
                mode's parent. Whenever there is a miss for a key handler in 
                this app, the parents will be searched
        """
        self.name = name
        self.valid_keys = keyboard.keys.values()
        
        # handlers: str -> ((str, int) -> None)
        self.handlers = handlers or {}
        self.parent = parent

    def on(self, key):
        """
            Add "on-key" handlers to this mode. Called with a key, (soon to
            support multi-key sequences), and returns a decorator that 
            consumes a function, and binds the original key sequence to be
            handled by the given function. The function will be called with: 
                * str - the text of the line that the cursor is in
                * int - the current x position of the cursor in that line 
            E.g.:
            >>> app = Peacock()
            >>> normal = Mode("normal", keyboard=app.keyboard)
            >>> app.add_mode(normal)
            >>> @normal.on("I")
            ... def insert_mode(app, *args):
            ...     # Switches back to insert mode    
            ...     app.set_mode("insert")
        """
        # Validate that it is in fact a valid key sequence
        if key not in self.valid_keys:
            raise ValueError("{} not a valid key".format(key))

        def inst_decorator(f):
            """
                Decorator closure that binds the key-sequence specified in
                the outer scope to the given function, in the given mode
                :param f: (str, int) -> None - void function which consumes the 
                    current line text and cursor x-position 
                :return: f - unaltered
            """
            self.handlers[key] = f 
            return f
        return inst_decorator
 
    def handle(self, key, app):
        """
            Executes whatever action is associated with the given key
            In the event loop, the handlers dictionary is already checked for
            the given key, so we can assume that when this method is called
            there is a binding.
            NOTE: if you wish to customize the function signature for your key
            handlers, this is the method to override

            :param key: str - a key code or sequence (non-None)
            :param app: Peacock - the currently running app
        """
        # TODO: add multi-key sequences
        # Handlers is a dict of mapping:
        #   str -> ((Peacock, str, int) -> None)
        # Call the function with the current app, the current line's text, 
        # and the x position in that line
        return self.handlers[key](app, app._buffer[app._y], app._x)
       
class ModeError(Exception):
    pass

