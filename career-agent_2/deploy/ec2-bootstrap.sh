#!/usr/bin/env bash
# Bootstraps Career Agent on a fresh Ubuntu EC2 instance.
#
# Usage: upload career-agent.zip to the instance first (scp), then:
#   chmod +x ec2-bootstrap.sh && ./ec2-bootstrap.sh
#
# If you're doing this on every "fresh instance" session, read the README's
# EC2 section about baking an AMI once you've got this working — it turns
# this whole script into a ~30 second launch instead of a multi-minute one.
set -euo pipefail

echo "==> Installing system packages…"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip unzip

# LaTeX is optional and SLOW to install from scratch (a full texlive can take
# 5-10+ minutes on a fresh instance). Skip it if you're fine with .docx only
# on this instance, or bake it into your AMI instead. Uncomment to install:
# sudo apt-get install -y texlive texlive-latex-extra texlive-fonts-recommended

echo "==> Unpacking Career Agent…"
cd "$HOME"
unzip -o -q career-agent.zip
cd career-agent

echo "==> Setting up Python environment…"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from template — edit it now:"
  echo "    - ANTHROPIC_API_KEY (required)"
  echo "    - CAREER_AGENT_HOST=0.0.0.0   (to allow access from outside the VM)"
  echo "    - BASIC_AUTH_USERNAME / BASIC_AUTH_PASSWORD (required if exposing publicly)"
fi

echo ""
echo "==> Done. Next steps:"
echo "    1. nano .env   (fill in the values above)"
echo "    2. If you have a backup zip, restore it via the app's 'Restore backup' button"
echo "       after starting, or scp it in and use the /api/backup/restore endpoint directly."
echo "    3. source .venv/bin/activate && python run.py"
echo ""
echo "    Remember to lock down the EC2 security group to your own IP for the app's port,"
echo "    not 0.0.0.0/0 — Basic Auth alone isn't encryption."
