{
  description = "Mem - Video work tracking system with local AI";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pythonPackages = pkgs.python311Packages;
        
        # Fetch uv binary directly for faster installation
        uv = pkgs.stdenv.mkDerivation rec {
          pname = "uv";
          version = "0.5.4";
          
          src = if pkgs.stdenv.isDarwin then
            pkgs.fetchurl {
              url = "https://github.com/astral-sh/uv/releases/download/${version}/uv-aarch64-apple-darwin.tar.gz";
              sha256 = "sha256-0000000000000000000000000000000000000000000=";  # TODO: Update with actual Darwin hash
            }
          else if pkgs.stdenv.isLinux && pkgs.stdenv.isx86_64 then
            pkgs.fetchurl {
              url = "https://github.com/astral-sh/uv/releases/download/${version}/uv-x86_64-unknown-linux-gnu.tar.gz";
              sha256 = "sha256-xbY9HNColCRhlSUMA0+dgtZG3I9xjx9CTOwrsaQuexc=";
            }
          else if pkgs.stdenv.isLinux && pkgs.stdenv.isAarch64 then
            pkgs.fetchurl {
              url = "https://github.com/astral-sh/uv/releases/download/${version}/uv-aarch64-unknown-linux-gnu.tar.gz";
              sha256 = "sha256-0000000000000000000000000000000000000000000=";  # TODO: Update with actual ARM hash
            }
          else
            throw "Unsupported platform for uv";
          
          nativeBuildInputs = with pkgs; [ autoPatchelfHook ];
          
          buildInputs = with pkgs; [ stdenv.cc.cc.lib ];
          
          sourceRoot = ".";
          
          installPhase = ''
            mkdir -p $out/bin
            # The extracted directory contains uv-x86_64-unknown-linux-gnu/uv
            if [ -f ./uv-x86_64-unknown-linux-gnu/uv ]; then
              cp ./uv-x86_64-unknown-linux-gnu/uv $out/bin/uv
            elif [ -f ./uv-aarch64-unknown-linux-gnu/uv ]; then
              cp ./uv-aarch64-unknown-linux-gnu/uv $out/bin/uv
            elif [ -f ./uv-aarch64-apple-darwin/uv ]; then
              cp ./uv-aarch64-apple-darwin/uv $out/bin/uv
            elif [ -f ./uv ]; then
              cp ./uv $out/bin/uv
            else
              echo "Error: Could not find uv binary"
              find . -name "uv" -type f
              exit 1
            fi
            chmod +x $out/bin/uv
          '';
        };
        
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python
            python311
            pythonPackages.pip
            pythonPackages.virtualenv
            
            # Package manager
            uv
            
            # System dependencies
            ffmpeg
            sqlite
            portaudio
            
            # Browser automation
            chromium
            playwright-driver.browsers
            
            # Development tools
            git
            gnumake
            curl
            wget
            jq
            nodejs_20  # For Playwright
            
            # Optional but useful
            ripgrep
            fd
            lazysql
            
            # For building native extensions
            gcc
            stdenv.cc.cc.lib
            pkg-config
            
            # Additional libraries for Chromium
            xorg.libX11
            xorg.libXcomposite
            xorg.libXcursor
            xorg.libXdamage
            xorg.libXext
            xorg.libXfixes
            xorg.libXi
            xorg.libXrandr
            xorg.libXrender
            xorg.libXtst
            xorg.libxcb
            nss
            nspr
            alsa-lib
            cups
            libdrm
            expat
            dbus
            libxkbcommon
            pango
            cairo
            at-spi2-atk
            at-spi2-core
            gtk3
            glib
            fontconfig
            freetype
          ];
          
          shellHook = ''
            echo "🎬 Mem Development Environment"
            echo "================================"
            echo "Python: $(python --version)"
            echo "FFmpeg: $(ffmpeg -version | head -n1)"
            echo "SQLite: $(sqlite3 --version)"
            echo "uv: $(uv --version)"
            echo "Node: $(node --version)"
            echo ""
            echo "To get started:"
            echo "  1. Install deps: uv sync"
            echo "  2. Run tests: make test"
            echo ""
            
            # Set up library paths for native extensions
            export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
            
            # Set up Playwright browser paths
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs.chromium}/bin"
            export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
            export CHROMIUM_EXECUTABLE_PATH="${pkgs.chromium}/bin/chromium"
            
            # For headless operation
            export DISPLAY=:99
          '';
          
          # Environment variables
          PYTHONPATH = ".";
          MEM_ENV = "development";
        };
      });
}