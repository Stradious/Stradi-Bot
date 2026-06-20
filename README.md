# Stradi Bot

A Discord community bot for Stradi's Shack. It includes welcome messages and role assignment, counting, polls, coin flips, and giveaways.

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

The Discord application must have the **Message Content Intent** and **Server Members Intent** enabled in the Discord Developer Portal.

## Host it 24/7 with Railway

GitHub stores the code but does not keep a Discord bot running. Railway can run the included Docker container as a long-running service:

1. Open the [Railway dashboard](https://railway.com/dashboard) and create a project from a GitHub repository.
2. Select `Stradious/Stradi-Bot`.
3. Open the service's **Variables** section and add `DISCORD_TOKEN` with the real token.
4. Deploy the service and check its logs for `We are ready to go in`.
5. Stop the local copy after the cloud copy is online. Only one instance should use the token.

`railway.json` tells Railway to build the `Dockerfile`, keep one instance running, and restart the bot automatically. The bot does not need a public web URL or port because it connects outward to Discord.

Railway requires a paid plan after its trial. Review [current Railway pricing](https://railway.com/pricing) before upgrading.

## Current commands

- `!hello`
- `!assign` and `!remove`
- `!dm <message>`
- `!reply`
- `!poll <question>`
- `!secret`
- `!coinflip`
- `!gstart <time> <winners> <prize>`

Counting state is stored in memory, so it resets whenever the bot restarts or is redeployed.
