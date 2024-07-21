# import os
# import json
# from termcolor import colored

# title = "精神"
# xx = colored(title,'red',attrs=['bold'])
# print(xx)

from colorama import Fore, Style
 
# 将字符串"fg:skyblue"转换为蓝色文本
def convert_color_string_to_colored_text(text, color_code):
    color_name, text = color_code.split(":")
    color = getattr(Fore, color_name.upper())
    return color + text + Style.RESET_ALL
 
# 示例
color_code = "fg:skyblue"
text = "raw text"
colored_text = convert_color_string_to_colored_text(text, color_code)
print(colored_text)  # 这将打印蓝色的文本
 
# 将"raw text"转换为HTML
def convert_text_to_html(text):
    return "<p>" + text + "</p>"
 
# 示例
html_text = convert_text_to_html("raw text")
print(html_text)  # 这将打印: <p>raw text</p>