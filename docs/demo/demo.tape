# vhs tape file for the kaggle-skill v2.1.0 README demo.
#
# Renders to docs/demo/install-and-demo.gif when you run:
#   vhs docs/demo/demo.tape
#
# Install vhs: brew install vhs    (or: go install github.com/charmbracelet/vhs@latest)
#
# Re-record after material UX changes. See docs/demo/demo-script.md for the
# matching asciinema instructions if you prefer that format.

Output docs/demo/install-and-demo.gif
Set FontSize 14
Set Width 1100
Set Height 700
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms
Set PlaybackSpeed 1.0

# Open Claude Code (placeholder — actual recording happens inside a real session)
Type "claude"
Enter
Sleep 2s

# Step 1: add the marketplace
Type "/plugin marketplace add shepsci/claude-marketplace"
Enter
Sleep 3s

# Step 2: install the plugin
Type "/plugin install kaggle-skill@shepsci"
Enter
Sleep 3s

# Step 3: ask in plain English to set up credentials
Type "set up my Kaggle credentials"
Enter
Sleep 5s

# Step 4: competition overview demo
Type "summarize the rules and evaluation metric for the titanic competition"
Enter
Sleep 8s

# Step 5: hackathon demo
Type "pull every writeup from kaggle-measuring-agi and group by track"
Enter
Sleep 8s

Sleep 2s
