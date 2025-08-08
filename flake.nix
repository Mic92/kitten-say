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

  outputs = { self, nixpkgs, flake-utils, uv2nix, pyproject-nix, pyproject-build-systems }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;

        # Load workspace from current directory
        workspace = uv2nix.lib.workspace.loadWorkspace {
          workspaceRoot = ./.;
        };

        # Create overlay from workspace
        overlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel"; # Prefer binary wheels to avoid build issues
        };

        # Build fixups overlay
        pyprojectOverrides = final: prev: {
          # Add setuptools for packages that need it
          kittentts = prev.kittentts.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or []) ++
              final.resolveBuildSystem {
                setuptools = [ ];
              };
          });

          docopt = prev.docopt.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or []) ++
              final.resolveBuildSystem {
                setuptools = [ ];
              };
          });

          curated-tokenizers = prev.curated-tokenizers.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or []) ++
              final.resolveBuildSystem {
                setuptools = [ ];
                cython = [ ];
              };
          });

          # Ignore missing CUDA libraries since we're using CPU only
          nvidia-cufile-cu12 = prev.nvidia-cufile-cu12.overrideAttrs (old: {
            autoPatchelfIgnoreMissingDeps = [
              "libmlx5.so.1"
              "librdmacm.so.1"
              "libibverbs.so.1"
            ];
          });

          nvidia-cusolver-cu12 = prev.nvidia-cusolver-cu12.overrideAttrs (old: {
            autoPatchelfIgnoreMissingDeps = [
              "libnvJitLink.so.12"
              "libcusparse.so.12"
              "libcublas.so.12"
              "libcublasLt.so.12"
            ];
          });

          nvidia-cusparse-cu12 = prev.nvidia-cusparse-cu12.overrideAttrs (old: {
            autoPatchelfIgnoreMissingDeps = [
              "libnvJitLink.so.12"
            ];
          });

          # Torch CUDA dependencies - ignore all since we're CPU only
          torch = prev.torch.overrideAttrs (old: {
            autoPatchelfIgnoreMissingDeps = [
              "libcudart.so.12"
              "libcusolver.so.11"
              "libcublas.so.12"
              "libcusparse.so.12"
              "libcudnn.so.9"
              "libcusparseLt.so.0"
              "libcufile.so.0"
              "libnvrtc.so.12"
              "libcuda.so.1"
              "libcufft.so.11"
              "libcurand.so.10"
              "libcublasLt.so.12"
              "libnccl.so.2"
              "libcupti.so.12"
            ];
          });

          # Add runtime library dependencies
          puss-say = prev.puss-say.overrideAttrs (old: {
            propagatedBuildInputs = (old.propagatedBuildInputs or []) ++ [
              pkgs.portaudio
              pkgs.libsndfile
            ];

            postInstall = (old.postInstall or "") + ''
              wrapProgram $out/bin/puss-say \
                --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [
                  pkgs.portaudio
                  pkgs.libsndfile
                  pkgs.stdenv.cc.cc.lib
                ]}
            '';

            nativeBuildInputs = (old.nativeBuildInputs or []) ++ [
              pkgs.makeWrapper
            ];
          });
        };

        # Python set with overlays
        pythonSet = (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope (
          pkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyprojectOverrides
          ]
        );

        # Import utility functions
        inherit (pkgs.callPackage pyproject-nix.build.util { }) mkApplication;

        # Create base virtualenv
        baseVirtualenv = pythonSet.mkVirtualEnv "puss-say-env" workspace.deps.default;

      in
      {
        packages = {
          # Use the individual package directly with proper wrapping
          default = pythonSet.puss-say.overrideAttrs (old: {
            # Add makeWrapper to wrap the binary
            nativeBuildInputs = (old.nativeBuildInputs or []) ++ [
              pkgs.makeWrapper
            ];
            
            # Wrap the installed binary with proper paths
            postInstall = (old.postInstall or "") + ''
              # Wrap the binary with necessary runtime libraries and Python path
              wrapProgram $out/bin/puss-say \
                --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [
                  pkgs.portaudio
                  pkgs.libsndfile
                  pkgs.stdenv.cc.cc.lib
                ]} \
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
          };

          shellHook = ''
            # Undo dependency propagation by nixpkgs.
            unset PYTHONPATH
            
            # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
            export REPO_ROOT=$(git rev-parse --show-toplevel)
          '';
        };
      });
}
