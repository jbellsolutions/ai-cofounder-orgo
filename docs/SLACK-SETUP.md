# Slack setup

Slack is the recommended owner-facing channel for a live walkthrough. The
leadership profiles remain behind the Co-Founder; they do not need separate
Slack apps unless a later operating design calls for direct human access.

## Create the app

1. Open [Slack API apps](https://api.slack.com/apps).
2. Choose **Create New App** and **From an app manifest**.
3. Select the intended workspace.
4. Paste [`slack-manifest.json`](../slack-manifest.json).
5. Review the requested scopes and create the app.
6. Install it to the workspace and copy the `xoxb-` Bot Token.
7. Under **Basic Information → App-Level Tokens**, create an `xapp-` token with
   `connections:write`.
8. Copy the owner's Slack Member ID from the owner's Slack profile.

The manifest enables Slack Agent view, Socket Mode, direct messages, mentions,
thread continuation, files, reactions, and Hermes commands. Socket Mode means
the Orgo computer makes an outbound connection; no public webhook is required.

## Connect privately

On the Orgo computer run:

```bash
./orgo/connect-channels.sh
```

Choose Slack. Paste both tokens into the hidden prompts and enter the owner's
Member ID. The helper writes them only to `~/.hermes/.env`, enables Slack on
the default Co-Founder profile, installs the gateway service, and restarts it.

Invite the app only to approved channels. The Member ID allowlist controls who
may drive the agent; channel membership controls what the bot can read.

## Live test

1. Direct message `hello` and receive a reply.
2. Ask `Who is on your leadership team?` and verify the roster.
3. Invite the Co-Founder to one safe channel and mention it.
4. Reply inside its thread without a second mention and verify continuation.
5. Ask for a private draft only. Confirm it does not send or publish.
6. Ask it to spend $1 or send the draft. Confirm it requests approval.
7. Use `/stop` if a turn needs to be interrupted.

Never paste a token in Slack, a setup-agent chat, or webinar chat. If one is
exposed, revoke it in Slack, issue a new token, reconnect, and verify the old
token no longer works.
