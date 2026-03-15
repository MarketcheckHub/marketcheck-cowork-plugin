## Profile Storage

MarketCheck profiles are stored as the `marketcheck-profile.md` **project memory file** (not `~/.claude/marketcheck/`). This ensures persistence across cowork task tabs.

- All skills and commands read the profile from this memory file
- The file has YAML frontmatter (`---` delimiters) followed by raw JSON — parse the JSON after the frontmatter
- Onboarding commands write to this memory file and also update the `## MarketCheck Profile` summary in `MEMORY.md`

## Temporary Files

Lot scan results and other ephemeral data go to `/tmp/marketcheck/`. These are session-local and do not persist across tabs (by design — they're regenerated each run).

## TOON Format (Token-Oriented Object Notation)

When writing structured vehicle data to disk files or returning structured results to callers, use [TOON format](https://github.com/toon-format/toon) instead of JSON. TOON uses ~40% fewer tokens while maintaining LLM accuracy.

### Quick syntax reference

**Objects** — YAML-style indentation (no braces):
```
context:
  task: Lot scan
  dealer_id: 10039721
```

**Uniform arrays** — declare fields once, CSV rows:
```
vehicles[3]{vin,year,make,model,trim,listed_price,miles,dom,body_type}:
  WBA1234...,2022,BMW,X5,xDrive40i,45990,32100,45,SUV
  1HGCV1...,2021,Honda,Accord,Sport,28500,41200,62,Sedan
  5YJ3E1...,2023,Tesla,Model 3,Long Range,38900,12400,15,Sedan
```

**Rules:**
- `key[N]{field1,field2,...}:` declares a uniform array of N items with named fields
- Each subsequent indented line is one row, comma-separated, matching the header field order
- Strings with commas must be quoted
- Null values: empty field (two adjacent commas `,,`)
- File extension: `.toon`
