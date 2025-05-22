# configuration.nix

{ self, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
  ];


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
  
  };

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
    extraGroups = [ "wheel" "audio" ]; # Enable ‘sudo’ for the user.
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
  ];

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
