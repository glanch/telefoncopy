{
  description = "Python 3.12 dev shell with code-cursor (unfree enabled)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, nixpkgs-unstable, flake-utils }:
    {

      images = {
        rpi-4 =
          (self.nixosConfigurations.pi.extendModules {
            modules = [ "${nixpkgs}/nixos/modules/installer/sd-card/sd-image-aarch64.nix" ];
          }).config.system.build.sdImage;
      };
      nixosConfigurations."pi" = nixpkgs.lib.nixosSystem {
        system = "aarch64-linux";
        modules = [
          ./nixos/configuration.nix
        ];
      };
    }
    // flake-utils.lib.eachDefaultSystem (system:
      let
        # Import stable pkgs with unfree allowed
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Import unstable pkgs with unfree allowed
        unstable = import nixpkgs-unstable {
          inherit system;
          config.allowUnfree = true;
        };

        python = pkgs.python312;
        pythonPackages = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          name = "audio-phone-guestbook-dev-shell";

          buildInputs = with pythonPackages; [
            blinker
            cffi
            click
            colorama
            flask
            gevent
            greenlet
            gunicorn
            importlib-metadata
            importlib-resources
            itsdangerous
            jinja2
            markupsafe
            packaging
            psutil
            pycparser
            ruamel-yaml
            ruamel-yaml-clib
            setuptools
            werkzeug
            zipp
            zope-event
            zope-interface
          ] ++ [
            colorzero
            gpiozero
            unstable.code-cursor
            rpi-gpio
            pyyaml
            pulsectl
            pyaudio
            pytest
          ] ++ [
            pkgs.alsa-utils
            pkgs.ffmpeg
          ];

          shellHook = ''
            echo "✅ Audio Phone Guestbook Dev Shell — with code-cursor (unfree enabled)"
          '';
        };
      });
}
