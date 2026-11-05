# Why the border goes inside

A browser counts the border **outside** the width by default. Then a 200 px box with a 2 px border
is 204 px wide. `box-sizing: border-box` puts the border inside, so the box stays 200 px.

```css title="vue.html" hl=5
.box {
  width: 200px;
  height: 120px;
  border: 2px solid #333;
  box-sizing: border-box;
}
```

Quasar turns this on for every element, so NiceGUI has it too. In plain Vue you write it yourself.
Here is the difference with a thick 8 px border, so you can see it:

```html preview height=200 title="content-box and border-box"
<style>
  body { margin: 16px; font: 15px system-ui, sans-serif; }
  .box { width: 200px; height: 56px; border: 8px solid #333; margin-bottom: 14px; padding: 6px; }
  .inside { box-sizing: border-box; }
</style>
<div class="box">content-box: 228 px</div>
<div class="box inside">border-box: 200 px</div>
```
