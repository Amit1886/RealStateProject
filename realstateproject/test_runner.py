import importlib.util
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test.runner import DiscoverRunner


class AppOnlyDiscoverRunner(DiscoverRunner):
    """
    Avoid discovering "test_*.py" scripts at the project root.

    The repo contains many ad-hoc `test_*.py` scripts that execute at import time and
    are not part of the Django test suite. This runner defaults to installed apps.
    """

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        # Django passes ['.'] when no labels are provided; treat that as "no labels".
        if not test_labels or test_labels == ["."]:
            # Use dotted test modules so unittest doesn't treat app dirs as start_dir paths
            # (which would import app-level tests as top-level "tests" and collide).
            labels = []
            base_dir = Path(getattr(settings, "BASE_DIR", ".")).resolve()
            for app in apps.get_app_configs():
                # Skip third-party and Django contrib tests (site-packages) to keep the suite focused.
                try:
                    app_path = Path(app.path).resolve()
                except Exception:
                    continue
                if "site-packages" in {p.lower() for p in app_path.parts}:
                    continue
                if not (app_path == base_dir or base_dir in app_path.parents):
                    continue

                test_module = f"{app.name}.tests"
                if importlib.util.find_spec(test_module) is not None:
                    labels.append(test_module)
            test_labels = labels
        return super().build_suite(test_labels, extra_tests=extra_tests, **kwargs)
