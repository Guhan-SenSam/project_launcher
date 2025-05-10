# CursorLauncher ULauncher Extension

## Overview

This ULauncher extension allows you to quickly search for and open your projects in your favorite code editors/IDEs. It supports a two-step selection: first, pick your project, then choose the editor you want to open it with. You can configure your preferred editors in the extension preferences.

### Key Features

- Fast project search with caching and confidence scoring (fallback to default search if results are not confident)
- Two-step workflow: select project, then select editor
- Editor list is user-configurable (comma-separated in preferences)
- Custom icons for popular editors/IDEs
- Easily extensible to add more editors

## Supported Editors with Auto-Added Icons

The following editors/IDEs will automatically display their icon in the editor selection list if their command matches:

- Visual Studio Code (`code`)
- Cursor (`cursor`)
- Sublime Text (`subl`)
- IntelliJ IDEA (`idea`)
- PyCharm (`pycharm`)
- CLion (`clion`)
- WebStorm (`webstorm`)
- GoLand (`goland`)
- PhpStorm (`phpstorm`)

If you add any of these commands to your editor list in preferences, the extension will show the corresponding icon (make sure the icon file exists in the `images/` directory).

## How to Add/Configure Editors

1. Open ULauncher preferences.
2. Find the CursorLauncher extension.
3. In the "Editors" field, enter a comma-separated list of editor commands (e.g. `code,cursor,nvim`).
4. Save your preferences.

## Example: Making Cursor Work Universally

To make the `cursor` command available everywhere (for this extension and your terminal), follow these steps:

1. **Create the launcher script:**

   ```bash
   nano ~/.local/bin/cursor
   ```

   Add the following content:

   ```bash
   #!/bin/bash
   nohup /opt/cursor.AppImage "$@" > /dev/null 2>&1 &
   ```

   Replace `/opt/cursor.AppImage` with the actual path to your downloaded Cursor AppImage if different.

2. **Make it executable:**

   ```bash
   chmod +x ~/.local/bin/cursor
   ```

3. **Ensure `~/.local/bin` is in your PATH:**

   Add this line to your `~/.bashrc` **and** `~/.profile` (or `~/.bash_profile`):

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

   Then reload your profile:

   ```bash
   source ~/.profile
   ```

Now, the `cursor` command will be available everywhere, including for this extension.

## Troubleshooting

- If an editor does not launch, ensure its command is available in your PATH or defined as a function/alias.
- Make sure the icon files for your editors are present in the `images/` directory.
- Adjust the confidence threshold in preferences if search results are not as expected.

## Contributing

Feel free to submit PRs to add more editor icons or improve the extension!
