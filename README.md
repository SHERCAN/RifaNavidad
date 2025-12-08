# Telegram Secret Santa Bot 🎄

A Python-based Telegram bot designed to organize a Secret Santa (Amigo Secreto) type raffle automatically. It ensures participants are paired mutually (A gifting B, B gifting A) and provides an interactive button-based interface for easy registration.

## Features

- **Interactive UI**: Uses Telegram Inline Keyboard buttons for a user-friendly registration process.
- **Secure Registration**: Requires a pre-configured password to join.
- **Nickname Support**: Users can set a custom nickname for the event.
- **Automatic Pairing**: Triggers the raffle automatically when the participant limit is reached.
- **Mutual Matching**: Ensures pairs are mutual (Couples) as per requirements.
- **Dockerized**: specific `Dockerfile` and `docker-compose.yml` for easy deployment on VPS.

## Prerequisites

- Docker & Docker Compose
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Configuration

Control the bot behavior using Environment Variables (in `.env` or `docker-compose.yml`):

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Your Telegram Bot Token | **Required** |
| `MAX_USERS` | Total number of participants. **Must be EVEN**. | `10` |
| `PASSWORD` | Password required to join | `secret123` |

## Installation & Deployment

1. **Clone/Copy** the project files to your server.
2. **Set up** the `.env` file or configure variables in `docker-compose.yml`.
3. **Run** with Docker Compose:

```bash
docker-compose up -d --build
```

## Usage Flow

1. **Start**: User sends `/start`.
2. **Setup**: User uses the buttons to:
   - ➜ **Set Nickname**: Enter the name others will see.
   - ➜ **Enter Password**: Enter the event password.
3. **Join**: Once both are valid (green checks ✅), the "Join Raffle" (📝 Inscribirse) button becomes active.
4. **Raffle**: When the Nth user joins (defined by `MAX_USERS`), the bot shuffles the list and privately messages every user with their assigned partner.

## Technical Details

- Built with `python-telegram-bot`.
- Uses in-memory state management (reset on restart).
- Enforces an even number of participants for mutual pairing.
