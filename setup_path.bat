@echo off
REM PATH setup script for Fast Fixup Finder (Windows)

echo 🛠️  Fast Fixup Finder PATH Setup (Windows)
echo ==========================================

REM Run the Python setup script
python setup_path.py

echo.
echo 💡 Quick manual setup (if automatic setup failed):
echo    1. Press Win + R, type 'sysdm.cpl', press Enter
echo    2. Click 'Environment Variables...'
echo    3. Under 'User variables', select 'Path' and click 'Edit...'
echo    4. Click 'New' and add the user Scripts directory
echo    5. Click OK to save
echo    6. Restart your terminal/PowerShell

pause