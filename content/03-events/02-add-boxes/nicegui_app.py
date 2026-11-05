from nicegui import ui

BOX = 'width: 200px; height: 120px; border: 2px solid #333; cursor: pointer'


def root():
    row = ui.row()

    def add():
        with row:
            ui.element('div').style(BOX).on('click', add)

    add()  # the first box


ui.run(root, title='3.2 Add a box on each click (NiceGUI)')
