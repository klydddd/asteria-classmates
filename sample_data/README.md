# Sample Data Policy

This directory only tracks small, redistributable templates:

- `metadata_template.csv` demonstrates the complete metadata contract.
- `provenance_manifest.example.json` documents source, license, and consent
  information expected for an imported dataset.

Do not add downloaded archives, imported metadata, real or private recordings,
speaker-identifying information, model weights, or generated artifacts here.
Keep working data outside the repository and write generated results to
`outputs/`.

The metadata template references an example audio path, but no audio file is
included. Replace every example value and record provenance before using it for
a real dataset.
