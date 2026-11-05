# The whole road

What happens when the browser opens the NiceGUI column or the mini NiceGUI. The two only differ at the
end: NiceGUI keeps a websocket open, so Python can change the page later (section 3).

```mermaid
sequenceDiagram
  participant B as Browser
  participant S as Server (FastAPI)
  participant P as Your Python
  B->>S: GET /
  S->>P: build the page
  P-->>S: the element tree
  S-->>B: HTML page with the tree as JSON
  B->>B: Vue: render each node with h()
  Note over B,S: NiceGUI only: a websocket stays open for clicks and changes
```

The mini NiceGUI's tree is nested. NiceGUI sends a flat, numbered list instead (step 2.1), so it can
change one element later by its number, without sending the whole tree again.
