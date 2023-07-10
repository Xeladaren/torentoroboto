
import sys

COLOR_BLACK   = "\033[1;30m"
COLOR_RED     = "\033[1;31m"
COLOR_GREEN   = "\033[1;32m"
COLOR_YELLOW  = "\033[1;33m"
COLOR_BLUE    = "\033[1;34m"
COLOR_MAGENTA = "\033[1;35m"
COLOR_CYAN    = "\033[1;36m"
COLOR_WHITE   = "\033[1;37m"

COLOR_BR_BLACK   = "\033[1;90m"
COLOR_BR_RED     = "\033[1;91m"
COLOR_BR_GREEN   = "\033[1;92m"
COLOR_BR_YELLOW  = "\033[1;93m"
COLOR_BR_BLUE    = "\033[1;94m"
COLOR_BR_MAGENTA = "\033[1;95m"
COLOR_BR_CYAN    = "\033[1;96m"
COLOR_BR_WHITE   = "\033[1;97m"

COLOR_RESET      = "\033[0m"
COLOR_NONE       = ""

verbose = False
debug   = True

def Error(msg):
    sys.stderr.write("[{}ERROR{}] {}\n".format(COLOR_RED, COLOR_RESET, msg))
    sys.stderr.flush()

def Warning(msg):
    sys.stderr.write("[{}WARNING{}] {}\n".format(COLOR_YELLOW, COLOR_RESET, msg))
    sys.stderr.flush()

def Debug(msg):
    if debug:
        sys.stdout.write("[{}DEBUG{}] {}\n".format(COLOR_BR_YELLOW, COLOR_RESET, msg))
        sys.stdout.flush()

def Custom(title, msg, title_color=COLOR_NONE, msg_color=COLOR_NONE, start="", always_print=False):

    if always_print or verbose:
        if title_color != COLOR_NONE:
            title_formated = "[{}{}{}]".format(title_color, title, COLOR_RESET)
        else:
            title_formated = "[{}]".format(title)

        if msg_color != COLOR_NONE:
            msg_formated = "{}{}{}".format(msg_color, msg, COLOR_RESET)
        else:
            msg_formated = "{}".format(msg)

        print("{}{} {}".format(start, title_formated, msg_formated))
        sys.stdout.flush()
