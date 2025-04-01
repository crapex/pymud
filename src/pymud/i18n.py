# internationalization (i18n)
import os, importlib

def i18n_ListAvailableLanguages():
    """
    List all available languages.

    This function checks all files in the `lang` directory for files starting with `i18n.` and ending with `.py`.
    These files represent internationalization configurations for different languages. The default language is Simplified Chinese ("chs").

    Returns:
        list: A list containing all available language codes.
    """
    # Define the default language list, here the default language is Simplified Chinese
    languages = []  
    # Define the directory where the language files are located
    lang_dir = os.path.join(os.path.dirname(__file__), "lang")

    # Check if the language directory exists. If it doesn't, return the default language list directly
    if os.path.exists(lang_dir):
        # Iterate through all files in the language directory
        for filename in os.listdir(lang_dir):
            # Check if the file starts with "i18n.", ends with ".py", and is not the default Simplified Chinese file
            if filename.startswith("i18n_") and filename.endswith(".py"):
                # Extract the language code from the filename, removing "i18n." and ".py"
                language = filename[5:-3]  
                # Add the extracted language code to the list of available languages
                languages.append(language)

    if not languages:
        languages.append("chs")

    return languages

def i18n_LoadLanguage(lang: str):
    lang_file = os.path.join(os.path.dirname(__file__), "lang", f"i18n_{lang}.py")
    if os.path.exists(lang_file):
        modLang = importlib.import_module(f"pymud.lang.i18n_{lang}")
        TRANS = modLang.__dict__["TRANSLATION"]
        if isinstance(TRANS, dict):
            from .settings import Settings
            Settings.text.update(TRANS["text"])