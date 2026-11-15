# Fixed template maintenance repair

`routine-spec-v01-officecli.docx` is a schema-valid maintenance copy of the
immutable legacy `routine-spec-kit` template. It is intended for later adoption
as the fixed OfficeCLI template. It does not redesign the document.

## Reproduction

From this directory, using the installed Python 3 launcher:

```powershell
py -3 .\repair_template.py --apply
```

Without `--apply`, the helper only regenerates the plan and command JSON. The
default OfficeCLI is the IBM Bob bundled `officecli.exe`, version 1.0.144.
`--source` and `--officecli` can override their locations. The output directory
is fixed to the helper's own directory; the source is never overwritten.

Python uses standard-library ZIP reading, XML reading/planning, copying, and
verification. All DOCX internal writes are performed by the recorded OfficeCLI
`batch` / `raw-set` instructions. OfficeCLI temporary and spill destinations
are redirected into `tmp/` here. The helper supports batch `data.outputFile`
spills and records the complete decoded results in `repair-batch.full.json`.
This run did not spill its compact inner batch result.

## Repair evidence

The original validator reported 164 schema errors. The 120 OfficeCLI commands
performed these minimal changes:

| Repair | Elements |
| --- | ---: |
| Put paragraph properties in schema order, including `snapToGrid` and `pageBreakBefore` | 103 |
| Put table properties in schema order | 12 |
| Put table cell margins in schema order | 12 |
| Supply missing `w:shd/@w:val="clear"`, retaining color/fill attributes | 33 |
| Remove a trailing empty duplicate `w:rFonts` from Normal, Heading1, Heading2, and Title; retain populated font properties | 4 |

The margin repairs are included in the table-property replacement commands.
One bulk attribute command supplies all 33 shading patterns. Thus 164 repaired
schema defects are addressed by 120 commands.

`validate-after.stdout.json` records validation success with no errors.
`repair-batch.full.json` records 120 executed, 120 succeeded, 0 failed, 0 skipped.
`repair-changes.json` records each repair's XPath and before/after property
order. `officecli-invocations.json` records exact arguments and exit codes.

## Preserved content and OfficeCLI save normalization

`repair-evidence.json` confirms that the source SHA-256 is unchanged and that
all body/header/footer paragraph text, template tokens, table row/cell counts,
table captions, and PAGE/NUMPAGES simple fields match the source. It compares
every original XML and binary package member against the exact repair plan.

The comparison explicitly accounts for these observed OfficeCLI/OpenXML SDK
save effects:

- Paragraph identity metadata (`w14:paraId`, `w14:textId`) is assigned to the
  source's paragraphs, which originally had no IDs.
- An audit-only `docProps/custom.xml` is added, containing exactly
  `OfficeCLI.Version=1.0.144` and `OfficeCLI.LastModified`, with its required
  package relationship and content-type declaration.
- Eight style indentation elements serialize `left/right` as `start/end` with
  identical values. The helper rejects templates with active RTL before using
  this equivalence.
- The 12 table-look elements retain `w:val="04A0"`; redundant explicit flags
  are removed by the SDK. The comparator only accepts flags that exactly match
  the retained bitmask.
- XML indentation whitespace and namespace-prefix spelling may change during
  serialization. Leaf text content is preserved and compared exactly.

No unexpected semantic package differences were found. Rendering was not
performed in this maintenance task; the root task will inspect appearance
before adopting the template.

## Primary implementation references

- [OfficeCLI v1.0.144 raw-set command](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/CommandBuilder.Raw.cs)
- [OfficeCLI raw XML actions and namespace handling](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/Core/RawXmlHelper.cs)
- [OfficeCLI batch atomicity and envelope handling](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/CommandBuilder.Batch.cs)
- [OfficeCLI existing-document audit metadata](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/Core/OfficeCliMetadata.cs)
