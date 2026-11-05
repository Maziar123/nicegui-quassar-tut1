from nicegui import ui

BOX = 'width: 200px; height: 120px; border: 2px solid #333'


def root():
    ui.element('div').style(BOX)


ui.run(root, title='1.1 One empty box (NiceGUI)')
