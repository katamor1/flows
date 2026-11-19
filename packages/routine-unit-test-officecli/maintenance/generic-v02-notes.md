# Generic 0.2.0 maintenance notes

The active release uses unit-test-spec-v02, schema0.2.0, and project-specific input locks. Legacy assets and ZIP remain available unchanged. New example specifications were authored from the program contracts; existing Alarm cases were migrated into separate v02 data.

The v02 template is copied once from the retained v01 template and edited by approved OfficeCLI text commands. All Python XML use in that maintenance script is read-only audit. Runtime row cloning, replacement, metadata and structural checks are all OfficeCLI operations.

Canonical empty lists are never padded. Only the renderer view has visible empty rows. Generic JSON values are rendered with JSON serialization and never evaluated. Required source references are discovered from the program declarations, and unverified/caller/out-of-scope rows retain explicit reasons.

Final verification and limitations are recorded in artifacts/routine-generic-validation/unit-tests/HANDOFF.md and acceptance-summary.json. The parent owns Bob integration and the combined distribution.
