from nicegui import ui

BOX = 'width: 200px; height: 120px; border: 2px solid #333'


def root():
    with ui.row():  # each `with` opens a node of the tree
        ui.element('div').style(BOX)  # left
        ui.element('div').style(BOX)  # right


ui.run(root, title='2.1 The element tree (NiceGUI)')
