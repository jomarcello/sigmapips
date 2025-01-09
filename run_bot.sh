#!/bin/bash

# Function to cleanup before starting
cleanup() {
    echo "Cleaning up..."
    pkill -f "python.*bot.py"
    sleep 2
}

# Cleanup before starting
cleanup

while true; do
    echo "Starting bot..."
    python3.9 bot.py
    
    # If the bot exits with an error
    if [ $? -ne 0 ]; then
        echo "Bot exited with error. Cleaning up and restarting in 5 seconds..."
        cleanup
        sleep 5
    else
        echo "Bot stopped normally. Exiting..."
        break
    fi
done
