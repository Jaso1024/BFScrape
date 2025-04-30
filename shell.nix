# shell.nix - Development environment for BFScrape

{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python with pip
    python310
    python310Packages.pip
    python310Packages.virtualenv
    
    # Chrome and chromedriver for Selenium
    chromium
    chromedriver
    
    # Development tools
    pre-commit
    
    # Additional build dependencies
    gnumake
    gcc
  ];

  shellHook = ''
    # Create and activate virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      virtualenv venv
    fi
    source venv/bin/activate
    
    # Install development dependencies (in the venv, not via nix)
    if [ -f "pyproject.toml" ]; then
      pip install -e ".[dev]"
    else
      pip install -e .
      if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
      fi
    fi
    
    # Set up pre-commit hooks if .pre-commit-config.yaml exists
    if [ -f .pre-commit-config.yaml ]; then
      pre-commit install
      echo "Pre-commit hooks installed."
    else
      echo "No .pre-commit-config.yaml found. Skipping pre-commit setup."
    fi
    
    # Set PATH to include chromedriver
    export PATH="${pkgs.chromedriver}/bin:$PATH"
    
    echo "BFScrape development environment ready."
    echo "Python virtual environment activated. Run 'deactivate' to exit."
  '';
} 