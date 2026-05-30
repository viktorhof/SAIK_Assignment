{
  description = "Optional development environment for the SAIK plant management project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };

          pythonEnv = pkgs.python312.withPackages (pythonPackages: with pythonPackages; [
            ipykernel
            jupyterlab
            matplotlib
            numpy
            pandas
            rdflib
            seaborn
          ]);

          texEnv = pkgs.texlive.combine {
            inherit (pkgs.texlive)
              booktabs
              listings
              scheme-small;
          };
        in
        {
          default = pkgs.mkShell {
            packages = [
              pythonEnv
              pkgs.curl
              pkgs.jdk21
              pkgs.sqlite
              pkgs.sqlite-jdbc
              texEnv
              pkgs.unzip
            ];

            shellHook = ''
              export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"

              echo "SAIK_Assignment optional dev shell"
              echo "Python: $(python --version)"
              echo "SQLite JDBC jars: ${pkgs.sqlite-jdbc}/share/java/*.jar"
            '';
          };
        });

      formatter = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        pkgs.nixpkgs-fmt);
    };
}
