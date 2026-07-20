import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SetupScriptTests(unittest.TestCase):
    def test_paddle_install_keeps_numpy_compatible_with_paddlex(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        setup_script = (ROOT / "setup.ps1").read_text(encoding="utf-8")

        self.assertIn("numpy>=1.24,<2.4", requirements)
        self.assertIn('$numpyRequirement = "numpy>=1.24,<2.4"', setup_script)
        self.assertIn("-Arguments @($numpyRequirement)", setup_script)

    def test_install_and_check_modes_verify_dependency_consistency(self):
        setup_script = (ROOT / "setup.ps1").read_text(encoding="utf-8")

        self.assertIn("function Test-PythonDependencies", setup_script)
        self.assertEqual(
            setup_script.count("Test-PythonDependencies -VenvPy $venvPy"),
            2,
        )
        self.assertIn("& $VenvPy -m pip check", setup_script)

    def test_pip_install_retries_without_a_broken_cache(self):
        setup_script = (ROOT / "setup.ps1").read_text(encoding="utf-8")

        self.assertIn("function Install-PipWithRetry", setup_script)
        self.assertIn("-m pip install --no-cache-dir @Arguments", setup_script)
        self.assertIn('Arguments @("-r", (Join-Path $Root "requirements.txt"))', setup_script)

    def test_default_install_builds_launcher_when_it_is_missing(self):
        setup_script = (ROOT / "setup.ps1").read_text(encoding="utf-8")

        self.assertIn('$launcherExe = Join-Path $Root "翻译.exe"', setup_script)
        self.assertIn(
            "if ($BuildLauncher -or -not (Test-Path -LiteralPath $launcherExe))",
            setup_script,
        )
        self.assertIn("Invoke-BuildLauncher -VenvPy $venvPy", setup_script)
        self.assertIn('-Arguments @("pyinstaller")', setup_script)
        self.assertIn("翻译.exe 生成结束后仍未找到", setup_script)


if __name__ == "__main__":
    unittest.main()
