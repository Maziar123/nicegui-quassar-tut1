# How each column reaches the browser

All three files end as the same page, but they take different roads.
NiceGUI is the only one with a server: your Python runs there, and the browser gets the page from it.

```mermaid
flowchart LR
  Q["quasar.html"] --> QV["Vue 3 + Quasar<br>(in the browser)"]
  N["nicegui_app.py"] --> S["NiceGUI server<br>(Python)"]
  S -->|"page + element tree"| QV
  V["vue.html"] --> VV["Vue 3<br>(in the browser)"]
  QV --> DOM["Browser DOM<br>one empty box"]
  VV --> DOM
```
