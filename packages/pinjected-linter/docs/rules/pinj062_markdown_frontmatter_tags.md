# PINJ062: Require Markdown frontmatter with tags

Markdown files (.md) must begin with a YAML frontmatter block and include a non-empty `tags` list, following Obsidian Properties style.

Frontmatter must be delimited by lines containing only `---` at the very top and end of the block. The `tags` property must be a list (sequence) of strings. Both YAML sequence forms are accepted:
- Block sequence
- Flow sequence

Inline comments after values are allowed. A leading `#` inside a tag value is permitted and will be ignored (e.g. `- #network` is treated as `network`). Non-string values (e.g., unquoted numbers or booleans) are not allowed.

## Bad examples

Missing frontmatter:
```
# My note

Some content here.
```

Frontmatter present but missing tags:
```
---
title: My note
---
```

`tags` is not a list:
```
---
tags: "influxdb"
---
```

`tags` empty:
```
---
tags: []
---
```

`tags` contains non-string entries:
```
---
tags: [influxdb, 123, true]
---
```

## Good examples

Block sequence:
```
---
tags:
  - influxdb
  - database
  - network # inline comment allowed
---
```

Flow sequence:
```
---
tags: [influxdb, database, network]
---
```

Block sequence with leading # in values:
```
---
tags:
  - #influxdb
  - #database
  - #network
---
```

## Rationale

Requiring consistent `tags` in frontmatter enables better organization and discovery of notes, aligning with Obsidian Properties conventions across the codebase and documentation.
