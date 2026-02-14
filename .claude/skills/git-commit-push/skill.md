---
name: Git Commit and Push
description: Stage all changes (including new files), commit with a descriptive message, and push to GitHub. Use this skill when the user asks to commit, push, or save changes to git.
---

# Git Commit and Push Skill

Automatically stage all changes (including new files), create a commit, and push to the remote repository.

## Usage

This skill will:
1. Run `git status` to show what will be committed
2. Run `git add .` to stage all changes (including new files)
3. Create a commit with a descriptive message
4. Push to the remote repository (origin/main)

## Commit Message Format

Follow conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `style:` - Code style changes
- `test:` - Test updates
- `chore:` - Build/tool updates

Example:
```
feat: add stock screening module

- Add fundamental indicators filtering
- Implement technical indicators screening
- Add industry classification

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## GitHub Repository

- **Username**: austinxyz
- **Repository**: https://github.com/austinxyz/stock.git
- **Branch**: main

## What Gets Committed

- Modified files
- New files (untracked files)
- Deleted files

**Note**: Files listed in `.gitignore` are automatically excluded.

## Common File Patterns

Files that are typically committed:
- Source code: `*.java`, `*.vue`, `*.js`, `*.ts`
- Configuration: `*.md`, `*.json`, `*.yaml`, `*.yml`
- Database: `*.sql`
- Documentation: `docs/**/*`, `*.md`

Files that are ignored (via `.gitignore`):
- Build outputs: `target/`, `dist/`, `node_modules/`
- Environment files: `.env`, `*.env.*`
- IDE files: `.idea/`, `.vscode/`
- Log files: `*.log`
