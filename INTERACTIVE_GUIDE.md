# Interactive Mode Guide

This guide explains Fast Fixup Finder's interactive mode in detail, giving you complete control over which changes become fixup commits.

## 🎯 **What Interactive Mode Does**

Instead of automatically creating fixup commits for all detected changes, interactive mode lets you:
1. **Choose which target commits** to create fixups for
2. **Review individual lines** within each target
3. **Override automatic classifications** when needed
4. **Select exactly which lines** to include in each fixup

## 🚀 **Quick Start**

```bash
# Basic interactive mode
fastfixupfinder create --interactive

# Compact mode (for many changes)
fastfixupfinder create --interactive --oneline

# Preview first (recommended)
fastfixupfinder create --interactive --dry-run
```

## 🔄 **Two-Stage Process**

Interactive mode works in two stages: target selection, then line-level control.

### **Stage 1: Target Selection**

First, you choose which commits you want to potentially create fixups for:

```bash
🧠 Enhanced interactive mode with line-level classification control
Found 3 potential fixup targets:

1. 08743fb3: Add calculator functions
   👤 Author: John Doe <john@example.com>
   📁 Files: main.py
   📝 Changed lines: 3

2. 59912895: Fix validation logic  
   👤 Author: Jane Smith <jane@example.com>
   📁 Files: utils.py
   📝 Changed lines: 2

3. a1b2c3d4: Update documentation
   👤 Author: Bob Wilson <bob@example.com>
   📁 Files: README.md
   📝 Changed lines: 5

🎯 Select targets (comma-separated numbers, 'all', or 'none'): 
```

#### **Target Selection Options**

| Option | Example | What It Does | When To Use |
|--------|---------|--------------|-------------|
| **Specific numbers** | `1,3` or `2` or `1-3,5` | Selects only the numbered targets | You only want fixups for certain commits |
| **`all`** | `all` | Selects every target found | You want to review everything |
| **`none`** | `none` | Exits immediately, creates no fixups | Wrong timing, or no fixups needed |

#### **Detailed Target Selection Examples**

**Example 1: Specific Targets**
```bash
🎯 Select targets: 1,3
```
- ✅ Will process target #1 (calculator functions)
- ❌ Will skip target #2 (validation logic) 
- ✅ Will process target #3 (documentation)

**Example 2: All Targets**
```bash
🎯 Select targets: all
```
- ✅ Will process all 3 targets
- You'll review each one in the next stage

**Example 3: No Targets**
```bash
🎯 Select targets: none
❌ No targets selected. Exiting.
```
- Command exits immediately
- No fixup commits created

**Example 4: Flexible Syntax**
```bash
🎯 Select targets: 1-3,5    # Targets 1, 2, 3, and 5
🎯 Select targets: 2        # Just target 2
🎯 Select targets: 1,4,6    # Specific non-consecutive targets
```

### **Stage 2: Line-Level Control**

For each selected target, you review the individual changes:

```bash
🔍 Reviewing lines for target 08743fb3: Add calculator functions...

📄 main.py

  1. ~ Line 42: def calculate(a, b):
     Classification: Likely Fixup
  2. + Line 43: # Fixed bug in calculation  
     Classification: Likely Fixup
  3. + Line 44: return a + b  # TODO: handle edge cases
     Classification: Possible Fixup

🎯 Select lines from main.py (numbers, 'all', 'none', or 'auto'): 
```

#### **Line Selection Options**

| Option | Example | What It Does | When To Use |
|--------|---------|--------------|-------------|
| **Specific lines** | `1,3` or `1-2` | Selects only those line numbers | Precise control over changes |
| **`all`** | `all` | Includes every line in this file | You want all changes for this target |
| **`none`** | `none` | Skips this file entirely | This file shouldn't be a fixup |
| **`auto`** | `auto` | Uses automatic classification | Trust the AI's classification |

#### **Line Selection Examples**

**Example 1: Specific Lines**
```bash
🎯 Select lines from main.py: 1,3
  ✅ Selected 2 lines
```
- Only lines 1 and 3 will be included in the fixup
- Line 2 will be ignored

**Example 2: Auto Selection** 
```bash
🎯 Select lines from main.py: auto
  ✅ Auto-selected 2 lines based on classification
```
- Includes lines classified as "Likely Fixup" and "Possible Fixup"
- Excludes "Unlikely Fixup" and "New File" classifications

**Example 3: All Lines**
```bash
🎯 Select lines from main.py: all
  ✅ Selected 3 lines
```
- Every change in this file becomes part of the fixup

**Example 4: Skip File**
```bash
🎯 Select lines from main.py: none
```
- No changes from this file will be included
- Moves to next file or target

## 🧠 **Intelligent Classification System**

Each line is automatically classified to help guide your decisions:

| Classification | Color | Description | Examples |
|---------------|-------|-------------|----------|
| **🟢 Likely Fixup** | Green | High confidence this is a fixup | Comments, typos, string fixes, small bug fixes |
| **🟡 Possible Fixup** | Yellow | Could be fixup or small feature | Minor logic changes, parameter tweaks |
| **🔴 Unlikely Fixup** | Red | Probably new functionality | New functions, complex logic, architectural changes |
| **🟣 New File** | Magenta | Completely new files | Any file that didn't exist before |

### **What `auto` Selection Does**

