{
  description = "Mem UI - React frontend for Mem video tracking system";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Node.js and package managers
            nodejs_20
            nodePackages.npm
            nodePackages.pnpm
            nodePackages.yarn
            
            # Development tools
            git
            curl
            jq
            ripgrep
            fd
            
            # For testing
            chromium
            
            # Code quality tools
            nodePackages.prettier
            nodePackages.eslint
            nodePackages.typescript
            nodePackages.typescript-language-server
            
            # Build tools
            watchman
          ];
          
          shellHook = ''
            echo "🎥 Mem UI Development Environment"
            echo "================================"
            echo "Node: $(node --version)"
            echo "npm: $(npm --version)"
            echo ""
            echo "To get started:"
            echo "  1. Install deps: npm install"
            echo "  2. Start dev server: npm run dev"
            echo "  3. Run tests: npm test"
            echo "  4. Build for production: npm run build"
            echo ""
            echo "Environment variables:"
            echo "  Set VITE_API_BASE_URL in .env file"
            echo "  Default: http://localhost:8000"
            echo ""
            
            # Set environment variables for development
            export BROWSER=none  # Prevent auto-opening browser
            export NODE_ENV=development
            
            # Ensure node_modules/.bin is in PATH
            export PATH="$PWD/node_modules/.bin:$PATH"
          '';
          
          # Environment variables
          BROWSER = "none";
          NODE_ENV = "development";
        };
      });
}