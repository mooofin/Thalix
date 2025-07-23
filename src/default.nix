{ pkgs ? import <nixpkgs> {} }:

let
  python-with-tk = pkgs.python3Full;
in

(python-with-tk.pkgs).buildPythonApplication {
  pname = "affinity-setter-gui";
  version = "1.0";

  src = ./.;

  propagatedBuildInputs = with python-with-tk.pkgs; [
    psutil
    customtkinter
  ];

  format = "other";

  installPhase = ''
    runHook preInstall
    mkdir -p $out/bin
    cp affinity_gui.py $out/affinity_gui.py
    # Corrected wrapper command
    makeWrapper ${python-with-tk}/bin/python $out/bin/affinity-setter-gui \
      --prefix PYTHONPATH : "$pythonPath" \
      --add-flags "$out/affinity_gui.py"
    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "A GUI tool to set CPU affinity for processes";
    license = licenses.mit;
    platforms = platforms.linux;
  };
}
