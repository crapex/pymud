import re

def remove_ansi_color(text):
    if isinstance(text, str) and '\x1b' in text:
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub('', text)
    else:
        return text
