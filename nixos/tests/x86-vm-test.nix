{ self, pkgs }:

pkgs.nixosTest {
  name = "hello-boots";
  nodes.machine = { config, pkgs, ... }: {
    imports = [
    ];
    system.stateVersion = "23.11";
  };

  testScript = ''
    machine.wait_for_open_port(3000)
  '';
}