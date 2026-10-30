# MacGyverSet Harness development

Apply this file when modifying this harness repository. When using the harness for an actual task, explicitly read START.md from the task workspace. A clone in a child directory does not automatically apply this file to the parent task.

- Publishing and distribution follow the execution environment policy and explicit authorization. This file grants neither.
- Keep consumer files self-contained, paths relative, and private data out of this repository.
- Preserve the task workspace instructions, configuration, permissions and existing files. START.md performs scoped skill registration through scripts/prepare.py when the user requests installation or application.
- Run Python stdlib tests and scripts/check.py before publishing. Behavioral scenarios are recorded under evals and validation evidence under docs/plans.
- Keep reporting, verification and role guidance in their existing referenced files. Avoid duplicating them here.
