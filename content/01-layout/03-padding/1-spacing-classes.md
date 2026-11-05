# Quasar's spacing classes

A spacing class has three parts: **what** (`p` padding, `m` margin), **where** (`a` all sides, `x` left
and right, `y` top and bottom, `t` `r` `b` `l` one side), and **how much**. So `q-pa-md` is padding on
all sides, medium; `q-mt-lg` is margin on the top, large. The sizes in Quasar 2.35:

| Size | `none` | `xs` | `sm` | `md` | `lg` | `xl` |
|---|---|---|---|---|---|---|
| Space | 0 | 4 px | 8 px | 16 px | 24 px | 48 px |

They work in NiceGUI too, several at once: `ui.element('div').classes('q-pa-md q-mt-lg')`.

Padding is the space **inside** a box, between its border and its content. Here are the same box and
square with padding from `xs` to `xl`:

```html preview height=150 title="padding: 4, 8, 16, 24 and 48 px"
<style>
  body { margin: 12px; display: flex; gap: 12px; font: 12px system-ui, sans-serif; }
  .box { width: 100px; height: 100px; border: 2px solid #333; box-sizing: border-box; }
  .dot { width: 20px; height: 20px; background: #333; }
  p { margin: 4px 0 0; text-align: center; }
</style>
<div><div class="box" style="padding: 4px"><div class="dot"></div></div><p>xs</p></div>
<div><div class="box" style="padding: 8px"><div class="dot"></div></div><p>sm</p></div>
<div><div class="box" style="padding: 16px"><div class="dot"></div></div><p>md</p></div>
<div><div class="box" style="padding: 24px"><div class="dot"></div></div><p>lg</p></div>
<div><div class="box" style="padding: 48px"><div class="dot"></div></div><p>xl</p></div>
```
