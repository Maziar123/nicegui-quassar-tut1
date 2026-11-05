from nicegui import ui

BOX = 'width: 200px; height: 120px; border: 2px solid #333'


def root():
    with ui.row():
        ui.element('div').style(BOX)  # left
        ui.element('div').style(BOX)  # right


ui.run(root, title='2.2 Mini NiceGUI (NiceGUI)')
