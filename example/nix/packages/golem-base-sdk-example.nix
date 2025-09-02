{
  pkgs,
  inputs,
  ...
}:

let
  inherit (pkgs) lib;

  # We need an actual path here, because of the editable install used below
  src = ../..;

  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = src;
  };

  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };

  pythonSet =
    (pkgs.callPackage inputs.pyproject-nix.build.packages {
      python = pkgs.python310;
    }).overrideScope
      (
        lib.composeManyExtensions [
          inputs.pyproject-build-systems.overlays.default
          overlay
        ]
      );

  inherit (pkgs.callPackages inputs.pyproject-nix.build.util { }) mkApplication;

  editableOverlay = workspace.mkEditablePyprojectOverlay {
    # This env var needs to be set to the root of the repo in the shell that runs the
    # application, otherwise python will not import golem_base_sdk from the right place
    root = "$REPO_ROOT/example";
    # Only enable editable for this package
    members = [ "golem-base-sdk" ];
  };

  editablePythonSet = pythonSet.overrideScope (
    lib.composeManyExtensions [
      editableOverlay

      # Apply fixups for building an editable package of your workspace packages
      (final: prev: {
        golem-base-sdk = prev.golem-base-sdk.overrideAttrs (old: {
          # We need the editables build system added here
          nativeBuildInputs =
            old.nativeBuildInputs
            ++ final.resolveBuildSystem {
              editables = [ ];
            };
        });
      })
    ]
  );

  virtualenv = editablePythonSet.mkVirtualEnv "golem-base-sdk-example-env" workspace.deps.default;
  virtualenvDev = editablePythonSet.mkVirtualEnv "golem-base-sdk-example-env" workspace.deps.all;
in

mkApplication {
  venv = virtualenv;
  package = pythonSet.golem-base-sdk-example.overrideAttrs (prevAttrs: {
    nativeCheckInputs = [
      pkgs.mypy
      pkgs.ruff
    ];

    doCheck = true;

    checkPhase = ''
      mypy golem_base_sdk_example
      ruff check --no-cache golem_base_sdk_example
    '';

    passthru = (prevAttrs.passthru or { }) // {
      inherit virtualenv virtualenvDev;
    };
  });
}
