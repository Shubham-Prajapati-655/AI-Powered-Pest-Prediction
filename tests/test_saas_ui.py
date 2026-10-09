import unittest
import os
import sys
import time
from streamlit.testing.v1 import AppTest

# Add project root and app directory to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "app"))

APP_FILE = os.path.join(ROOT_DIR, "app", "app.py")

class TestAgriAIAdvisorUI(unittest.TestCase):
    """
    Automated UI tests verifying AgriAI Advisor v2.1.0 frontend views,
    state management, page switching, and error-free rendering.
    """

    def setUp(self):
        try:
            import streamlit as st
            st._main_dg._form_data = None
            if hasattr(st, "sidebar"):
                st.sidebar._form_data = None
                if getattr(st.sidebar, "_parent", None):
                    st.sidebar._parent._form_data = None
            from streamlit.elements.lib.form_utils import context_dg_stack
            from streamlit.delta_generator import DeltaGenerator
            context_dg_stack.set((DeltaGenerator(),))
        except Exception:
            pass

    def tearDown(self):
        try:
            import streamlit as st
            st._main_dg._form_data = None
            if hasattr(st, "sidebar"):
                st.sidebar._form_data = None
                if getattr(st.sidebar, "_parent", None):
                    st.sidebar._parent._form_data = None
            from streamlit.elements.lib.form_utils import context_dg_stack
            from streamlit.delta_generator import DeltaGenerator
            context_dg_stack.set((DeltaGenerator(),))
        except Exception:
            pass

    def test_unauthenticated_landing(self):
        """Verify unauthenticated user lands on Auth Gateway with proper brand text."""
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        # Verify brand title or auth presence
        html_content = "".join([m.value for m in at.markdown])
        self.assertIn("AgriAI Advisor", html_content)
        self.assertIn("v2.1.0", html_content)

    def test_authenticated_dashboard(self):
        """Verify authenticated user views Dashboard with Hero, metrics, and workflow."""
        user = {
            "id": 1,
            "name": "Test Farmer",
            "email": "farmer@agriai.org",
            "role": "farmer",
            "state": "Maharashtra",
            "district": "Pune",
            "preferred_crop": "Cotton"
        }
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.session_state["authenticated"] = True
        at.session_state["user"] = user
        at.session_state["login_timestamp"] = time.time()
        at.session_state["current_page"] = "🏠 Dashboard"
        at.run()
        self.assertFalse(at.exception)
        html_content = "".join([m.value for m in at.markdown])
        self.assertIn("AgriAI Advisor", html_content)
        self.assertIn("AI-Powered Crop Pest Prediction &amp; Advisory Platform", html_content)
        self.assertIn("Core Capabilities", html_content)

    def test_about_page(self):
        """Verify About page renders company mission, feature pillars, and benefits."""
        user = {
            "id": 1,
            "name": "Test Farmer",
            "email": "farmer@agriai.org",
            "role": "farmer"
        }
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.session_state["authenticated"] = True
        at.session_state["user"] = user
        at.session_state["login_timestamp"] = time.time()
        at.session_state["current_page"] = "ℹ️ About"
        at.run()
        self.assertFalse(at.exception)
        html_content = "".join([m.value for m in at.markdown])
        self.assertIn("About", html_content)
        self.assertIn("Why Choose Our Platform", html_content)

    def test_contact_page(self):
        """Verify Contact page renders SLA and contact details."""
        user = {
            "id": 1,
            "name": "Test Farmer",
            "email": "farmer@agriai.org",
            "role": "farmer"
        }
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.session_state["authenticated"] = True
        at.session_state["user"] = user
        at.session_state["login_timestamp"] = time.time()
        at.session_state["current_page"] = "📩 Contact"
        at.run()
        self.assertFalse(at.exception)
        html_content = "".join([m.value for m in at.markdown])
        self.assertIn("Contact Support", html_content)
        self.assertIn("support@agriai.org", html_content)

    def test_history_page(self):
        """Verify History page renders archival search and filters."""
        user = {
            "id": 1,
            "name": "Test Farmer",
            "email": "farmer@agriai.org",
            "role": "farmer"
        }
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.session_state["authenticated"] = True
        at.session_state["user"] = user
        at.session_state["login_timestamp"] = time.time()
        at.session_state["current_page"] = "📜 History"
        at.run()
        self.assertFalse(at.exception)

    def test_admin_portal_access(self):
        """Verify Admin user can access Enterprise Admin Portal."""
        admin = {
            "id": 2,
            "name": "System Administrator",
            "email": "admin@agriai.org",
            "role": "admin"
        }
        at = AppTest.from_file(APP_FILE, default_timeout=80)
        at.session_state["authenticated"] = True
        at.session_state["user"] = admin
        at.session_state["login_timestamp"] = time.time()
        at.session_state["current_page"] = "🛡️ Admin Portal"
        at.run()
        self.assertFalse(at.exception)
        html_content = "".join([m.value for m in at.markdown])
        self.assertIn("Enterprise Operations Center", html_content)

    def test_sidebar_logout_flow(self):
        """Verify 1-click sidebar logout completely wipes session, auth state, and redirects to Login."""
        user = {
            "id": 1,
            "name": "Test Farmer",
            "email": "farmer@agriai.org",
            "role": "farmer"
        }
        at = AppTest.from_file(APP_FILE, default_timeout=30)
        at.session_state["authenticated"] = True
        at.session_state["user"] = user
        at.session_state["login_timestamp"] = time.time()
        at.session_state["current_page"] = "🏠 Dashboard"
        at.session_state["active_prediction"] = {"crop": "Cotton", "predicted_pest": "Pink Bollworm"}
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state["authenticated"])

        # Click the 1-click sidebar logout button
        logout_btn = [b for b in at.button if b.key == "btn_sidebar_logout"][0]
        logout_btn.click()
        at.run()

        # Verify full session purge
        self.assertFalse(at.exception)
        self.assertFalse(at.session_state["authenticated"])
        self.assertIsNone(at.session_state["user"])
        self.assertNotIn("active_prediction", at.session_state)
        
        # Verify Login Gateway rendered, dashboard not visible
        html_content = "".join([m.value for m in at.markdown])
        self.assertIn("AgriAI Platform", html_content)
        self.assertNotIn("Recent Field Predictions", html_content)

    @classmethod
    def tearDownClass(cls):
        if "app" in sys.modules and not hasattr(sys.modules["app"], "__path__"):
            del sys.modules["app"]


if __name__ == "__main__":
    unittest.main()
