from nicegui import ui

RECT = 'width: 200px; height: 120px; border: 2px solid #333'


def root():
    with ui.row().style('gap: 16px'):   # flex row, side by side
        ui.element('div').style(RECT)   # left
        ui.element('div').style(RECT)   # right


ui.run(root, title='Step 3 – NiceGUI (Python)')
