#!/usr/bin/env bash
# Creates a small Ubuntu VM on your Azure student subscription and runs the agent on it 24/7.
# Works from Azure Cloud Shell or from Git Bash on Windows (after `az login`):
#
#   bash deploy/azure/deploy.sh
#
# Re-running it pushes the latest code and agent/.env to the existing VM and restarts the agent.
# Standard_B2ats_v2 / Standard_B1s are covered by the student free tier (750 h/month).
set -euo pipefail
export MSYS_NO_PATHCONV=1   # stop Git Bash on Windows rewriting /opt/... paths

RG=${RG:-jobagent-vm-koreacentral}
VM=${VM:-jobagent-vm}
LOCATION=${LOCATION:-koreacentral}
SIZE=${SIZE:-Standard_B2ats_v2}
HERE=$(cd "$(dirname "$0")/../.." && pwd)

[ -f "$HERE/agent/.env" ] || { echo "agent/.env is missing - copy agent/.env.example and fill it in first."; exit 1; }

if ! az vm show -g "$RG" -n "$VM" -o none 2>/dev/null; then
  az group create -n "$RG" -l "$LOCATION" -o none
  az vm create -g "$RG" -n "$VM" --image Ubuntu2204 --size "$SIZE" \
    --admin-username azureuser --generate-ssh-keys --public-ip-sku Standard \
    --nsg-rule NONE -o none   # no inbound ports: the bot only makes outbound connections
fi

# SSH is closed by --nsg-rule NONE, so files go in through run-command instead.
TARBALL=$(cd "$HERE" && tar czf - --exclude='agent/data' --exclude='__pycache__' agent deploy/azure/jobagent.service | base64 -w0)
# The script goes in a file (az reads @file) because it's too long for a Windows command line.
SCRIPT=$(mktemp)
cat > "$SCRIPT" <<SH
set -e
dpkg -s python3-venv >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq python3-venv; }
mkdir -p /opt/jobagent && cd /opt/jobagent
echo '$TARBALL' | base64 -d | tar xzf - --no-same-owner
[ -x venv/bin/pip ] || { rm -rf venv && python3 -m venv venv; }
venv/bin/pip install -q -r agent/requirements.txt
chown -R azureuser:azureuser /opt/jobagent && chmod 600 agent/.env
cp deploy/azure/jobagent.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable jobagent && systemctl restart jobagent
sleep 5 && systemctl is-active jobagent && journalctl -u jobagent -n 5 --no-pager
SH
command -v cygpath >/dev/null && SCRIPT_ARG=$(cygpath -w "$SCRIPT") || SCRIPT_ARG=$SCRIPT  # Windows az needs C:\ paths
az vm run-command invoke -g "$RG" -n "$VM" --command-id RunShellScript --scripts @"$SCRIPT_ARG" \
  --query "value[0].message" -o tsv
rm -f "$SCRIPT"
echo "Deployed to $VM in $RG. Send /start to your bot on Telegram."
echo "Logs: az vm run-command invoke -g $RG -n $VM --command-id RunShellScript --scripts 'journalctl -u jobagent -n 50 --no-pager' --query 'value[0].message' -o tsv"
