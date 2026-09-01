# Orgo setup

This is the precise technical contract behind the plain-language
[Start Here](../START-HERE.md) walkthrough.

## Computer contract

The canonical values live in [`orgo/deployment.json`](../orgo/deployment.json):

- workspace: AI Guy unless the owner chooses a customer workspace;
- computer: `ai-guy-cofounder`;
- template: `system/hermes-agent@1.0.0`;
- 8 GB RAM, 2 vCPU, 40 GB disk, 1440 × 900 display;
- compact six-profile mode;
- Hermes v0.21.0 at the pinned commit;
- A2A on private port 9900;
- API server peer transport on private port 8377 when selected.

Orgo Startup can launch the maintained Hermes template. A private custom
golden-template build is unnecessary for this repository and may require a
different plan. The reproducible overlay keeps the public GitHub template
usable without an Orgo account change.

## Deployment order

1. Read account/workspace/computer state before mutating anything.
2. Reuse a valid partial `ai-guy-cofounder`; do not create duplicates.
3. Create only the intended computer from the maintained template.
4. Clone the repository and run `./orgo/setup.sh`.
5. Run `hermes setup` and prove the model locally.
6. Run `./orgo/create-team.sh` before channel or business-app credentials exist.
7. Connect owner channels, tools, and optional A2A peers.
8. Run `./orgo/verify.sh` and the live acceptance tests.

## Why the order matters

Named profiles clone the working default model connection when created. The
installer then removes anything that is not a recognized model-provider key.
Creating the team before Slack, Telegram, Composio, PandaDoc, or A2A connection
prevents accidental credential sharing and makes the webinar path easier to
explain.

## No deployment from GitHub alone

The repository contains no Orgo API key and performs no account mutation when
opened or cloned. A setup agent must inspect the authorized account, resolve the
workspace, create or select the exact computer, and operate its terminal. This
prevents a public repository from becoming an accidental billing action.

## Production split

Use the compact computer for the first generic build. Split onto a Co-Founder
Core and Team Hub when separate secret trust, filesystem boundaries, load, or
customer isolation justify it. Connect the existing Funding Revenue Partner as
an authenticated peer rather than reinstalling it.

For the applied platform facts and API boundaries, see
[Orgo reference](ORGO-REFERENCE.md).
