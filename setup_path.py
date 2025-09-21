#!/usr/bin/env python3
"""
Automatic PATH setup utility for Fast Fixup Finder
Helps users configure their PATH to run the tool from anywhere
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
import site


def get_user_bin_path():
    """Get the user binary installation path."""
    user_base = site.getusersitepackages()
    if platform.system() == "Windows":
        # Windows: Scripts directory in user site-packages parent
        user_bin = Path(user_base).parent / "Scripts"
    else:
        # Linux/macOS: bin directory in user base
        user_base_dir = subprocess.run(
            [sys.executable, "-m", "site", "--user-base"],
            capture_output=True,
            text=True
        ).stdout.strip()
        user_bin = Path(user_base_dir) / "bin"
    
    return user_bin


def is_in_path(directory):
    """Check if directory is already in PATH."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    return str(directory) in path_dirs


def detect_shell():
    """Detect the user's shell and return appropriate config file."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    
    if "zsh" in shell:
        return home / ".zshrc"
    elif "fish" in shell:
        return home / ".config" / "fish" / "config.fish"
    elif "bash" in shell or not shell:  # Default to bash
        # Try .bashrc first, then .bash_profile, then .profile
        for bashrc in [".bashrc", ".bash_profile", ".profile"]:
            config_file = home / bashrc
            if config_file.exists():
                return config_file
        # If none exist, create .bashrc
        return home / ".bashrc"
    else:
        # Unknown shell, use .profile as fallback
        return home / ".profile"


def add_to_unix_path(user_bin_path):
    """Add user bin path to Unix shell configuration."""
    config_file = detect_shell()
    
    print(f"Detected shell config file: {config_file}")
    
    # Check if PATH is already configured
    if config_file.exists():
        content = config_file.read_text()
        if str(user_bin_path) in content:
            print("✓ PATH already configured in shell config")
            return True
    
    # Add PATH export to config file
    path_line = f'\n# Added by Fast Fixup Finder setup\nexport PATH="$PATH:{user_bin_path}"\n'
    
    try:
        with open(config_file, "a") as f:
            f.write(path_line)
        print(f"✓ Added PATH configuration to {config_file}")
        print(f"  Run: source {config_file}")
        print("  Or restart your terminal to apply changes")
        return True
    except Exception as e:
        print(f"✗ Failed to update {config_file}: {e}")
        return False


def add_to_windows_path(user_bin_path):
    """Add user bin path to Windows PATH."""
    try:
        # Try to use PowerShell to modify user PATH
        ps_command = f"""
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*{user_bin_path}*") {{
    $newPath = if ($currentPath) {{ "$currentPath;{user_bin_path}" }} else {{ "{user_bin_path}" }}
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "✓ Added to Windows user PATH"
    Write-Host "  Restart your terminal/PowerShell to apply changes"
}} else {{
    Write-Host "✓ PATH already configured"
}}
"""
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(f"✗ PowerShell command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to update Windows PATH automatically: {e}")
        print(f"Please manually add this to your PATH: {user_bin_path}")
        print("Instructions:")
        print("1. Press Win + R, type 'sysdm.cpl', press Enter")
        print("2. Click 'Environment Variables...'")
        print("3. Under 'User variables', select 'Path' and click 'Edit...'")
        print(f"4. Click 'New' and add: {user_bin_path}")
        print("5. Click OK to save")
        return False


def test_installation(user_bin_path):
    """Test if the fastfixupfinder command is available."""
    fastfixup_exe = user_bin_path / ("fastfixupfinder.exe" if platform.system() == "Windows" else "fastfixupfinder")
    
    if not fastfixup_exe.exists():
        print(f"⚠  Warning: {fastfixup_exe} not found")
        print("   Make sure you've installed the package with: pip install --user .")
        return False
    
    print(f"✓ Found executable: {fastfixup_exe}")
    
    # Test if command works in current environment
    try:
        result = subprocess.run(
            ["fastfixupfinder", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ Command works in current environment")
            return True
        else:
            print("⚠  Command not yet available (restart terminal)")
            return False
    except FileNotFoundError:
        print("⚠  Command not yet available (restart terminal or source shell config)")
        return False
    except Exception as e:
        print(f"⚠  Error testing command: {e}")
        return False


def main():
    """Main setup function."""
    print("🛠️  Fast Fixup Finder PATH Setup")
    print("=" * 40)
    
    # Get user binary path
    user_bin_path = get_user_bin_path()
    print(f"User binary path: {user_bin_path}")
    
    # Check if already in PATH
    if is_in_path(user_bin_path):
        print("✓ User binary directory is already in PATH")
    else:
        print("⚠  User binary directory not in PATH")
        
        # Add to PATH based on platform
        if platform.system() == "Windows":
            success = add_to_windows_path(user_bin_path)
        else:
            success = add_to_unix_path(user_bin_path)
        
        if not success:
            print("Manual PATH configuration required")
            return 1
    
    print("\n🧪 Testing installation...")
    test_installation(user_bin_path)
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Restart your terminal (or source your shell config)")
    print("2. Test with: fastfixupfinder --version")
    print("3. If that fails, use: python3 -m fastfixupfinder.cli --version")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())