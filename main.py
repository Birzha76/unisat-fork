import sys
import asyncio

from utils.runner import run_modules

from termcolor import cprint
from questionary import Choice, select


def main():
    try:
        while True:
            answer = select(
                'What do you want to do?',
                choices=[
                    Choice("Mint Runes", 'mint_runes'),
                    Choice("Mint Inscribes Ordinals", 'mint_inscribes'),
                    Choice("Show Account INFO", 'show_account_info'),
                    Choice('❌ Exit', "exit")
                ],
                qmark='🛠️',
                pointer='👉'
            ).ask()

            if 'mint' in answer:
                print()
                asyncio.run(run_modules(answer))
                print()
            elif answer == 'show_account_info':
                print()
                asyncio.run(run_modules(answer))
                print()
            elif answer == 'exit':
                sys.exit()
            elif answer is not None:
                print()
                answer()
                print()
            else:
                raise KeyboardInterrupt
    except KeyboardInterrupt:
        cprint(f'\nQuick software shutdown by <ctrl + C>', color='light_yellow')
        sys.exit()


if __name__ == "__main__":
    main()
