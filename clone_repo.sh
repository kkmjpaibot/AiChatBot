#!/bin/bash

# Check if repository URL is provided
if [ -z "$1" ]
then
    echo "Please provide the repository URL"
    echo "Usage: ./clone_repo.sh <repository_url>"
    exit 1
fi

# Store the repository URL
REPO_URL=$1

# Create backup of existing directory if it exists
if [ -d "aibot(1)" ]; then
    echo "Creating backup of existing directory..."
    mv "aibot(1)" "aibot(1)_backup_$(date +%Y%m%d_%H%M%S)"
fi

# Clone the repository
echo "Cloning repository from $REPO_URL..."
git clone "$REPO_URL" "aibot(1)"

# Check if clone was successful
if [ $? -eq 0 ]; then
    echo "Repository cloned successfully!"
    echo "Your repository is now in c:/xampp/htdocs/aibot(1)"
else
    echo "Failed to clone repository. Please check the URL and try again."
fi
