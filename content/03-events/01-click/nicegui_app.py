from nicegui import ui

BOX = 'width: 200px; height: 120px; border: 2px solid #333; cursor: pointer'


def root():
    ui.add_css('.filled { background: #333; }')
    box = ui.element('div').style(BOX)
    box.on('click', lambda: box.classes(toggle='filled'))


ui.run(root, title='3.1 Click a box (NiceGUI)')
