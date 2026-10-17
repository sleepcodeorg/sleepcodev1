# SleepCode Deployment Guide

This document explains how to schedule SleepCode to run unattended overnight using systemd or cron.

---

## Safety and Requirements

- **Keep the Machine On:** The computer must remain powered on and awake during the scheduled night window for SleepCode to execute tasks.
- **Environment File Security:** Store API keys in an environment file permissions-restricted to mode `0600` (`chmod 600 ~/.sleepcode/env`). Never inline plain API keys inside systemd unit files or crontabs.
- **Morning Review:** Every morning, review the generated report (`sleepcode report --latest`) and review task branches created under `sleepcode/<slug>-<timestamp>`.

---

## Option 1: systemd User Service & Timer

*(Status: UNTESTED - systemd user session bus is not active inside this container sandbox environment)*

Systemd can manage overnight SleepCode executions without root privileges using a user timer and service.

### 1. Create Environment File

Create `~/.sleepcode/env` with mode 0600:

```bash
mkdir -p ~/.sleepcode
touch ~/.sleepcode/env
chmod 600 ~/.sleepcode/env
```

Add your provider key to `~/.sleepcode/env`:
```env
GROQ_API_KEY=your-api-key-here
```

### 2. Service Unit: `~/.config/systemd/user/sleepcode-night.service`

```ini
[Unit]
Description=SleepCode Overnight Execution Service
After=network.target

[Service]
Type=oneshot
EnvironmentFile=%h/.sleepcode/env
ExecStart=/usr/local/bin/sleepcode night start --window 23:00-07:00 --budget-usd 5.00

[Install]
WantedBy=default.target
```

### 3. Timer Unit: `~/.config/systemd/user/sleepcode-night.timer`

```ini
[Unit]
Description=Timer for SleepCode Overnight Execution

[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Enable and Start Systemd Timer

```bash
systemctl --user daemon-reload
systemctl --user enable --now sleepcode-night.timer
systemctl --user list-timers
```

---

## Option 2: Cron Job

*(Status: UNTESTED - cron daemon is not running inside this container sandbox environment)*

For systems without systemd, add an entry to your user crontab (`crontab -e`):

```cron
# Run SleepCode overnight runner at 23:00 every night
0 23 * * * export $(cat $HOME/.sleepcode/env | xargs) && /usr/local/bin/sleepcode night start --window 23:00-07:00 --budget-usd 5.00 >> $HOME/.sleepcode/cron.log 2>&1
```
