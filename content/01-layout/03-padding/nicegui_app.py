from nicegui import ui

BOX = 'width: 200px; height: 120px; border: 2px solid #333'
DOT = 'width: 40px; height: 40px; background: #333'


def root():
    with ui.row():
        with ui.element('div').classes('q-pa-md').style(BOX):  # left
            ui.element('div').style(DOT)
        with ui.element('div').classes('q-pa-md').style(BOX):  # right
            ui.element('div').style(DOT)


ui.run(root, title='1.3 Space inside a box (NiceGUI)')
