# Fast Fixup Finder Workflows

This document describes all possible workflows for using Fast Fixup Finder to manage fixup and squash commits.

---

## 📋 Table of Contents

1. [Quick Status Check](#1-quick-status-check)
2. [Non-Interactive Auto-Create](#2-non-interactive-auto-create)
3. [Interactive Mode (Simplified)](#3-interactive-mode-simplified)
4. [Dry-Run Preview](#4-dry-run-preview)
5. [Limiting by Commit Range](#5-limiting-by-commit-range)
6. [Converting Fixup to Squash (Resquash)](#6-converting-fixup-to-squash-resquash)
7. [Restore from Backup](#7-restore-from-backup)
8. [Organization Email Filtering](#8-organization-email-filtering)
9. [Complete End-to-End Workflow](#9-complete-end-to-end-workflow)

---

## 1. Quick Status Check

**Use Case**: Quickly see what fixup targets are available without making any changes.

### Commands:

```bash
# Default status (smart filtering)
fastfixupfinder status

# Compact one-line format
fastfixupfinder status --oneline

# Detailed analysis with line-by-line breakdown
fastfixupfinder status --detailed

# Only show high-confidence fixup targets
fastfixupfinder status --fixups-only

# Include all changes (no filtering)
fastfixupfinder status --include-all
```

### Example Output:

```
🎯 Found 2 potential fixup targets:

• 08743fb3: Add basic calculator with add and subtract functions
  👤 Author: John Doe <john@example.com>
  📁 File: main.py
  📝 Changed lines: 3
```

### When to Use:
- Before starting work to see what fixups are pending
- To verify changes are being detected correctly
- As part of your daily workflow to maintain clean history

---

## 2. Non-Interactive Auto-Create

**Use Case**: Automatically create all fixup commits without any prompts (fastest workflow).

### Command:

```bash
# Create all fixup commits automatically
fastfixupfinder create

# Skip automatic backup
fastfixupfinder create --no-backup
```

### Workflow:
1. Tool analyzes all changes
2. Auto-assigns lines to target commits
3. Creates fixup commits for all targets
4. Creates automatic backup tag
5. Shows rebase command
6. Suggests resquash command for conversions

### Example:

```bash
$ fastfixupfinder create

🎯 Found 2 potential fixup targets:
[Shows table with targets]

🚀 Creating fixup commits...

✅ Created fixup commit a1b2c3d4 for 08743fb3
✅ Created fixup commit b2c3d4e5 for 59912895

💡 Tip: To convert any fixup to squash with message editing:
   fastfixupfinder resquash <commit-sha>

🚀 To apply the fixup commits, run:
    git rebase -i --autosquash HEAD~5
```

### When to Use:
- All changes are clearly fixups
- You trust the auto-assignment
- Speed is priority
- Want to decide on message editing later (using resquash)

---

## 3. Interactive Mode (Simplified)

**Use Case**: Quickly select and create fixup commits with review.

### Command:

```bash
# Interactive mode - creates fixup commits only
fastfixupfinder create -i
```

### Workflow:

**Step 1: Select Targets**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Target Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [ ] 1. 08743fb3  Add basic calculator functions (3 files, 12 lines)
  [ ] 2. 59912895  Fix validation logic (1 file, 4 lines)
  [ ] 3. abc12345  Update documentation (2 files, 8 lines)

Commands: 1,3,5 | 1-3 (range) | all | info N | done
→ 1,3
✅ Added 2 target(s), total: 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Target Selection (2 of 3 selected)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [✓] 1. 08743fb3  Add basic calculator functions (3 files, 12 lines)
  [ ] 2. 59912895  Fix validation logic (1 file, 4 lines)
  [✓] 3. abc12345  Update documentation (2 files, 8 lines)

Commands: 1,3,5 | 1-3 (range) | all | info N | done
→ done
```

**Step 2: View Auto-Assigned Lines**
```
🔍 Line Assignment Summary
All lines auto-assigned based on git blame analysis

  1. 08743fb3
     📁 main.py: 3 lines
  2. abc12345
     📁 utils.py: 2 lines
     📁 helpers.py: 3 lines
```

**Step 3: Create Fixup Commits**
```
🚀 Creating fixup commits...

✅ Created fixup commit a1b2c3d4 for 08743fb3
✅ Created fixup commit b2c3d4e5 for abc12345

✅ Created 2 fixup commit(s)

💡 Tip: To convert any fixup to squash with message editing:
   fastfixupfinder resquash <commit-sha>
```

### Interactive Commands:

**Target Selection:**
- `1,3,5` - Select specific targets
- `1-3` - Select range of targets
- `all` - Select all targets
- `info N` - Show detailed information about target N
- `done` - Finish selection

### When to Use:
- Need to review what will be committed before creating
- Want to inspect target details with `info`
- Selective target creation
- Quick fixup workflow with confirmation

### Converting to Squash:
After creating fixup commits, use the resquash command to convert specific ones:
```bash
fastfixupfinder resquash <commit-sha>
```
See workflow #6 for details on the resquash command.

---

## 4. Dry-Run Preview

**Use Case**: Preview what would happen without making any changes.

### Commands:

```bash
# Preview non-interactive mode
fastfixupfinder create --dry-run

# Preview interactive mode
fastfixupfinder create -i --dry-run
```

### Output:

```
🔍 Git commands that would be executed:

╒════════╤═══════════════════════════════════════════╕
│ Step   │ Git Command                               │
╞════════╪═══════════════════════════════════════════╡
│ 1      │ git add --patch main.py  # auto-select... │
├────────┼───────────────────────────────────────────┤
│ 2      │ git commit --fixup 08743fb3 --no-verify   │
╘════════╧═══════════════════════════════════════════╛
```

### When to Use:
- First time using the tool
- Verifying command sequences
- Documenting workflows
- Testing before actual commit
- Debugging issues

---

## 5. Limiting by Commit Range

**Use Case**: Only search and create fixups for commits after a specific point in history.

### Commands:

```bash
# View status for commits after a specific SHA1
fastfixupfinder status --limit abc1234

# Create fixups only for commits after a specific SHA1
fastfixupfinder create --limit abc1234

# Combine with other options
fastfixupfinder status --limit abc1234 --detailed
fastfixupfinder create --limit abc1234 --interactive
```

### Use Cases:
- Working on recent commits only (ignore old history)
- CI/CD pipelines that process specific commit ranges
- Feature branch fixups (limit to commits since branch point)
- Avoiding fixup targets from long-completed features
- Performance optimization for large repositories

### Example Workflow:

```bash
# Get recent commit to use as limit
$ git log --oneline -10
abc1234 Recent feature work
def5678 Earlier work
...

# Only fix recent changes
$ fastfixupfinder create --limit abc1234

# Shows only fixup targets for commits after abc1234
# (current changes + abc1234 and later commits)
```

---

## 6. Converting Fixup to Squash (Resquash)

**Use Case**: Convert an already-created fixup! commit to squash! with message editing.

### Command:

```bash
fastfixupfinder resquash <commit-sha>
```

### Workflow:

**Method 1: Direct (if at HEAD)**
```bash
# If the fixup commit is at HEAD
$ fastfixupfinder resquash a1b2c3d4

🔄 Converting fixup to squash: a1b2c3d4

Current message: fixup! Add basic calculator functions...

✏️  Opening editor to edit commit message...
[Editor opens with original target message]

✅ New message: Add basic calculator with improved error handling

Convert fixup to squash? [Y/n]: y

🔄 Rewriting commit...

✅ Successfully converted to squash commit: e5f6a7b8
```

**Method 2: During Interactive Rebase**
```bash
# Start interactive rebase
$ git rebase -i HEAD~10

# In editor, mark the fixup commit for 'edit'
pick abc1234 Some commit
edit def5678 fixup! Target commit  # ← Mark as 'edit'
pick ghi9012 Another commit

# Save and exit, git will stop at the fixup commit

# Now convert it
$ fastfixupfinder resquash def5678

# Continue rebase
$ git rebase --continue
```

### Requirements:
- Must be at the commit (HEAD) or in interactive rebase
- Commit must start with `fixup!`

### When to Use:
- Realized you need to edit the message after creating fixup
- Converting batch fixups to selective squashes
- Cleanup before pushing
- Changing strategy mid-rebase

---

## 7. Restore from Backup

**Use Case**: Undo changes and restore to state before fixup creation.

### Command:

```bash
fastfixupfinder restore
```

### Workflow:
1. Shows list of backup tags
2. Select which backup to restore
3. Confirms restoration
4. Resets to backup state

### Example:

```bash
$ fastfixupfinder restore

Available backups:
1. fastfixupfinder_backup_20250924_143022 (2 hours ago)
2. fastfixupfinder_backup_20250924_120515 (5 hours ago)

Select backup to restore (or 'cancel'): 1

⚠️  This will reset your repository to the backup state
Continue? [y/N]: y

✅ Restored to backup: fastfixupfinder_backup_20250924_143022
```

### Alternative (Manual):
```bash
# List backup tags
$ git tag | grep fastfixupfinder_backup

# Reset to specific backup
$ git reset --hard fastfixupfinder_backup_20250924_143022
```

### When to Use:
- Made wrong fixup assignments
- Need to undo and try different approach
- Emergency recovery
- Experimentation without risk

---

## 8. Organization Email Filtering

**Use Case**: Only create fixups for commits by your team/organization.

### Command:

```bash
# Only fixup commits from @mycompany.com authors
fastfixupfinder status --org-email ".*@mycompany\.com"

# Create fixups only for organization commits
fastfixupfinder create --org-email ".*@mycompany\.com"

# Interactive with filtering
fastfixupfinder create -i --org-email ".*@mycompany\.com"
```

### When to Use:
- Working on open-source with external contributors
- Don't want to fixup third-party code
- Team policy to only fixup own commits
- Multi-organization repositories

---

## 9. Complete End-to-End Workflow

**Use Case**: Recommended workflow for day-to-day use.

### Full Example:

```bash
# Step 1: Make your changes
$ vim src/calculator.py src/utils.py
$ # ... make changes ...

# Step 2: Check what fixup targets exist
$ fastfixupfinder status
🎯 Found 3 potential fixup targets:
• 08743fb3: Add basic calculator...
• 59912895: Add utility functions...
• abc12345: Fix validation logic...

# Step 3: Use interactive mode to create fixups
$ fastfixupfinder create -i

[Follow interactive workflow:]
- Select targets: 1,3
- View auto-assigned lines
- Mark target 1 as squash
- Edit squash message
- Create commits

✅ Created 2 commit(s): 1 fixup, 1 squash

# Step 4: Review what was created
$ git log --oneline -5
a1b2c3d squash! Add basic calculator with improved error handling
b2c3d4e fixup! Fix validation logic
abc1234 Fix validation logic
59912895 Add utility functions
08743fb3 Add basic calculator functions

# Step 5: Apply the fixups with rebase
$ git rebase -i --autosquash HEAD~5

[Editor opens showing:]
pick 08743fb3 Add basic calculator functions
squash a1b2c3d squash! Add basic calculator with improved error handling
pick 59912895 Add utility functions
pick abc1234 Fix validation logic
fixup b2c3d4e fixup! Fix validation logic

# Save and exit - git automatically applies fixups/squashes

# Step 6: Verify clean history
$ git log --oneline -3
abc1234 Fix validation logic
59912895 Add utility functions
08743fb3 Add basic calculator with improved error handling

# Step 7: Push
$ git push
```

### Optional: Convert Fixup to Squash Later
```bash
# If you realize you want to edit a fixup message
$ git rebase -i HEAD~5
# Mark fixup commit for 'edit'

$ fastfixupfinder resquash <fixup-sha>
# Edit message

$ git rebase --continue
```

---

## 🎯 Decision Tree: Which Workflow to Use?

```
Do you need to review changes before creating?
├─ No → Use workflow #2 (Non-Interactive Auto-Create)
│
└─ Yes → Do you need selective target creation?
    ├─ No → Use workflow #2 with --dry-run first
    │
    ├─ Yes, simple → Use workflow #3 (Interactive Mode)
    │
    └─ Yes, complex → Use workflow #4 (Visual GUI Mode)

Need to edit commit messages (squash)?
└─ Use workflow #6 (Resquash) after creating fixups

Already created fixups but need to convert to squash?
└─ Use workflow #6 (Resquash)

Need to undo everything?
└─ Use workflow #7 (Restore from Backup)
```

---

## 📝 Quick Reference

| What I Want | Command |
|------------|---------|
| Just check status | `fastfixupfinder status` |
| Create all fixups fast | `fastfixupfinder create` |
| Review before creating | `fastfixupfinder create --dry-run` |
| Select specific targets | `fastfixupfinder create -i` |
| Visual drag-and-drop | `fastfixupfinder gui` |
| Convert fixup to squash | `fastfixupfinder resquash <sha>` |
| Undo everything | `fastfixupfinder restore` |
| Filter by organization | Add `--org-email ".*@company\.com"` |

---

## 🔗 See Also

- [README.md](README.md) - Getting started and installation
- [INTERACTIVE_GUIDE.md](INTERACTIVE_GUIDE.md) - Detailed interactive mode guide
- [SAFETY.md](SAFETY.md) - Safety features and recovery procedures
