#!/bin/bash

# Interactive Demo Script for Fast Fixup Finder
# This script walks users through the complete demonstration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_step() {
    echo -e "${CYAN}➤ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠  $1${NC}"
}

wait_for_user() {
    echo -e "\n${YELLOW}Press Enter to continue...${NC}"
    read -r
}

run_command() {
    local cmd="$1"
    local description="$2"
    
    echo -e "\n${BLUE}Running:${NC} ${GREEN}$cmd${NC}"
    if [ -n "$description" ]; then
        echo -e "${BLUE}Purpose:${NC} $description"
    fi
    echo -e "${BLUE}Output:${NC}"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    eval "$cmd"
    local exit_code=$?
    
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    if [ $exit_code -eq 0 ]; then
        print_success "Command completed successfully"
    else
        print_warning "Command completed with exit code: $exit_code"
    fi
    
    return $exit_code
}

check_requirements() {
    print_step "Checking requirements..."
    
    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ] || [ ! -d "testcase" ]; then
        echo -e "${RED}Error: Please run this script from the fastfixupfinder project root directory${NC}"
        echo -e "${RED}Expected files: pyproject.toml, testcase/ directory${NC}"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: python3 is required but not found${NC}"
        exit 1
    fi
    
    print_success "Requirements check passed"
}

setup_environment() {
    print_step "Setting up demo environment..."
    
    # Check if tool is installed
    if ! python3 -c "import fastfixupfinder" 2>/dev/null; then
        print_info "FastFixupFinder not installed. Installing in development mode..."
        pip install -e . || {
            print_warning "Installation failed. Will use PYTHONPATH method instead."
            export DEMO_USE_PYTHONPATH=1
        }
    else
        print_success "FastFixupFinder is already installed"
        export DEMO_USE_PYTHONPATH=0
    fi
}

get_command() {
    if [ "${DEMO_USE_PYTHONPATH:-0}" = "1" ]; then
        echo "PYTHONPATH=. python3 -m fastfixupfinder.cli"
    else
        echo "fastfixupfinder"
    fi
}

# Main demo function
main() {
    print_header "🚀 Fast Fixup Finder Interactive Demo"
    
    echo -e "This demo will walk you through the complete Fast Fixup Finder experience:"
    echo -e "• Explore the test repository structure"
    echo -e "• Examine the commit history" 
    echo -e "• View current changes"
    echo -e "• Run the fixup finder tool"
    echo -e "• See the tool identify fixup targets"
    echo -e "• Optionally create fixup commits"
    
    wait_for_user
    
    # Check requirements
    check_requirements
    
    # Setup environment
    setup_environment
    
    # Change to testcase directory
    print_header "📁 Entering Test Repository"
    print_step "Changing to testcase directory..."
    cd testcase || {
        echo -e "${RED}Error: Cannot access testcase directory${NC}"
        exit 1
    }
    print_success "Now in testcase directory: $(pwd)"
    
    wait_for_user
    
    # Show repository structure
    print_header "🏗️  Repository Structure"
    run_command "ls -la" "Show all files in the test repository"
    
    wait_for_user
    
    # Show git history
    print_header "📚 Git Commit History"
    run_command "git log --oneline --graph" "Display the commit history with visual graph"
    
    wait_for_user
    
    # Show current changes
    print_header "🔍 Current Working Directory Changes"
    run_command "git status --short" "Show modified files"
    
    echo -e "\n${BLUE}Let's examine what changes were made:${NC}"
    wait_for_user
    
    run_command "git diff --stat" "Show change statistics"
    
    wait_for_user
    
    run_command "git diff" "Show detailed changes"
    
    wait_for_user
    
    # Run fastfixupfinder status
    print_header "🎯 Fast Fixup Finder - Status Check"
    local cmd=$(get_command)
    run_command "$cmd status" "Check what fixup targets are available"
    
    wait_for_user
    
    # Run detailed analysis
    print_header "🔬 Fast Fixup Finder - Detailed Analysis"
    run_command "$cmd analyze" "Show detailed analysis of changes and target commits"
    
    wait_for_user
    
    # Run dry-run
    print_header "🧪 Fast Fixup Finder - Dry Run Preview"
    run_command "$cmd create --dry-run" "Preview what fixup commits would be created"
    
    wait_for_user
    
    # Ask if user wants to create actual fixup commits
    print_header "💾 Create Fixup Commits?"
    echo -e "${YELLOW}Would you like to actually create the fixup commits?${NC}"
    echo -e "${YELLOW}(This will modify the git repository)${NC}"
    echo -e "\n${CYAN}Options:${NC}"
    echo -e "  ${GREEN}y${NC} - Yes, create fixup commits interactively"
    echo -e "  ${GREEN}a${NC} - Yes, create all fixup commits automatically"
    echo -e "  ${RED}n${NC} - No, skip this step"
    echo -e "\nChoice (y/a/n): "
    read -r choice
    
    case $choice in
        [Yy]*)
            print_step "Running interactive fixup creation..."
            echo -e "${BLUE}You'll be prompted to select which fixups to create.${NC}"
            echo -e "${BLUE}Try entering: ${GREEN}1,2${NC} to create fixups for the first two targets${NC}"
            wait_for_user
            $cmd create --interactive
            ;;
        [Aa]*)
            print_step "Creating all fixup commits automatically..."
            $cmd create
            ;;
        *)
            print_info "Skipping fixup commit creation"
            ;;
    esac
    
    # Show final state
    if [[ $choice =~ ^[YyAa] ]]; then
        wait_for_user
        print_header "🎉 Final Repository State"
        run_command "git log --oneline -10" "Show recent commits including any new fixups"
        
        echo -e "\n${GREEN}Great! You can now apply these fixup commits using:${NC}"
        echo -e "${CYAN}git rebase -i --autosquash HEAD~<number_of_commits>${NC}"
        echo -e "\n${BLUE}This will automatically squash the fixup commits into their target commits.${NC}"
    fi
    
    wait_for_user
    
    # Demo completion
    print_header "🏁 Demo Complete!"
    
    echo -e "${GREEN}Congratulations! You've successfully completed the Fast Fixup Finder demo.${NC}"
    echo -e "\n${CYAN}What you've learned:${NC}"
    echo -e "• How to check for potential fixup targets"
    echo -e "• How to analyze changes and their original commits"
    echo -e "• How to preview and create fixup commits"
    echo -e "• How the tool traces changes back to their source commits"
    
    echo -e "\n${CYAN}Next steps:${NC}"
    echo -e "• Try using the tool on your own projects"
    echo -e "• Read the documentation: README.md and TESTCASE.md"
    echo -e "• Explore the source code in fastfixupfinder/"
    
    echo -e "\n${PURPLE}Thank you for trying Fast Fixup Finder! 🚀${NC}"
    
    # Return to original directory
    cd ..
}

# Error handling
trap 'echo -e "\n${RED}Demo interrupted. Returning to parent directory...${NC}"; cd ..; exit 1' INT

# Run the main demo
main "$@"