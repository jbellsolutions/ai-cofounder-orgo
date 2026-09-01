# Telegram setup

Telegram is optional and connects only to AI Co-Founder by default.

1. In Telegram, open the verified `@BotFather` account.
2. Use `/newbot`, choose a display name and unique username, and copy the token.
3. Obtain the owner's numeric Telegram user ID from a trusted method.
4. On the Orgo computer run `./orgo/connect-channels.sh` and choose Telegram.
5. Enter the bot token in the hidden prompt and the owner's numeric ID.
6. Send `hello` to the bot and verify the answer.

The helper sets `TELEGRAM_ALLOWED_USERS`; an unknown user is not treated as the
owner. Telegram uses long-polling, so no public webhook or firewall port is
required.

Use a different bot token for any future profile that receives Telegram
directly. Hermes prevents two profiles from polling the same token.
