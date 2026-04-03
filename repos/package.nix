{ lib, stdenv, makeWrapper, git, python3 }:

stdenv.mkDerivation {
  pname = "repos";
  version = "0.1.0";

  src = ./.;
  dontBuild = true;

  nativeBuildInputs = [ makeWrapper python3 git ];

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/bin" "$out/libexec/repos"
    install -m755 repos "$out/libexec/repos/repos"
    cp -r template "$out/libexec/repos/template"

    makeWrapper ${python3}/bin/python3 "$out/bin/repos" \
      --add-flags "$out/libexec/repos/repos" \
      --prefix PATH : ${lib.makeBinPath [ git ]}

    runHook postInstall
  '';

  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    PATH=${lib.makeBinPath [ git ]}:$PATH \
      REPOS_SCRIPT="$out/libexec/repos/repos" \
      ${python3}/bin/python3 -m unittest -v test_repos
    runHook postInstallCheck
  '';

  meta = with lib; {
    description = "Small CLI for scaffolding and checking git repositories";
    mainProgram = "repos";
    platforms = platforms.unix;
  };
}
