# vhs tape file for the kaggle-skill v2.3.0 README demo.
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

# Open Claude Code. The asciinema recording is the canonical issue #7 artifact.
Type "claude"
Enter
Sleep 2s

# Step 1: add the marketplace
Type "/plugin marketplace add shepsci/kaggle-skill"
Enter
Sleep 3s

# Step 2: install the plugin
Type "/plugin install kaggle@shepsci"
Enter
Sleep 3s

# Step 3: ask in plain English to verify credentials without displaying secrets
Type "set up my Kaggle credentials and verify them without showing any secrets"
Enter
Sleep 5s

# Step 4: competition overview demo
Type "summarize the rules and evaluation metric for the titanic competition"
Enter
Sleep 8s

# Step 5: forums/writeups demo
Type "search recent Kaggle competition writeup discussions and show three useful results"
Enter
Sleep 8s

Sleep 2s
