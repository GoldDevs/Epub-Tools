#!/bin/bash

# This script interactively generates standard community health files for a GitHub project,
# including issue templates, a contributing guide, and a code of conduct.

set -e # Exit immediately if a command exits with a non-zero status.

echo "--- GitHub Community File Generator ---"
echo "This script will create CONTRIBUTING.md, a CODE_OF_CONDUCT.md,"
echo "and issue templates for your project."
echo ""

# --- 1. Gather Information Interactively ---

# Suggest repository name from the current directory name
DEFAULT_REPO_NAME=$(basename "$(pwd)")
read -p "Enter your GitHub repository name [$DEFAULT_REPO_NAME]: " REPO_NAME
REPO_NAME=${REPO_NAME:-$DEFAULT_REPO_NAME}

# Ask for GitHub username
read -p "Enter your GitHub username: " GITHUB_USERNAME
if [ -z "$GITHUB_USERNAME" ]; then
    echo "Error: GitHub username cannot be empty."
    exit 1
fi

# Ask for a contact email for the Code of Conduct
read -p "Enter a contact email for the Code of Conduct: " CONTACT_EMAIL
if [ -z "$CONTACT_EMAIL" ]; then
    echo "Error: Contact email cannot be empty."
    exit 1
fi

echo ""
echo "--- Configuration Summary ---"
echo "Project URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo "Contact Email: $CONTACT_EMAIL"
echo ""

read -p "Is this correct? (y/n) " CONFIRM
echo ""

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 1
fi

# --- 2. Create Directories ---
echo "Creating directory structure .github/ISSUE_TEMPLATE..."
mkdir -p .github/ISSUE_TEMPLATE

# --- 3. Generate CONTRIBUTING.md ---
echo "Generating CONTRIBUTING.md..."
cat > CONTRIBUTING.md << EOL
# Contributing to $REPO_NAME

First off, thank you for considering contributing! It's people like you that make open source such a fantastic community.

All contributions are welcome, from reporting a bug to suggesting a new feature, or even submitting a pull request.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [$CONTACT_EMAIL](mailto:$CONTACT_EMAIL).

## How Can I Contribute?

### Reporting Bugs
- If you find a bug, please ensure it hasn't already been reported by searching through the [Issues](https://github.com/$GITHUB_USERNAME/$REPO_NAME/issues).
- If you're unable to find an open issue addressing the problem, please [open a new one](https://github.com/$GITHUB_USERNAME/$REPO_NAME/issues/new/choose). Be sure to use the **Bug Report** template and include as much detail as possible.

