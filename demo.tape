# deepworm Demo Recording
# Run with: vhs demo.tape

Output demo.gif

Set Shell "zsh"
Set FontSize 15
Set Width 1200
Set Height 700
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Padding 20
Set Framerate 8
Set PlaybackSpeed 1.5

Require deepworm

# Title comment
Type "# deepworm - AI deep research from your terminal"
Enter
Sleep 1s

# Show help briefly
Type "deepworm --help | head -25"
Enter
Sleep 3s

# Clear
Type "clear"
Enter
Sleep 500ms

# Set API key (demo placeholder)
Type "# Step 1: Set your API key"
Enter
Type "# export GOOGLE_API_KEY='your-key-here'"
Enter
Type "# (or use: deepworm interactive → /keys)"
Enter
Sleep 1.5s

# Run the actual research with full pipeline
Type "deepworm 'quantum computing breakthroughs 2025' --depth 1 --breadth 1 -v --polish --graph stats"
Enter

# Wait for research to complete (~45s, at 1.5x playback = ~30s viewed)
Sleep 65s

# Final pause to see results
Sleep 4s
