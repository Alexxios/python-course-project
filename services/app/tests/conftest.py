"""Hypothesis profiles shared by the app's unit and integration suites."""

import os

from hypothesis import settings

settings.register_profile("app", max_examples=30, deadline=None, print_blob=True)
settings.register_profile("fuzz", parent=settings.get_profile("app"), max_examples=1000)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "app"))
