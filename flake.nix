{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      tmpssh = pkgs.callPackage ./tmpssh/package.nix { };
      repos = pkgs.callPackage ./repos/package.nix { };
      tmpsshApp = {
        type = "app";
        program = "${tmpssh}/bin/tmpssh";
      };
      reposApp = {
        type = "app";
        program = "${repos}/bin/repos";
      };
    in
    {
      packages.${system} = {
        inherit tmpssh repos;
        default = repos;
      };

      checks.${system} = {
        inherit tmpssh repos;
        default = repos;
      };

      apps.${system} = {
        tmpssh = tmpsshApp;
        repos = reposApp;
        default = reposApp;
      };
    };
}
