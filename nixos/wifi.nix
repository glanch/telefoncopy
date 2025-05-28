{ config, pkgs, lib, ... }:

let
  interface = "wlan0";
  ssid = "MyHotspot";
  password = "MySecretPassword";
in
{
  networking.usePredictableInterfaceNames = false;

  # Enable forwarding packets
  boot.kernel.sysctl = {
    "net.ipv6.conf.all.forwarding" = 1;
    "net.ipv4.conf.all.forwarding" = 1;
  };
  networking.interfaces.wlan0.ipv4.addresses = [
    {
      address = "10.0.64.1";
      prefixLength = 24;
    }
  ];
  # Create an access point
  services.hostapd.enable = true;

  services.hostapd.radios.wlan0 = {
    band = "2g"; # Equivalent to hw_mode=g
    channel = 1;
    countryCode = "DE";

    wifi4.capabilities = [
      "HT20"
      "SHORT-GI-20"
      "DSSS_CCK-40"
    ];

    networks.wlan0 = {
      ssid = "WLANrouter";
      authentication = {
        mode = "wpa2-sha1";
        wpaPassword = "testtest";
      };
    };
  };

  networking.interfaces.end0.useDHCP = false;

  # Updated dnsmasq config using `settings`
  services.dnsmasq = {
    enable = true;
    settings = {
      interface = interface;
      bind-interfaces = true;
      domain-needed = true;
      bogus-priv = true;
      dhcp-range = "10.0.64.10,10.0.64.100,12h";
      dhcp-option = [
        "3,10.0.64.1" # gateway
        "6,10.0.64.1" # DNS
      ];
    };
  };

  # # Enable NAT for internet sharing
  # networking.nat = {
  #   enable = true;
  #   internalInterfaces = [ interface ];
  #   externalInterface = "eth0"; # Adjust to your internet-facing interface
  # };

  # # Allow DNS, DHCP in firewall
  # networking.firewall.allowedUDPPorts = [ 53 67 68 ];
  # networking.firewall.allowedTCPPorts = [ 53 ];

  # # Enable kernel IP forwarding
  # boot.kernel.sysctl."net.ipv4.ip_forward" = true;
}
