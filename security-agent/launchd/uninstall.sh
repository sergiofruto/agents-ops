#!/bin/zsh
# Stop the security agent and remove it from login items.
PLIST=com.sergiofruto.security-agent.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/$PLIST 2>/dev/null
rm -f ~/Library/LaunchAgents/$PLIST
echo "Removed."
