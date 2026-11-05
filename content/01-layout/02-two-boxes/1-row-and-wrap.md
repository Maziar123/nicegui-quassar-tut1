# A row is flexbox

`display: flex` turns a box into a row: its children line up side by side. Two more lines give it
the gap and the wrapping. Quasar's `row` class and NiceGUI's `ui.row()` are this CSS with a name.

```css title="vue.html" hl=2-4
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
```

Here are three rows in a box only 380 px wide. The first has no gap, the second has a gap, and the
third also wraps, so its last box moves to a new line:

```html preview height=330 title="no gap, gap, gap + wrap"
<style>
  body { margin: 12px; font: 13px system-ui, sans-serif; width: 380px; }
  p { margin: 10px 0 4px; }
  .row { display: flex; outline: 1px dashed #999; }
  .gap { gap: 16px; }
  .wrap { flex-wrap: wrap; }
  .box { width: 120px; height: 50px; border: 2px solid #333; box-sizing: border-box; flex: none; }
</style>
<p>display: flex</p>
<div class="row"><div class="box"></div><div class="box"></div><div class="box"></div></div>
<p>+ gap: 16px (too wide now: the last box sticks out)</p>
<div class="row gap"><div class="box"></div><div class="box"></div><div class="box"></div></div>
<p>+ flex-wrap: wrap</p>
<div class="row gap wrap"><div class="box"></div><div class="box"></div><div class="box"></div></div>
```