When you choose `auto`, the tool includes:
- ✅ **Likely Fixup** lines (green)
- ✅ **Possible Fixup** lines (yellow)
- ❌ **Unlikely Fixup** lines (red)
- ❌ **New File** lines (magenta)

This gives you a balanced approach: includes obvious fixups and borderline cases, but excludes obvious new features.

## 📝 **Compact Mode (`--oneline`)**

For projects with many changes, compact mode provides streamlined output:

### **Compact Target Selection**
```bash
🧠 Interactive mode: 3 targets:
1. 08743fb3: Add calculator functions... (1 files, 3 lines)
2. 59912895: Fix validation logic... (1 files, 2 lines)  
3. a1b2c3d4: Update documentation... (1 files, 5 lines)

🎯 Select targets: 1,3
```

### **Compact Line Review**
```bash
🔍 08743fb3: Add calculator functions...
📄 main.py
3 lines: 2 likely 1 possible
  1. ~ L42: def calculate(a, b): [Likely]
  2. + L43: # Fixed bug in calculation [Likely]
  3. + L44: return a + b  # TODO: handle edge... [Possible]

🎯 Select from main.py (#s, 'all', 'none', 'auto'): auto
  ✅ Auto-selected 3 lines based on classification
```

**Benefits of compact mode:**
- Much less screen space used
- Faster to scan through many changes
- Shows classification summaries (e.g., "2 likely 1 possible")
- Truncated content for readability

## 🛡️ **When to Use Interactive Mode**

### **Perfect For:**
- **Mixed changes**: Some lines are fixups, others are new features
- **Learning the tool**: See what it detects and understand the classifications
- **Complex scenarios**: Multiple files with different types of changes
- **Precision needed**: You want exact control over what gets fixed up
- **Code review**: Verify the tool's detection before committing

### **Real-World Scenarios:**

**Scenario 1: Bug Fix + New Feature**
```
You fixed a typo in a function but also added a new parameter.
→ Use interactive mode to fixup only the typo, not the new parameter.
```

**Scenario 2: Documentation Updates**
```
You updated docs for multiple features across several commits.
→ Use interactive mode to create separate fixups for each original commit.
```

**Scenario 3: Refactoring Cleanup**
```
You did major refactoring but also fixed some small bugs found along the way.
→ Use interactive mode to extract just the bug fixes as fixups.
```

**Scenario 4: Multi-Branch Work**
```
You've been working on several features and found cross-cutting fixes.
→ Use interactive mode to precisely assign fixes to their original commits.
```

## 🚀 **Workflow Tips**

### **Best Practices:**
1. **Start with `auto`**: Let classification do the work first
2. **Use `--dry-run`**: Preview what will be created before committing
3. **Use `--oneline`**: More readable with many changes
4. **Review red classifications**: "Unlikely Fixup" items need human judgment
5. **Trust green classifications**: "Likely Fixup" items are usually correct

### **Common Patterns:**

**Quick Review Workflow:**
```bash
# 1. See what's available
fastfixupfinder status --oneline

# 2. Preview with auto-selection
fastfixupfinder create --interactive --oneline --dry-run

# 3. Create the fixups
fastfixupfinder create --interactive --oneline
```

**Precise Control Workflow:**
```bash
# 1. Detailed analysis first
fastfixupfinder status --detailed

# 2. Full interactive mode for control
fastfixupfinder create --interactive

# 3. Manual line selection as needed
```

**Bulk Processing Workflow:**
```bash
# For many changes, use compact mode with auto-selection
fastfixupfinder create --interactive --oneline
# Then use 'auto' for most files
```

## 🔍 **Understanding the Output**

### **Change Type Symbols:**
- **`+`** (green): Added line
- **`-`** (red): Deleted line  
- **`~`** (yellow): Modified line

### **Final Selection Summary:**
```bash
✅ Final selection: 5 lines across 2 files
```
This tells you exactly how many changes will be included in the fixup commit.

### **Commit Creation:**
```bash
✅ Created fixup commit a1b2c3d4 for 08743fb3
```
Shows the new fixup commit hash and which original commit it targets.

## 🎯 **Advanced Usage**

### **Range Selection:**
```bash
🎯 Select lines: 1-3,5,7-9    # Lines 1,2,3,5,7,8,9
🎯 Select lines: 1-5          # Lines 1,2,3,4,5
🎯 Select lines: 3,5,7        # Just lines 3,5,7
```

### **File-by-File Strategy:**
Some targets involve multiple files. You can handle each file differently:
```bash
📄 main.py
🎯 Select from main.py: auto     # Use auto-classification

📄 utils.py  
🎯 Select from utils.py: 1,3     # Manual selection

📄 README.md
🎯 Select from README.md: all    # Include everything
```

### **Mixed Strategies:**
You can combine approaches within a single session:
- `auto` for obvious files
- Manual selection for complex files
- `none` for files you want to skip
- `all` for files you trust completely

## 🚫 **What Interactive Mode Doesn't Do**

- **Doesn't modify files**: Only creates fixup commits
- **Doesn't change classifications**: You can override them, but can't retrain the AI
- **Doesn't handle conflicts**: If changes conflict, you'll need to resolve manually
- **Doesn't edit commit messages**: Fixup commits use standard `fixup!` format

Interactive mode gives you surgical precision over your fixup commits while still benefiting from intelligent automation. Use it whenever you need more control than the basic `create` command provides!