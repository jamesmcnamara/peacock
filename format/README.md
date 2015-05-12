# Format
The format `Peacock.format` extends the `str.format` grammar with additional rules for adding color, styles, and backgrounds to strings. 

## Grammar
```
format     ::=  "{" [format specifications]? ["|" foreground] [";" background] "}"
foreground ::= (color | style) ("," (color | style))* 
background ::= color ("," color)* 
color      ::= "green" | "white" | "red" | "magenta" | "black" | "blue" | "yellow" | "cyan" | "negative"
style      ::= "bold" | "underline" | "blink" | "concealed"
```
## English
`Peacock.format` supports a superset of the format specification mini-language, where any format specification can be extend by adding a `|` and comma seperated foreground text specifications, such as color or style options (like bold, underline, etc.), and optionally a `;` followed by background specifications. The list of possible options are as follows:

### _Colors_
* Green
* White
* Red
* Magenta 
* Black
* Blue
* Yellow
* Cyan

### _Styles_
* **Bold**
* <u>Underline</u>
* Blink
* Concealed
 
### _Foreground_
 * Supports all colors
 * Supports all styles

 
### _Background_
 * Supports all colors

## Examples

Print text where the first word is bold red text on a black background, and the second word is blinking:

```python
print(format("{|red, bold; black} {|blink}", "Hello", "World")
```

Print text where the argument is a 3 digit keyword float, displayed in negative. 

```python
print(format("{pi:.3f|negative}", pi=7/22)
```