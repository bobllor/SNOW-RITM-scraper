def main_menu():
    print("\n   Service Now RITM scraper")
    print("\n\t a. Label generation (WIP)")
    print("\t b. User creation")
    print("\t c. Quit")

    choice = input("\n   Enter an option: ").lower()

    while choice not in ['a', 'b', 'c']:
        print("   Option not detected.")
        choice = input("   Enter an option: ").lower()
    
    return choice