{
  description = "Python 3.12 dev shell with code-cursor (unfree enabled)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    flake-utils.url = "github:numtide/flake-utils";

    deploy-rs.url = "github:serokell/deploy-rs";

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
    { self
    , nixpkgs
    , flake-utils
    , deploy-rs
    , uv2nix
    , pyproject-nix
    , pyproject-build-systems
    , ...
    }:
    let

    in
    {
      images = {
        rpi-4 =
          (self.nixosConfigurations.pi.extendModules {
            modules = [ "${nixpkgs}/nixos/modules/installer/sd-card/sd-image-aarch64.nix" ];
          }).config.system.build.sdImage;
      };
      nixosConfigurations."pi" = nixpkgs.lib.nixosSystem {
        system = "aarch64-linux";
        specialArgs = { inherit self; };
        modules = [
          ./nixos/configuration.nix
        ];
      };
      deploy.nodes.pi = {
        hostname = "10.0.0.5";
        fastConnection = true;
        sshUser = "root";
        user = "root";
        #interactiveSudo = true;
        profiles.system = {
          path = deploy-rs.lib.aarch64-linux.activate.nixos self.nixosConfigurations.pi;
        };
      };

      # This is highly advised, and will prevent many possible mistakes
      checks = builtins.mapAttrs (system: deployLib: deployLib.deployChecks self.deploy) deploy-rs.lib;
    }
    // flake-utils.lib.eachDefaultSystem (system:
    let
      # Import stable pkgs with unfree allowed
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };

      inherit (nixpkgs) lib;

      # Package containing all static sounds
      soundFiles = pkgs.stdenv.mkDerivation
        {
          pname = "sounds";
          version = "1.0";

          src = ./sounds/.;

          installPhase = ''
            cp -r $src $out
          '';
        };

      # Load a uv workspace from a workspace root.
      # Uv2nix treats all uv projects as workspace projects.
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      # Create package overlay from workspace.
      overlay = workspace.mkPyprojectOverlay {
        # Prefer prebuilt binary wheels as a package source.
        # Sdists are less likely to "just work" because of the metadata missing from uv.lock.
        # Binary wheels are more likely to, but may still require overrides for library dependencies.
        sourcePreference = "wheel"; # or sourcePreference = "sdist";
        # Optionally customise PEP 508 environment
        # environ = {
        #   platform_release = "5.10.65";
        # };
      };

      # Extend generated overlay with build fixups
      #
      # Uv2nix can only work with what it has, and uv.lock is missing essential metadata to perform some builds.
      # This is an additional overlay implementing build fixups.
      # See:
      # - https://pyproject-nix.github.io/uv2nix/FAQ.html
      pyprojectOverrides = _final: _prev: {

        audio-guestbook = _prev.audio-guestbook.overrideAttrs (old: {
          # ${pkgs.alsa-utils}/bin/aplay"'
          #substituteInPlace /src/audio_guestbook/async_audio_test.py \
          #      --replace-fail '_FFPLAY = "ffplay"' '_FFPLAY = "${pkgs.ffmpeg}/bin/ffplay"'
          postPatch = ''
            substituteInPlace src/audio_guestbook/statemachine.py \
              --replace-fail 'SOUNDS_PATH_STR = "sounds/"' 'SOUNDS_PATH_STR = "${soundFiles}"' 
            substituteInPlace src/audio_guestbook/async_audio_test.py \
              --replace-fail '_APLAY = "aplay"' '_APLAY = "${pkgs.alsa-utils}/bin/aplay"' 
            substituteInPlace src/audio_guestbook/async_audio_test.py \
              --replace-fail '_ARECORD = "arecord"' '_ARECORD = "${pkgs.alsa-utils}/bin/arecord"' 
            substituteInPlace src/audio_guestbook/async_audio_test.py \
              --replace-fail '_FFPLAY = "ffplay"' '_FFPLAY = "${pkgs.ffmpeg}/bin/ffplay"' 
            substituteInPlace src/audio_guestbook/audio_manager.py \
              --replace-fail '_MPV = "mpv"' '_MPV = "${pkgs.mpv}/bin/mpv"' 
            substituteInPlace src/audio_guestbook/audio_manager.py \
              --replace-fail '_ARECORD = "arecord"' '_ARECORD = "${pkgs.alsa-utils}/bin/arecord"' 
          '';
        });


        # Implement build fixups here.
        # Note that uv2nix is _not_ using Nixpkgs buildPythonPackage.
        # It's using https://pyproject-nix.github.io/pyproject.nix/build.html
      };

      # Use Python 3.12 from nixpkgs
      python = pkgs.python312;

      # Construct package set
      pythonSet =
        # Use base package set from pyproject.nix builders
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.default
              overlay
              pyprojectOverrides
            ]
          );

    in
    {




      # Package a virtual environment as our main application.
      #
      # Enable no optional dependencies for production build.
      packages =
        let
          venv = pythonSet.mkVirtualEnv "audio-guestbook-env" workspace.deps.default;
        in

        {
          default = venv;
          audioFiles = soundFiles;
        } //
        lib.optionalAttrs pkgs.stdenv.isLinux {
          # Expose Docker container in packages
          docker =

            pkgs.dockerTools.buildLayeredImage {
              name = "telephone";
              config = {
                Cmd = [
                  "${venv}/bin/telephone"
                ];
                Env = [
                ];
              };
            };
        };

      # Make telephone runnable with `nix run`
      apps.default = {
        type = "app";
        program = "${self.packages.x86_64-linux.default}/bin/aplay -l telephone";
      };

      apps.deploy = {
        type = "app";
        program = toString (pkgs.writeShellScript "deploy" ''
          ${deploy-rs.packages.x86_64-linux.deploy-rs}/bin/deploy --skip-checks .#pi 
        '');
      };


      # This example provides two different modes of development:
      # - Impurely using uv to manage virtual environments
      # - Pure development using uv2nix to manage virtual environments
      devShells = {
        # It is of course perfectly OK to keep using an impure virtualenv workflow and only use uv2nix to build packages.
        # This devShell simply adds Python and undoes the dependency leakage done by Nixpkgs Python infrastructure.
        impure = pkgs.mkShell {
          packages = [
            python
            pkgs.uv
          ];
          env =
            {
              # Prevent uv from managing Python downloads
              UV_PYTHON_DOWNLOADS = "never";
              # Force uv to use nixpkgs Python interpreter
              UV_PYTHON = python.interpreter;
            }
            // lib.optionalAttrs pkgs.stdenv.isLinux {
              # Python libraries often load native shared objects using dlopen(3).
              # Setting LD_LIBRARY_PATH makes the dynamic library loader aware of libraries without using RPATH for lookup.
              LD_LIBRARY_PATH = lib.makeLibraryPath pkgs.pythonManylinuxPackages.manylinux1;
            };
          shellHook = ''
            unset PYTHONPATH
          '';
        };

        # This devShell uses uv2nix to construct a virtual environment purely from Nix, using the same dependency specification as the application.
        # The notable difference is that we also apply another overlay here enabling editable mode ( https://setuptools.pypa.io/en/latest/userguide/development_mode.html ).
        #
        # This means that any changes done to your local files do not require a rebuild.
        #
        # Note: Editable package support is still unstable and subject to change.
        uv2nix =
          let
            # Create an overlay enabling editable mode for all local dependencies.
            editableOverlay = workspace.mkEditablePyprojectOverlay {
              # Use environment variable
              root = "$REPO_ROOT";
              # Optional: Only enable editable for these packages
              # members = [ "hello-world" ];
            };

            # Override previous set with our overrideable overlay.
            editablePythonSet = pythonSet.overrideScope (
              lib.composeManyExtensions [
                editableOverlay

                # Apply fixups for building an editable package of your workspace packages
                (final: prev: {
                  audio-guestbook = prev.audio-guestbook.overrideAttrs (old: {
                    # It's a good idea to filter the sources going into an editable build
                    # so the editable package doesn't have to be rebuilt on every change.
                    src = lib.fileset.toSource {
                      root = old.src;
                      fileset = lib.fileset.unions [
                        (old.src + "/pyproject.toml")
                        (old.src + "/README.md")
                        (old.src + "/src/audio_guestbook/__init__.py")
                        (old.src + "/src/audio_guestbook/async_audio_test.py")
                        (old.src + "/src/audio_guestbook/statemachine.py")
                      ];
                    };

                    # Hatchling (our build system) has a dependency on the `editables` package when building editables.
                    #
                    # In normal Python flows this dependency is dynamically handled, and doesn't need to be explicitly declared.
                    # This behaviour is documented in PEP-660.
                    #
                    # With Nix the dependency needs to be explicitly declared.
                    nativeBuildInputs =
                      old.nativeBuildInputs
                      ++ final.resolveBuildSystem {
                        editables = [ ];
                      };
                  });

                })
              ]
            );

            # Build virtual environment, with local packages being editable.
            #
            # Enable all optional dependencies for development.
            virtualenv = editablePythonSet.mkVirtualEnv "audio-guestbook-dev-env" workspace.deps.all;

          in
          pkgs.mkShell {
            packages = with pkgs; [
              virtualenv
              uv
              alsa-utils
              ffmpeg
              mpv
              code-cursor
            ];

            env = {
              # Don't create venv using uv
              UV_NO_SYNC = "1";

              # Force uv to use Python interpreter from venv
              UV_PYTHON = "${virtualenv}/bin/python";

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
      };
    });
}
