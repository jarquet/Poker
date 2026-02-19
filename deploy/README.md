# Deploying Poker Web on Raspberry Pi

Run the poker web app in Docker on a Raspberry Pi, accessible on your local network (e.g. 192.168.8.*), managed as a systemd service.

## Prerequisites

- Raspberry Pi with Docker and Docker Compose installed
- Project copied to the Pi (e.g. `/home/pi/poker`)

## Quick Start

```bash
cd /home/pi/poker
docker compose build
docker compose up -d
```

Open http://\<raspberry-pi-ip\>:8000 from any device on your network.

## Systemd Service

To run the app as a systemd service (starts on boot, restarts on failure):

### 1. Edit the service file

Update `WorkingDirectory` in `deploy/poker-web.service` to match your project path:

```ini
WorkingDirectory=/home/pi/poker
```

If you use `docker-compose` (hyphen) instead of `docker compose`, change:

```ini
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
```

### 2. Install the service

```bash
sudo cp deploy/poker-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable poker-web
```

### 3. Build the image (first time only)

```bash
cd /home/pi/poker
docker compose build
```

### 4. Start the service

```bash
sudo systemctl start poker-web
sudo systemctl status poker-web
```

### 5. Useful commands

| Command | Description |
|---------|-------------|
| `sudo systemctl start poker-web` | Start the container |
| `sudo systemctl stop poker-web` | Stop the container |
| `sudo systemctl restart poker-web` | Restart the container |
| `sudo systemctl status poker-web` | Check status |
| `docker compose logs -f` | View logs (run from project dir) |

## Firewall

If `ufw` is enabled:

```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

## Troubleshooting

- **Can't connect from other devices**: Check the Pi's IP with `hostname -I`, ensure port 8000 is open, and that the container is running (`docker ps`).
- **Container exits**: Run `docker compose logs` to inspect errors.
- **Compose not found**: Install the Docker Compose plugin or use `docker-compose` (standalone) and update the service file.
