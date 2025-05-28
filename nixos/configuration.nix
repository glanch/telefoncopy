# configuration.nix

{ self, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./wifi.nix
  ];


  systemd.services.my-app =
    let
      # Import your flake and get defaultPackage
      envFile = pkgs.writeText "my-app.env" (builtins.readFile ../pi.env);
    in
    {
      description = "My App from Flake";
      after = [ "network.target" ];
      wantedBy = [ "multi-user.target" ];

      serviceConfig = {
        ExecStart = "${self.packages.aarch64-linux.default}/bin/telephone";
        EnvironmentFile = envFile;
        Restart = "always";
        RestartSec = 0;
        DynamicUser = false;
        User="admin";
        SupplementaryGroups = [ "gpio" "audio" "pulse-access"];
        #StateDirectory = "my-app";  # Creates /var/lib/my-app owned by the dynamic user
        WorkingDirectory = "/home/admin/telephone_state";
      };
    };


  networking.firewall.enable = false;
  # Use the extlinux boot loader. (NixOS wants to enable GRUB by default)
  boot.loader.grub.enable = false;
  # Enables the generation of /boot/extlinux/extlinux.conf
  boot.loader.generic-extlinux-compatible.enable = true;

  users.users.root.password = "root"; # =test use mkpasswd to generate
  # networking config. important for ssh!

  # rtkit is optional but recommended
  security.rtkit.enable = true;
  services.pulseaudio = {
    enable = true;
    systemWide = true;
  };
  # Create gpio group
  users.groups.gpio = { };

  # Change permissions gpio devices
  services.udev.extraRules = ''

    SUBSYSTEM=="input", GROUP="input", MODE="0660"
    SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0660"
    SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"
    SUBSYSTEM=="*gpiomem*", GROUP="gpio", MODE="0660"
    SUBSYSTEM=="rpivid-*", GROUP="video", MODE="0660"

    SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
    SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", RUN+="${pkgs.bash}/bin/bash -c 'chown root:gpio /sys/class/gpio/export /sys/class/gpio/unexport ; chmod 220 /sys/class/gpio/export /sys/class/gpio/unexport'"
    SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add",RUN+="${pkgs.bash}/bin/bash -c 'chown root:gpio /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value ; chmod 660 /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value'"
  '';

  boot.kernelParams = [ "snd_bcm2835.enable_hdmi=1" "snd_bcm2835.enable_headphones=1" ];
  networking = {
    hostName = "pi";
    interfaces.end0 = {
      ipv4.addresses = [{
        address = "10.0.0.5";
        prefixLength = 24;
      }];
    };
  };

  # the user account on the machine
  users.users.admin = {
    isNormalUser = true;
    extraGroups = [ "wheel" "audio" "gpio" "pulse-access"]; # Enable ‘sudo’ for the user.
    password = "admin";
  };

  # Enable the OpenSSH daemon.
  services.openssh.enable = true;

  # I use neovim as my text editor, replace with whatever you like
  environment.systemPackages = with pkgs; [
    neovim
    wget
    self.packages.aarch64-linux.default
    alsa-utils
    ffmpeg
    mpv
    pulseaudio
    sox
    libgpiod
  ];
  boot.kernelPackages = pkgs.linuxPackages_rpi4;

  # allows the use of flakes
  nix.extraOptions = ''
    keep-outputs = true
    keep-derivations = true
    experimental-features = nix-command flakes
  '';

  # this allows you to run `nixos-rebuild --target-host admin@this-machine` from
  # a different host. not used in this tutorial, but handy later.
  nix.settings.trusted-users = [ "admin" ];

  # ergonomics, just in case I need to ssh into
  programs.zsh.enable = true;
  environment.variables = {
    SHELL = "zsh";
    EDITOR = "neovim";
  };
}
