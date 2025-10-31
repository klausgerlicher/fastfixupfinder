# Safety Guide for Fast Fixup Finder

This guide provides strategies to protect your work when using Fast Fixup Finder.

## 🛡️ Built-in Safety Features

Fast Fixup Finder includes automatic safety features:

### Automatic Backup
```bash
# Creates automatic git stash backup before changes
fastfixupfinder create

# Skip automatic backup if needed
fastfixupfinder create --no-backup
```

### Restore from Backup
```bash
# List and restore from available backups
fastfixupfinder restore

# Restore specific backup
fastfixupfinder restore --backup-name "fastfixupfinder_backup_20240101_120000"
```

### Always Preview First
```bash
# Always run dry-run first to see what will happen
fastfixupfinder create --dry-run

# Use interactive mode for precise control
fastfixupfinder create --interactive
```

## 🔒 Manual Safety Strategies

### 1. Git Stash Method (Recommended)
```bash
# Create backup before using tool
git stash push -m "Pre-fixup backup $(date)"

# Use the tool
fastfixupfinder create --dry-run  # Always preview first
fastfixupfinder create --interactive

# If something goes wrong, restore
git stash list  # See available stashes
git stash pop   # Restore most recent stash
```

### 2. Branch-Based Protection
```bash
# Create backup branch from current state
git checkout -b backup-$(date +%Y%m%d-%H%M%S)

# Return to main branch and use tool
git checkout main
fastfixupfinder create --interactive

# If problems occur, restore from backup branch
git reset --hard backup-20240101-120000
```

### 3. Patch File Backup
```bash
# Create patch files of all changes
git diff > changes-backup-$(date +%Y%m%d-%H%M%S).patch
git diff --cached > staged-backup-$(date +%Y%m%d-%H%M%S).patch

# If you need to restore changes
git apply changes-backup-20240101-120000.patch
```

### 4. Working Directory Copy
```bash
# For extra paranoia, copy entire working directory
cp -r . ../my-project-backup-$(date +%Y%m%d-%H%M%S)
```

## ⚠️ Safety Checklist

Before using Fast Fixup Finder:

- [ ] **Commit important work** - Don't run on uncommitted critical changes
- [ ] **Run status first** - `fastfixupfinder status` to understand what it will do
- [ ] **Use dry-run** - `fastfixupfinder create --dry-run` to preview
- [ ] **Check git status** - Understand your current repository state
- [ ] **Create backup** - Use one of the manual methods above
- [ ] **Test on copy** - Try on a copy of your repo first if nervous

## 🚨 Emergency Recovery

If something goes wrong:

### 1. Check Git Reflog
```bash
# See recent commits and HEAD movements
git reflog

# Reset to previous state
git reset --hard HEAD@{1}  # or appropriate reflog entry
```

### 2. Restore from Fast Fixup Finder Backup
```bash
# List available automatic backups
git stash list | grep fastfixupfinder_backup

# Restore specific backup
fastfixupfinder restore
```

### 3. Undo Recent Commits
```bash
# Remove last N commits but keep changes
git reset --soft HEAD~N

# Remove last N commits and discard changes
git reset --hard HEAD~N
```

### 4. Restore from Manual Backup
```bash
# From stash
git stash apply stash@{N}

# From patch file  
git apply your-backup.patch

# From backup branch
git reset --hard backup-branch-name
```

## 🎯 Best Practices

### Development Workflow
1. **Work in feature branches** - Never use on main/master directly
2. **Small, frequent commits** - Easier to recover from issues
3. **Test first** - Always dry-run on test repositories
4. **Document backups** - Note what backups you've created

### Repository Hygiene
1. **Clean working directory** - Commit or stash unrelated changes first
2. **Meaningful commit messages** - Helps identify what to recover
3. **Regular pushes** - Remote backups are the best backups
4. **Backup branches** - Keep backup branches for important work

### Team Usage
1. **Training** - Ensure team members understand the tool
2. **Standards** - Establish team backup practices
3. **Review process** - Have experienced users review complex fixups
4. **Documentation** - Document any team-specific safety procedures

## 🔍 Verification After Use

After creating fixup commits:

```bash
# Verify the commits look correct
git log --oneline -10

# Check the changes in each fixup commit
git show <fixup-commit-hash>

# Verify your working directory is clean
git status

# Test that your code still works
# Run tests, build, etc.
```

## 📞 Getting Help

If you encounter issues:

1. **Check this safety guide** for recovery procedures
2. **Review git reflog** to understand what happened
3. **Use git stash/backup recovery** methods above
4. **Check command availability** - If `fastfixupfinder` command not found:
   ```bash
   # Use module syntax as fallback
   python3 -m fastfixupfinder.cli restore
   
   # Or check PATH configuration (see README.md)
   echo $PATH | grep -q "$(python3 -m site --user-base)/bin" || echo "PATH needs user bin directory"
   ```
5. **Report bugs** to the project repository with details
6. **Ask for help** with specific git commands if needed

Remember: Git is designed to be safe, and most operations are recoverable with the right knowledge!