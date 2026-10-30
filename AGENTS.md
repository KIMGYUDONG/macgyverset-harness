# Harness kit development

This repository builds a portable instruction kit, not an exam answer. START.md is the consumer entry point. Its exam restrictions apply to consuming the kit during an exam; publishing this repository is separately authorized maintenance.

- Keep all runtime content self-contained and paths relative. Never include personal logs, credentials, private provenance or database connections.
- Preserve the consumer's existing instructions, configuration, permissions and files. The optional preparer writes only new kit skill directories beneath the explicitly selected workspace.
- Use Python standard library for preparation and tests. Run `python3 -m unittest discover -s tests -v` and `python3 scripts/check.py` before publishing.
- Store implementation and validation evidence in docs/plans. Keep actual exam data out of this repository.
- Consumer reporting and task-based model/effort routing are defined in knowledge/reporting-and-routing.md. Keep START.md linked to them. Official upstream skills are fetched from the pinned lock, not rewritten or auto-registered.
