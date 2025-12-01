# Deployment Guide for Railway

This guide explains how to deploy the RomanBot to Railway using Docker.

## Prerequisites

1. A Railway account (sign up at https://railway.app)
2. GitHub repository with your code (or use Railway CLI)
3. All required API keys and tokens

## Required Environment Variables

The following environment variables must be set in Railway:

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token from @BotFather
- `GROQ_API_KEY` - Your Groq API key
- `YCLIENTS_PARTNER_TOKEN` - Your YClients partner token
- `YCLIENTS_USER_TOKEN` - Your YClients user token

## Deployment Steps

### Option 1: Deploy via Railway Dashboard

1. **Create a New Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo" (or use Railway CLI)

2. **Connect Repository**
   - Connect your GitHub repository containing this code
   - Railway will automatically detect the Dockerfile

3. **Set Environment Variables**
   - Go to your project settings
   - Navigate to "Variables" tab
   - Add all required environment variables:
     - `TELEGRAM_BOT_TOKEN`
     - `GROQ_API_KEY`
     - `YCLIENTS_PARTNER_TOKEN`
     - `YCLIENTS_USER_TOKEN`

4. **Deploy**
   - Railway will automatically build and deploy using the Dockerfile
   - Monitor the logs to ensure the bot starts successfully

### Option 2: Deploy via Railway CLI

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Initialize Project**
   ```bash
   railway init
   ```

4. **Link to Existing Project** (or create new)
   ```bash
   railway link
   ```

5. **Set Environment Variables**
   ```bash
   railway variables set TELEGRAM_BOT_TOKEN=your_token
   railway variables set GROQ_API_KEY=your_key
   railway variables set YCLIENTS_PARTNER_TOKEN=your_token
   railway variables set YCLIENTS_USER_TOKEN=your_token
   ```

6. **Deploy**
   ```bash
   railway up
   ```

## Local Development with Docker Compose

For local testing before deploying to Railway:

1. **Create .env file** (copy from .env.example and fill in your values)
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

2. **Build and run**
   ```bash
   docker-compose up --build
   ```

3. **Run in detached mode**
   ```bash
   docker-compose up -d
   ```

4. **View logs**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the container**
   ```bash
   docker-compose down
   ```

## Docker Commands (Without Docker Compose)

1. **Build the image**
   ```bash
   docker build -t romanbot .
   ```

2. **Run the container**
   ```bash
   docker run --env-file .env --name romanbot romanbot
   ```

## Verifying Deployment

After deployment:

1. Check Railway logs for any errors
2. The bot should start polling for Telegram messages
3. Test the bot by sending `/start` command to your Telegram bot

## Troubleshooting

### Bot not responding
- Check that all environment variables are set correctly
- Verify the Telegram bot token is valid
- Check Railway logs for error messages

### Import errors
- Ensure all dependencies are in `requirements.txt`
- Check if `yclients_client` module is properly installed or needs to be added

### Connection issues
- Verify API keys are correct
- Check network connectivity from Railway's servers

## Railway Configuration

The project includes `railway.json` and `railway.toml` configuration files. Railway will:
- Use the Dockerfile for building
- Restart the container on failure (up to 10 retries)
- Run a single replica of the bot

## Notes

- Railway automatically provides environment variables to containers
- No port exposure needed for Telegram bot (uses polling)
- The bot will restart automatically if it crashes
- Railway provides free tier with usage limits