### Suggesting Enhancements
- If you have an idea for a new feature, first check the [Issues](https://github.com/$GITHUB_USERNAME/$REPO_NAME/issues) to see if it has been suggested before.
- If not, feel free to [open a new issue](https://github.com/$GITHUB_USERNAME/$REPO_NAME/issues/new/choose) using the **Feature Request** template.

### Pull Requests
Pull requests are the best way to propose changes to the codebase.

1.  **Fork the repo** on GitHub.
2.  **Clone your fork** locally.
3.  **Create a virtual environment** and install the package in "editable" mode:
    \`\`\`bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    \`\`\`
4.  **Create a new branch** for your changes (\`git checkout -b feature/MyAmazingFeature\`).
5.  Make your changes.
6.  **Commit your changes** with a descriptive commit message.
7.  **Push to your branch** (\`git push origin feature/MyAmazingFeature\`).
8.  **Open a Pull Request** against the \`main\` branch of the original repository.

## Styleguides
- Please follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code.
- Add comments to your code where the logic is complex.

Thank you again for your interest in contributing!
EOL

# --- 4. Generate CODE_OF_CONDUCT.md (using Contributor Covenant v2.1) ---
echo "Generating CODE_OF_CONDUCT.md..."
cat > CODE_OF_CONDUCT.md << EOL
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, religion, or sexual identity
and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment for our
community include:

*   Demonstrating empathy and kindness toward other people
*   Being respectful of differing opinions, viewpoints, and experiences
*   Giving and gracefully accepting constructive feedback
*   Accepting responsibility and apologizing to those affected by our mistakes,
    and learning from the experience
*   Focusing on what is best not just for us as individuals, but for the
    overall community

Examples of unacceptable behavior include:

*   The use of sexualized language or imagery, and sexual attention or
    advances of any kind
*   Trolling, insulting or derogatory comments, and personal or political attacks
*   Public or private harassment
*   Publishing others' private information, such as a physical or email
    address, without their explicit permission
*   Other conduct which could reasonably be considered inappropriate in a
    professional setting

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of
acceptable behavior and will take appropriate and fair corrective action in
response to any behavior that they deem inappropriate, threatening, offensive,
or harmful.

Community leaders have the right and responsibility to remove, edit, or reject
comments, commits, code, wiki edits, issues, and other contributions that are
not aligned to this Code of Conduct, and will communicate reasons for moderation
decisions when appropriate.

## Scope

This Code of Conduct applies within all community spaces, and also applies when
an individual is officially representing the community in public spaces.
Examples of representing our community include using an official e-mail address,
posting via an official social media account, or acting as an appointed
representative at an online or offline event.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the community leaders responsible for enforcement at
**[$CONTACT_EMAIL](mailto:$CONTACT_EMAIL)**.
All complaints will be reviewed and investigated promptly and fairly.

All community leaders are obligated to respect the privacy and security of the
reporter of any incident.

## Enforcement Guidelines

Community leaders will follow these Community Impact Guidelines in determining
the consequences for any action they deem in violation of this Code of Conduct:

### 1. Correction
**Community Impact**: Use of inappropriate language or other behavior deemed
unprofessional or unwelcome in the community.
**Consequence**: A private, written warning from community leaders, providing
clarity around the nature of the violation and an explanation of why the
behavior was inappropriate. A public apology may be requested.

### 2. Warning
**Community Impact**: A violation through a single incident or series
of actions.
**Consequence**: A warning with consequences for continued behavior. No
interaction with the people involved, including unsolicited interaction with
those enforcing the Code of Conduct, for a specified period of time. This
includes avoiding interaction in community spaces as well as external channels
like social media. Violating these terms may lead to a temporary or
permanent ban.

### 3. Temporary Ban
**Community Impact**: A serious violation of community standards, including
sustained inappropriate behavior.
**Consequence**: A temporary ban from any sort of interaction or public
communication with the community for a specified period of time. No public or
private interaction with the people involved, including unsolicited interaction
with those enforcing the Code of Conduct, is allowed during this period.
Violating these terms may lead to a permanent ban.

### 4. Permanent Ban
**Community Impact**: Demonstrating a pattern of violation of community
standards, including sustained inappropriate behavior, harassment of an
individual, or aggression toward or disparagement of classes of individuals.
**Consequence**: A permanent ban from any sort of public interaction within
the community.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.1, available at
[https://www.contributor-covenant.org/version/2/1/code_of_conduct.html][v2.1].

[homepage]: https://www.contributor-covenant.org
[v2.1]: https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
EOL

# --- 5. Generate Bug Report Template ---
echo "Generating bug report template..."
cat > .github/ISSUE_TEMPLATE/bug_report.md << EOL
---
name: 🐞 Bug Report
description: Create a report to help improve the application
title: "[BUG] A brief, descriptive title of the bug"
labels: ["bug", "triage"]
assignees: ''

---

**Describe the Bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Press key '....'
3. See error

**Expected Behavior**
A clear and concise description of what you expected to happen.

**Screenshots or Logs**
If applicable, add screenshots, GIFs, or copy-paste any relevant log files from \`~/.config/$REPO_NAME/logs/\` to help explain your problem.

**Environment:**
 - OS: [e.g., Android Termux, Ubuntu 22.04]
 - Python Version: [e.g., 3.10]
 - Terminal: [e.g., Termux, GNOME Terminal]
 - App Version: [e.g., 2.0.0]

**Additional Context**
Add any other context about the problem here.

---
### Before Submitting
- [ ] I have searched the [existing issues](https://github.com/$GITHUB_USERNAME/$REPO_NAME/issues) to make sure this is not a duplicate.
- [ ] I have provided a clear title and description.
EOL

# --- 6. Generate Feature Request Template ---
echo "Generating feature request template..."
cat > .github/ISSUE_TEMPLATE/feature_request.md << EOL
---
name: ✨ Feature Request
description: Suggest an idea or new functionality for this project
title: "[FEATURE] A brief, descriptive title of the feature"
labels: ["enhancement", "needs-discussion"]
assignees: ''

---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. *I'm always frustrated when [...]*.

**Describe the Solution You'd Like**
A clear and concise description of what you want to happen.

**Describe Alternatives You've Considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional Context**
Add any other context or mockups about the feature request here.

---
### Before Submitting
- [ ] I have searched the [existing issues](https://github.com/$GITHUB_USERNAME/$REPO_NAME/issues) to make sure this is not a duplicate.
- [ ] I have provided a clear title and description.
EOL

echo ""
echo "--- ✅ Success! ---"
echo "Generated the following files:"
echo "  - CONTRIBUTING.md"
echo "  - CODE_OF_CONDUCT.md"
echo "  - .github/ISSUE_TEMPLATE/bug_report.md"
echo "  - .github/ISSUE_TEMPLATE/feature_request.md"
echo ""
echo "Next step: Commit these new files to your repository."
echo "git add . && git commit -m \"docs: Add community health files\""
echo ""