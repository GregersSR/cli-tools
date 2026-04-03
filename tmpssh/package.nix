{ pkgs, ... }:
  let
    python = pkgs.python3.withPackages (ps: with ps; [ requests ]);
  in
    pkgs.writeShellApplication {
      name = "tmpssh";
      runtimeInputs = [ pkgs.openssh ];
      text = ''
        exec -a "$0" ${python} ${./tmpssh.py} "$@"
      '';
    }
