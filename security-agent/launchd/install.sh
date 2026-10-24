#!/bin/zsh
# Start the security agent at login (and now). Undo with uninstall.sh.
set -e
PLIST=com.sergiofruto.security-agent.plist
cp "$(dirname "$0")/$PLIST" ~/Library/LaunchAgents/$PLIST
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/$PLIST
echo "Installed. Dashboard: http://127.0.0.1:5007"
