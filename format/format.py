from itertools import chain, zip_longest, repeat
from re import search, compile

def _format_factory():
    """
        Because the format function requires so many constants, this function 
        defines them all, and returns the format function as a closure
    """
    ############################ UTILITY REGEXS ###############################
    # matches a format specification
    FMT_RE = compile("\{.*?\}")

    # within a format specificaiton, matches the peacock specifications
    PEACOCK_ATTRS_RE = compile("(?<=\|).*(?=\})")

    # matches peacock specifications wholly, so they can be easily removed
    REMOVE_PEACOCK_RE = compile("\|.*(?=\})")

    # character codes for foreground attributes
    FG_MAP = {
                "bold": "1;",
                "underline": "4;",
                "blink": "5;",
                "negative": "7;",
                "concealed": "8;",
                "black": "30;",
                "red": "31;",
                "green": "32;",
                "yellow": "33;",
                "blue": "34;",
                "magenta": "35;",
                "cyan": "36;",
                "white": "37;"
            }

    # character codes for background attributes
    BG_MAP = {
                "negative": "7;",
                "black": "40;",
                "red": "41;",
                "green": "42;",
                "yellow": "43;",
                "blue": "44;",
                "magenta": "45;",
                "cyan": "46;",
                "white": "47;"
            }
    
    # Escape sequence code 
    ESCAPE_SEQ = "\033["

    # turn off color styling code
    STYLE_OFF = "{}0;m".format(ESCAPE_SEQ)
    

    ################################ IMPLEMENTATION ###########################
    def preprocess_fmt_spec(fmt_spec):
        """
            Consumes a format specification and returns the string that should
            be added to the format string to achieve the formatting specified
            ex: '{wage:0.3f|blue,bold;cyan} will return "\033[34;1;m{wage:0.3f}\033[0;m"
            :param fmt_spec: str - format specification 
                e.g.{wage:0.3f|blue,bold;cyan}
            :return: str 
        """
        # if the given format specification does not contain a peacock grammar,
        # return the unmodified fmt_string
        if "|" not in fmt_spec:
            return fmt_spec

        # find the specifications following a '|' (e.g. in {wage:.2f|blue;orange}
        # peacock_attrs would hold 'blue;orange'
        peacock_attrs = PEACOCK_ATTRS_RE.search(fmt_spec).group()

        if ";" in peacock_attrs:
            fg_attrs, bg_attrs = peacock_attrs.split(";")

            # zips each attribute with the dictionary it should be looked up in
            attr_map = chain(zip(fg_attrs.lower().split(","), repeat(FG_MAP)), 
                             zip(bg_attrs.lower().split(","), repeat(BG_MAP)))
        else:
            attr_map = zip(peacock_attrs.lower().split(","), repeat(FG_MAP))
        
        
        # attrs holds the attribute strings which will be added to the string
        # at the end of preprocessing
        attrs = [map[attr.strip()] for attr, map in attr_map] 
        
        # trim fmt_spec to be acceptable to str.format()
        raw_fmt_spec = REMOVE_PEACOCK_RE.sub("", fmt_spec)

        # format string starts with escape sequence, concatenates all 
        # user-specified strings ends with an 'm' to designate graphics
        attr_string = ESCAPE_SEQ + "".join(attrs) + "m"
        return "".join((attr_string, raw_fmt_spec, STYLE_OFF))

    def format(fmt, *args):
        """
            Extends the functionality of str.format by adding additional rules
            to the grammar. Users can chain text attributes after a "|", and 
            background attributes after a ";"
            :param fmt: str - format string
            :param args: iter - values to insert into format string 
        """

        # Split the string into text segments and format specifications
        non_formats = iter(FMT_RE.split(fmt))
        format_chunks = FMT_RE.findall(fmt)
 
        fmt_string = (text + preprocess_fmt_spec(fmt_spec)
                      for text, fmt_spec in 
                      zip_longest(non_formats, format_chunks, fillvalue=""))

        # After converting the peacock format string into a standard format
        # string, pass the call to str.format
        return "".join(chain(fmt_string, non_formats)).format(*args)

    return format    

