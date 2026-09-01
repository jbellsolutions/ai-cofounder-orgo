# Start here: AI Co-Founder on an Orgo computer

This walkthrough is written for someone creating a cloud computer for the
first time. You do not need to know server commands. A setup agent should do
the technical work while the account owner handles only private sign-ins,
billing approvals, and permission choices.

## The one message to use

Paste this into Codex, Claude Code, or another capable setup agent:

```text
Install AI Co-Founder from this repository:
https://github.com/jbellsolutions/ai-cofounder-orgo

Read AGENTS.md, START-HERE.md, and docs/ORGO-SETUP.md before changing anything.
Use my Orgo account and the maintained Hermes template. Handle every technical
step yourself. Walk me through private approvals one screen at a time. Never
display, repeat, log, or commit a key. Connect the model first, create the team,
connect the managed stack, connect Slack, and then add Telegram, Calendar,
inbox, CRM, and PandaDoc if I authorize them. Finish only when a real message gets a reply and
./orgo/verify.sh passes without exposing a secret.
```

## Before the call

The setup agent quietly confirms:

- the intended Orgo workspace and computer do not already exist;
- the owner is ready to select a model provider;
- the intended Slack workspace is available;
- optional Telegram and business-app accounts are available if wanted;
- no unrelated Orgo computer will be changed.

Private values go only into hidden prompts on the Orgo computer. They never go
in GitHub, a webinar chat, a screenshot, a shared note, or an AI response.

## Step 1 — Create the computer

In Orgo, open the intended customer workspace and create a computer from the
maintained template `system/hermes-agent@1.0.0`:

- Name: `ai-guy-cofounder`
- Memory: 8 GB
- CPU: 2 vCPU
- Disk: 40 GB
- Display: 1440 × 900

Wait until the status says **running**, then open the visible desktop and its
Terminal. There is no public website or Slack webhook to configure.

## Step 2 — Install the Co-Founder core

The setup agent runs:

```bash
git clone https://github.com/jbellsolutions/ai-cofounder-orgo.git
cd ai-cofounder-orgo
./orgo/setup.sh
```

This installs the reviewed Hermes v0.21.0 release and the AI Co-Founder
identity, company constitution, policies, skills, controlled Agent Factory,
Bot Mode configuration, Kanban foundation, and private A2A gateway. It does
not create a paid Orgo computer, connect an account, send a message, or publish
anything by itself.

## Step 3 — Connect the model privately

The setup agent runs:

```bash
hermes setup
```

The owner signs in or enters the provider credential in the private prompt.
The setup agent confirms a harmless local answer. It never asks the owner to
paste a key into chat.

## Step 4 — Create the leadership team

After the model works, the setup agent runs:

```bash
./orgo/create-team.sh
```

This creates five isolated Hermes profiles:

1. Head of Operations
2. Revenue Partner
3. Affiliate Revenue Partner
4. Finance & Risk Lead
5. Research & Analysis Lead

They inherit the working model connection at creation time, then receive their
own identity, skills, role-specific tools, memory, sessions, and configuration.
The installer enables one multiplexed gateway, separate A2A routes, and one
durable Kanban board. It never copies future Slack, Telegram, or business-app
tokens into the worker profiles.

When the team first answers, tell the Co-Founder:

```text
Walk me through the company onboarding one question at a time. Start with what
we are building, who we help, the offer, the current numbers, and the next
90-day outcome. Show me each summary before you save it as company truth.
```

It fills the private company operating files only after the owner confirms each
summary. The public GitHub copy remains generic.

## Step 5 — Connect memory, company identity, and visibility

The setup agent runs `./orgo/connect-agent-stack.sh` and handles the technical
work. The owner completes only private account verification. Honcho gives each
profile a separate memory identity, Agent Bundle gives the Co-Founder one
company inbox/phone/TEST-mode card, and Latitude monitors all profiles. Start
Latitude in metadata-only mode unless conversation-level evaluation is both
wanted and permitted. See [the managed stack guide](docs/MANAGED-AGENT-STACK.md).

## Step 6 — Connect Slack

Create the Slack app from [`slack-manifest.json`](slack-manifest.json), install
it into the intended workspace, and then run:

```bash
./orgo/connect-channels.sh
```

Choose Slack. The helper privately stores the `xoxb-` bot token, `xapp-` Socket
Mode token, and the owner's Slack Member ID.

Prove three things:

1. Send `hello` in a direct message and receive a reply.
2. Ask `Who is on your leadership team?` and receive the five-profile roster.
3. Ask it to create a private research task. Confirm the task appears in
   Kanban and the Research & Analysis profile returns a result.

## Step 7 — Add Telegram if wanted

Run `./orgo/connect-channels.sh` again, choose Telegram, create the bot with
`@BotFather`, enter the token in the hidden prompt, and send `hello`.
Telegram uses outbound long-polling and requires no public inbound port.

## Step 8 — Connect business tools

Run:

```bash
./orgo/connect-tools.sh
```

Connect only the accounts the owner chooses. Begin with read-only or private
draft tests:

```text
Read my next three calendar events. Do not create, change, or cancel anything.
List three recent inbox subject lines. Do not send, move, or change anything.
Create a private draft proposal titled "Connection Test". Do not send it.
```

## Step 9 — Connect another computer with A2A

For the compact webinar version, every local profile already has an A2A route.
To connect a separate Funding Revenue Partner or another computer, join both
machines to the same Tailscale network and run:

```bash
./orgo/connect-a2a.sh
```

The helper uses separate inbound and outbound tokens, an authenticated peer
identity, a trusted-peer allowlist, and a three-turn anti-loop limit. It never
opens an unauthenticated public A2A port.

## Step 10 — Finish with proof

Run:

```bash
./orgo/verify.sh
```

Setup is complete only when:

- Hermes is at the pinned reviewed commit;
- all six profiles have the correct identity and role skills;
- the Co-Founder has the Kanban and Agent Factory tools;
- the multiplex allowlist and all five A2A routes are present;
- the gateway, model, and selected messaging channel are healthy;
- a real owner message receives a reply;
- a research task completes through the worker profile;
- consequential external actions still stop for approval;
- no private value appears in Git or the setup report.

If an optional account is not ready, leave the computer running and return to
the relevant connection helper later. Do not delete `~/.hermes`; that is where
the team keeps its profiles, memories, sessions, policies, and work board.
