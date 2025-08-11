{
  pkgs,
  perSystem,
  ...
}:

let
  inherit (perSystem.self.golem-base-sdk.passthru) virtualenvDev;
in

perSystem.devshell.mkShell {
  packages = [
    virtualenvDev
    pkgs.uv
    pkgs.ruff
  ];

  env = [
    {
      # Don't create venv using uv
      name = "UV_NO_SYNC";
      value = "1";
    }
    {
      # Force uv to use Python interpreter from venv
      name = "UV_PYTHON";
      value = "${virtualenvDev}/bin/python";
    }
    {
      # Prevent uv from downloading managed Python's
      name = "UV_PYTHON_DOWNLOADS";
      value = "never";
    }
  ];

  devshell.startup.uv2nix.text =
    # bash
    ''
      # Undo dependency propagation by nixpkgs.
      unset PYTHONPATH
      # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
      export REPO_ROOT=$(git rev-parse --show-toplevel)
    '';
}
