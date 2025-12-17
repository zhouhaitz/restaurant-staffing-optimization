#!/bin/bash

# Script to set up GitHub remote and push repository

echo "=========================================="
echo "GitHub Repository Setup"
echo "=========================================="
echo ""

# Check if remote already exists
if git remote | grep -q "^origin$"; then
    echo "⚠️  Remote 'origin' already exists:"
    git remote -v
    read -p "Do you want to update it? (y/n): " update_remote
    if [ "$update_remote" != "y" ]; then
        echo "Exiting. No changes made."
        exit 0
    fi
    git remote remove origin
fi

# Get GitHub username
read -p "Enter your GitHub username: " github_username

# Get repository name
read -p "Enter repository name (or press Enter for 'restaurant-staffing-optimization'): " repo_name
repo_name=${repo_name:-restaurant-staffing-optimization}

# Construct repository URL
repo_url="https://github.com/${github_username}/${repo_name}.git"

echo ""
echo "Repository URL: ${repo_url}"
echo ""
read -p "Is this correct? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "Exiting. No changes made."
    exit 0
fi

# Add remote
echo ""
echo "Adding remote repository..."
git remote add origin "${repo_url}"

# Check if repository exists on GitHub
echo ""
echo "⚠️  IMPORTANT: Make sure you've created the repository on GitHub first!"
echo "   Go to: https://github.com/new"
echo "   Repository name: ${repo_name}"
echo "   (Don't initialize with README, .gitignore, or license)"
echo ""
read -p "Have you created the repository on GitHub? (y/n): " repo_created

if [ "$repo_created" != "y" ]; then
    echo ""
    echo "Please create the repository first, then run this script again."
    echo "Or run these commands manually after creating the repo:"
    echo "  git remote add origin ${repo_url}"
    echo "  git push -u origin main"
    exit 0
fi

# Push to remote
echo ""
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo "   Repository: ${repo_url}"
else
    echo ""
    echo "❌ Push failed. Common issues:"
    echo "   1. Repository doesn't exist on GitHub"
    echo "   2. Authentication required (use GitHub CLI or SSH keys)"
    echo "   3. Branch name mismatch (try: git push -u origin main:main)"
fi

