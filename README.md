# Orpheus
The Orpheus System transforms static slides into interactive lecture videos with lifelike professor avatars, combining expressive narration, visual presence, and dynamic content to create engaging, personalized learning experiences.

## Architecture
<!---
The diagram was created with [Apollon](https://apollon.ase.in.tum.de/).
You can edit it by adjusting [OrpheusArchitecture.apollon](./OrpheusArchitecture.apollon).
We recommend using [VsCode](https://code.visualstudio.com/) with the [Apollon Extension](https://marketplace.visualstudio.com/items?itemName=TUMAET.apollon-vscode) to do so.

Once you edited the diagram, make sure to export it as svg to replace the existing [OrpheusArchitecture.svg](./OrpheusArchitecture.svg).
-->
<div style="text-align: center;">
  <img src="./OrpheusArchitecture.svg" alt="Orpheus System Architecture" style="max-width: 80%; height: auto;">
</div>

## API Interface Documentation

TODO: exchange with actual service descriptions
| Service                      | Description                                                                                                                                                                              | OpenAPI Specification                                                                  |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| **AI Core**                  | Orchestrates lecture generation from user prompts, creating a lecture script, and managing asynchronous jobs for creating interactive slides and videos with lifelike professor avatars. | [AI Core](./core/service_core_v1.yaml)                                                 |
| **Document Intelligence**    | Retrieves content related to the student question from instructor provided lecture slides and materials.                                                                                 | [Document Intelligence](./document-intelligence/service_document-intelligence_v1.yaml) |
| **Slide Generation**         | Generates lecture slides from a lecture script, stores generated slides and provides their generation status and download URL.                                                           | [Slide Service](./slides/service_slides_v1.yaml)                                       |
| **Avatar Generation**        | Generates short videos of lifelike professor avatars with expressive narration.                                                                                                          |                                                                                        |
| **Lecture Content Delivery** | Content Delivery Network (CDN) that stores the lecturer avatar videos and lecture slides.                                                                                                |                                                                                        |

<!--
TODOS
Open questions:
* Migrate to service levels instead
* Slide Generation vs folder name?
* Avatar Generation vs folder name?
* ai-core vs folder name?
* format the architecture 16:9
-->

## Getting Started
### Initial Setup
#### 1. Install Python 3.13.7 using pyenv
##### Linux (Debian/Ubuntu)
1. Install system dependencies for building Python (one-time setup)
    ```bash
    sudo apt update
    sudo apt install -y build-essential curl git \
    libssl-dev zlib1g-dev libncurses5-dev libbz2-dev libreadline-dev \
    libsqlite3-dev libffi-dev liblzma-dev tk-dev uuid-dev
    ```
2. Install pyenv (via the pyenv-installer)
    ```bash
    curl https://pyenv.run | bash
    ```
3. Add pyenv to your shell and reload it
   1. For bash
      ```bash
      echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
      echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
      echo 'eval "$(pyenv init -)"' >> ~/.bashrc
      ```
   2. For zsh
      ```bash
      echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
      echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
      echo 'eval "$(pyenv init -)"' >> ~/.zshrc
      ```
   **Important**: Restart your terminal or run `exec "$SHELL"` for the changes to take effect
   ```bash
   exec "$SHELL"
   ```
4. Install Python 3.13.7 and set it as the global default version
```bash
pyenv install 3.13.7
pyenv global 3.13.7
``` 
5. Verify the installation
```bash
python --version
```
Expected output: Python 3.13.7

##### macOS
1. Install Homebrew if you haven't already
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```
2. Install pyenv
    ```bash
    brew install pyenv
    ```
3. Add pyenv to your shell and reload it
   For zsh (the default on modern macOS):
   ```bash
   echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
   echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
   echo 'eval "$(pyenv init -)"' >> ~/.zshrc
   ```
   **Important**: Restart your terminal or run `exec "$SHELL"` for the changes to take effect
   ```bash
   exec "$SHELL"
   ```
4. Install Python 3.13.7 and set it as the global default version
   ```bash
   pyenv install 3.13.7
   pyenv global 3.13.7
   ```
5. Verify the installation
   ```bash
   python --version
   ```
   Expected output: Python 3.13.7

##### Windows (PowerShell, run as Administrator)
1. Install pyenv-win via PowerShell 
    Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"; Remove-Item "./install-pyenv-win.ps1"
2. Add pyenv to your PowerShell session
    The following lines are automatically added to your $PROFILE.
    You may need to run them manually for the current session or restart your terminal.
    ```bash
    $env:PYENV = [System.Environment]::GetEnvironmentVariable('PYENV','User')
    $env:PYENV_HOME = [System.Environment]::GetEnvironmentVariable('PYENV_HOME','User')
    $env:PYENV_ROOT = [System.Environment]::GetEnvironmentVariable('PYENV_ROOT','User')
    $env:Path = [System.Environment]::GetEnvironmentVariable('path','User')
    ```
    **Important**: Restart your PowerShell window to ensure the PATH changes are active.
3. Update pyenv-win to get the latest list of available versions
    ```bash
    pyenv update
    ``` 
4. Install Python 3.13.7 and set it as the global default version
    ```bash
    pyenv install 3.13.7
    pyenv global 3.13.7
    ```
5. Verify the installation
    ```bash
    python --version
    ```
    Expected output: Python 3.13.7

    (Optional) Check which version pyenv is managing
    ```bash
    pyenv version
    ```
    Expected output: 3.13.7 (set by C:\Users\YourUser\.pyenv\pyenv-win\version)
