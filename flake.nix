{
  description = "puss-say: A CLI tool that mimics macOS say command using KittenTTS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Override stdenv with a higher Darwin minimum version for onnxruntime compatibility
        stdenvDarwin13 = pkgs.stdenv.override (old: {
          targetPlatform = pkgs.stdenv.targetPlatform // {
            darwinMinVersion = "13.0";
            darwinSdkVersion = "13.0";
          };
        });

        python = pkgs.python313;

        # Common runtime libraries needed for audio
        runtimeLibs = [
          pkgs.portaudio
          pkgs.libsndfile
          pkgs.stdenv.cc.cc.lib
          pkgs.espeak-ng
        ];

        # Platform-specific library path variable
        libPathVar = if pkgs.stdenv.isDarwin then "DYLD_LIBRARY_PATH" else "LD_LIBRARY_PATH";

        # Load workspace from current directory
        workspace = uv2nix.lib.workspace.loadWorkspace {
          workspaceRoot = ./.;
        };

        # Create overlay from workspace
        overlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel"; # Prefer binary wheels to avoid build issues
        };

        # Build fixups overlay for packages that need setuptools
        pyprojectOverrides = final: prev: {
          kittentts = prev.kittentts.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
              final.setuptools
            ];
          });
        };

        # Python set with overlays
        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages {
            inherit python;
            stdenv = if pkgs.stdenv.isDarwin then stdenvDarwin13 else pkgs.stdenv;
          }).overrideScope
            (
              pkgs.lib.composeManyExtensions [
                pyproject-build-systems.overlays.default
                overlay
                pyprojectOverrides
              ]
            );

        # Create base virtualenv
        baseVirtualenv = pythonSet.mkVirtualEnv "puss-say-env" workspace.deps.default;

      in
      {
        packages = {
          # Use the individual package directly with proper wrapping
          default = pythonSet.puss-say.overrideAttrs (old: {
            # Add makeWrapper to wrap the binary
            nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
              pkgs.makeWrapper
            ];

            # Wrap the installed binary with proper paths
            postInstall = (old.postInstall or "") + ''
              # Wrap the binary with necessary runtime libraries and Python path
              # binutils is needed for `ld` so it can find the libraries

              wrapProgram $out/bin/puss-say \
                --prefix ${libPathVar} : ${pkgs.lib.makeLibraryPath runtimeLibs} \
                --prefix PATH : ${
                  pkgs.lib.makeBinPath (
                    [ pkgs.espeak-ng ]
                    ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
                      pkgs.binutils
                    ]
                  )
                } \
                --set PYTHONPATH "${baseVirtualenv}/${python.sitePackages}"
            '';
          });

          # Also keep the virtualenv package for development
          virtualenv = baseVirtualenv;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            baseVirtualenv
            pkgs.uv
          ];

          env = {
            # Don't create venv using uv
            UV_NO_SYNC = "1";

            # Force uv to use nixpkgs Python interpreter
            UV_PYTHON = python.interpreter;

            # Prevent uv from downloading managed Python's
            UV_PYTHON_DOWNLOADS = "never";

            # Set library path for portaudio and other libraries
            "${libPathVar}" = pkgs.lib.makeLibraryPath runtimeLibs;
          };

          shellHook = ''
            # Undo dependency propagation by nixpkgs.
            unset PYTHONPATH

            # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
            export REPO_ROOT=$(git rev-parse --show-toplevel)
          '';
        };
      }
    );
}
