#!/usr/bin/env bash
# ==============================================================================
# GTA 6 AI Shorts Automation — 1-Click Cloud VPS Deployment Script
# Supports: Ubuntu 22.04 / 24.04 LTS, Debian 12
# Works on: DigitalOcean, Hetzner, AWS EC2, GCP, Linode, Oracle Cloud Free Tier
# ==============================================================================

set -e

echo "=== [1/5] Updating system packages and installing FFmpeg & Python ==="
apt-get update -y
apt-get install -y python3 python3-pip python3-venv ffmpeg fonts-dejavu fonts-freefont-ttf git curl

echo "=== [2/5] Setting up project directory at /opt/gta6-agent ==="
mkdir -p /opt/gta6-agent
cp -r . /opt/gta6-agent/
cd /opt/gta6-agent

echo "=== [3/5] Installing Python dependencies ==="
pip3 install --no-cache-dir -r requirements.txt

echo "=== [4/5] Setting up systemd background service ==="
cp gta6-automation.service /etc/systemd/system/gta6-automation.service
systemctl daemon-reload
systemctl enable gta6-automation.service
systemctl restart gta6-automation.service

echo "=== [5/5] Checking service status ==="
systemctl status gta6-automation.service --no-pager

echo ""
echo "======================================================================"
echo " SUCCESS! The GTA 6 Automation Engine is now running 24/7 in background!"
echo " Logs: journalctl -u gta6-automation -f"
echo " Channel: @gta-6-rampage"
echo "======================================================================"
