from .text_formats import text_format

'''
Displays and returns input of the menu for the program.
'''

quit_text = text_format('[q] Quit')

# returns the choice selected by the user.
def get_choice(valid_choices: set) -> str:
    while True:
        choice = input(text_format('Enter an option: ')).lower()

        if choice in valid_choices:
            return choice
        
        print('Selected choice is not found.')

# main menu related functions.
def display_main_menu():
    print(text_format('[a] Automatic mode'))
    print(text_format('[m] Manual mode'))
    print(text_format('[c] Close RITMs'))

def main_menu_choice() -> str:
    valid_choices = ('a', 'm', 'c', 'q')
    
    return get_choice(valid_choices)

# core function related menus
def display_manual_menu():
    print(text_format('[m] Manual input - Manually enter an RITM to create users'))
    print(text_format('[f] File input - Select a CSV/XLSX for create users'))
    print(text_format('[s] Scan VTB - Scan the VTB for a list of elements'))
    print(quit_text)

def manual_choice() -> str:
    valid_choices = ('m', 'f', 'q', 's')
    
    return get_choice(valid_choices)