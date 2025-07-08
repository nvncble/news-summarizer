# Reddit Personal Setup

## Required Environment Variables

```bash
export REDDIT_CLIENT_ID="your_reddit_app_client_id"
export REDDIT_CLIENT_SECRET="your_reddit_app_client_secret"
export REDDIT_REFRESH_TOKEN="your_refresh_token"
Getting Your Refresh Token

Quick Setup

Create Reddit app at https://www.reddit.com/prefs/apps (type: script)
Set redirect URI to: http://localhost:8000
Follow OAuth flow to get refresh token
Test: python digestr_cli_enhanced.py briefing --social

Features

Social Briefing: Personal Reddit feed with casual tone
Combined Briefing: Professional news + personal content
Smart Caching: Respects Reddit API limits