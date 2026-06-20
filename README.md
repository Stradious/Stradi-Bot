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

## Host it 24/7

GitHub stores the code but does not keep a Discord bot running. Deploy this repository as a long-running worker/service on a cloud host that supports Docker:

1. Connect the public GitHub repository to the host.
2. Let the host build the included `Dockerfile`.
3. Add a secret environment variable named `DISCORD_TOKEN` with the real token.
4. Deploy one instance. Do not run the local copy at the same time.

The bot does not need a public web URL or port. It connects outward to Discord.

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
