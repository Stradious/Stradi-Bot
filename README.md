# Stradious

A configurable Discord community app for Stradi's Shack. It includes welcome messages, self-service roles, persistent counting, polls, coin flips, and giveaways.

## Keep the token private

The real Discord bot token belongs only in `.env` on your computer or in your hosting provider's secret/environment-variable settings. Never paste it into GitHub, Discord chat, screenshots, or source code.

If a token is ever exposed, reset it immediately in the Discord Developer Portal.

## Run locally

1. Install Python 3.14 or newer.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and add the real token:

   ```env
   DISCORD_TOKEN=your_real_token_here
   ```

5. Start the bot:

   ```powershell
   python main.py
   ```

The Discord application must have the **Message Content Intent** and **Server Members Intent** enabled in the Discord Developer Portal. Change the optional channel and role settings from `.env.example` when installing Stradious in a different server.

## Host it 24/7 with Railway

GitHub stores the code but does not keep a Discord bot running. Railway can run the included Docker container as a long-running service:

1. Open the [Railway dashboard](https://railway.com/dashboard) and create a project from a GitHub repository.
2. Select `Stradious/Stradi-Bot`.
3. Open the service's **Variables** section and add `DISCORD_TOKEN` with the real token.
4. Deploy the service and check its logs for `Ready as`.
5. Stop the local copy after the cloud copy is online. Only one instance should use the token.

`railway.json` tells Railway to build the `Dockerfile`, keep one instance running, and restart the bot automatically. The bot does not need a public web URL or port because it connects outward to Discord.

Railway requires a paid plan after its trial. Review [current Railway pricing](https://railway.com/pricing) before upgrading.

## Current commands

Every command works both as a traditional `!command` and as a Discord slash
command. Type `/` in Discord to open the native searchable command picker.

- `!hello`
- `!help`
- `!assign` and `!remove`
- `!count`
- `!poll <question>`
- `!secret`
- `!coinflip`
- `!gstart <time> <winners> <prize>`

Giveaways can be started from any server channel and are posted in the
configured `GIVEAWAY_CHANNEL_ID`. The notification role is resolved first by
`GIVEAWAY_ROLE_ID`, then by `GIVEAWAY_ROLE_NAME`, so a stale role ID does not
produce an unknown-role mention. `BOT_NICKNAME` controls the bot's display name
within each server where it has permission to change its nickname.

Counting state is saved to `data/counting.json`, so local restarts no longer erase progress. On Railway, attach persistent storage at `/app/data` if progress must also survive a fresh deployment.
