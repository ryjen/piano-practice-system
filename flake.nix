{
  description = "Piano practice system — pinned local development and deterministic checks";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in {
      devShells = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = [ pkgs.python312 ];
            TZDIR = "${pkgs.tzdata}/share/zoneinfo";
            shellHook = ''
              export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"
            '';
          };
        });

      # Preserve the existing stdlib tests and CLI smoke checks; no second test framework.
      checks = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          core = pkgs.runCommand "piano-practice-core-check" {
            nativeBuildInputs = [ pkgs.python312 ];
            TZDIR = "${pkgs.tzdata}/share/zoneinfo";
          } ''
            cp -R ${self} source
            chmod -R u+w source
            cd source
            export HOME="$TMPDIR"
            export PYTHONPATH="$PWD"

            python -m unittest discover -s tests -v
            python -m piano_practice.cli plan --date 2026-11-10 > "$TMPDIR/piano-plan.json"
            python -m piano_practice.cli assess examples/midi-takes/pulse-quarter-pass.json > "$TMPDIR/piano-assessment.json"
            python -c 'import json, os; assert json.load(open(os.environ["TMPDIR"] + "/piano-assessment.json"))["pass"] is True'

            mkdir -p "$out"
            cp "$TMPDIR/piano-plan.json" "$out/plan.json"
            cp "$TMPDIR/piano-assessment.json" "$out/assessment.json"
          '';
        });
    };
}
