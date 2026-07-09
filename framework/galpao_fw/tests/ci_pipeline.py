"""Quick build verification used by the CI script. Calls both pipeline and build."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest

sys.exit(pytest.main([os.path.dirname(__file__), "-v", "--tb=short",
                       "-m", "not build"]))
