# Orgo reference used by this repository

Last verified: August 31, 2026.

The source of truth is Orgo's machine-readable documentation:
[https://docs.orgo.ai/llms.txt](https://docs.orgo.ai/llms.txt).

## Applied facts

- An Orgo computer is persistent and belongs to a workspace.
- A computer is created from a template and has explicit CPU, memory, disk, and
  display settings.
- `system/hermes-agent@1.0.0` is the maintained Hermes template used here.
- Workspace-scoped API keys are preferred over broader account keys.
- Creating, resizing, stopping, or deleting a computer changes external state;
  deletion and billing-affecting changes are never inferred from a repository.
- Custom golden-template publication is separate from installing this public
  overlay onto a maintained template.

## Setup-agent API discipline

When using the Orgo API, the setup agent should:

1. list workspaces and select the exact intended workspace;
2. list computers in that workspace and match the exact name;
3. reuse a valid existing computer instead of duplicating it;
4. use `POST /computers` only after resolving the target and authorization;
5. wait for `running` before operating the terminal;
6. keep API keys out of commands, output, screenshots, Git, and notes;
7. never update, resize, stop, or delete an unrelated computer;
8. verify the resulting computer ID, name, workspace, template, and state.

The public repository deliberately does not contain account-specific API
requests or credentials. The live setup agent should fetch the current Orgo
schema from `llms.txt` before an account mutation because endpoints and plan
capabilities can change after this release.
