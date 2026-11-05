# A click's round trip

In Quasar and Vue, a click never leaves the browser. In NiceGUI it makes a round trip to your Python
and back. It is quick enough that you do not notice, and it means your click handler can use anything
Python can: files, a database, other libraries.

```mermaid
sequenceDiagram
  participant U as You
  participant B as Browser
  participant P as Python (NiceGUI server)
  U->>B: click the box
  Note over B: Quasar / Vue: the handler runs here, done
  B->>P: NiceGUI: "click" event over the websocket
  P->>P: box.classes(toggle='filled')
  P-->>B: the box's new classes
  B->>U: the box is dark
```

The handler is a normal Python function. A `lambda` is short for one line; a longer one looks like this:

```python title="nicegui_app.py, written with def"
def toggle():
    box.classes(toggle='filled')


box.on('click', toggle)
```
