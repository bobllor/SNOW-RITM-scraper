from rich.table import Table, Column
from rich.emoji import Emoji
from rich import box
from .base import console

#table = Table(title="PLACEHOLDER", min_width=70, box=box.ASCII, show_lines=True)

class TableGUI:
    def __init__(self, tasks: dict[str, list[str]]):
        self.tasks = tasks

        self.table = Table(
            Column(header='TASK', width=50, justify='left', no_wrap=False),
            Column(header='STATE', width=5, justify='center'),
            title='PLACEHOLDER',
            box=box.ASCII,
        )

        # emojis.
        self.x = Emoji(name='x')
        self.check = Emoji(name='white_heavy_check_mark')
    
    def create_table(self):
        for task, state in self.tasks.values():
            if state == 'NC':
                self.table.add_row(task, f'{self.x}')
            else:
                self.table.add_row(task, f'{self.check}')
    
    def print_table(self):
        console.print(self.table)