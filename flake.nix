{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    python = pkgs.python3.withPackages (ps: with ps; [ requests ]);
  in
  {
    packages.${system} = {
      tmpssh = pkgs.writeShellApplication {
        name = "tmpssh";
        runtimeInputs = [ python pkgs.openssh ];

        text = ''
            python ${./tmpssh.py} "$@"
        '';
      };
    };
  };
}