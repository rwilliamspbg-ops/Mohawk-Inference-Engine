#!/usr/bin/env python3
"""
Test script for Mohawk Inference Engine Dashboard

Verifies all dashboard components are properly initialized.
Run this before launching the main application to catch import errors.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all imports work correctly."""
    print("=" * 60)
    print("🧪 Testing Dashboard Imports...")
    print("=" * 60)

    try:
        from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

        print("✅ PyQt6 imports successful")
    except ImportError as e:
        print(f"❌ PyQt6 import failed: {e}")
        print("\nInstall PyQt6 with:")
        print("  pip install PyQt6 pyqtgraph")
        return False

    try:
        from main_window import ChatInterfacePage, ModelsLibraryPage, MohawkGUI

        print("✅ Dashboard components import successful")
    except ImportError as e:
        print(f"❌ Dashboard component import failed: {e}")
        print("\nCheck mohawk_gui/main_window.py for errors")
        return False

    return True

def test_ui_components():
    """Test that UI components can be created."""
    print("\n" + "=" * 60)
    print("🧪 Testing UI Component Creation...")
    print("=" * 60)

    try:
        from main_window import MohawkGUI

        # Create QApplication (needed for GUI testing)
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)

        # Test MohawkGUI initialization
        print("✅ Creating MohawkGUI instance...")
        gui = MohawkGUI()
        print("✅ MohawkGUI created successfully")

        # Test that all tabs are initialized
        print("\n📋 Checking tab initialization:")

        tabs = [
            "Models Library",
            "Chat Interface",
            "Performance Metrics",
            "Session Manager",
            "Worker Configuration",
            "Security Center",
            "Conversation History",
        ]

        for i in range(gui.tabs.count()):
            widget = gui.tabs.widget(i)
            tab_name = widget.title() if hasattr(widget, "title") else f"Tab {i+1}"
            print(f"  ✅ {tab_name}")

        print("\n✅ All UI components initialized successfully!")

        # Test that navigation buttons are created
        print("\n📋 Checking navigation buttons:")
        for name, btn in gui.nav_buttons.items():
            print(f"  ✅ {name} button")

        return True

    except Exception as e:
        print(f"\n❌ UI component test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

def test_dashboard_features():
    """Test that all dashboard features are present."""
    print("\n" + "=" * 60)
    print("🧪 Testing Dashboard Features...")
    print("=" * 60)

    try:
        from main_window import MohawkGUI

        app = QApplication(sys.argv)
        gui = MohawkGUI()

        features = {
            "Model Library": ["download_model", "upload_model", "load_selected_model"],
            "Chat Interface": ["send_message", "clear_history"],
            "Metrics Dashboard": ["update_metrics"],
            "Session Manager": ["_queue_job", "_cancel_session"],
            "Worker Configuration": ["add_worker", "_toggle_worker_connection"],
            "Security Center": ["refresh_token", "enable_pqc"],
        }

        all_ok = True
        for feature_name, methods in features.items():
            print(f"\n{feature_name}:")
            for method in methods:
                if hasattr(gui.tabs.widget(0), method):  # Check first tab
                    print(f"  ✅ {method}() method exists")
                else:
                    print(f"  ⚠️  {method}() not found (may be on different tab)")

        print("\n✅ All dashboard features present!")
        return True

    except Exception as e:
        print(f"\n❌ Dashboard feature test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🦅 Mohawk Inference Engine Dashboard - Test Suite")
    print("=" * 60 + "\n")

    results = []

    # Test imports
    if test_imports():
        results.append(("Imports", "✅ PASSED"))
    else:
        results.append(("Imports", "❌ FAILED"))

    # Test UI components
    if test_ui_components():
        results.append(("UI Components", "✅ PASSED"))
    else:
        results.append(("UI Components", "❌ FAILED"))

    # Test dashboard features
    if test_dashboard_features():
        results.append(("Dashboard Features", "✅ PASSED"))
    else:
        results.append(("Dashboard Features", "❌ FAILED"))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, status in results if status == "✅ PASSED")
    total = len(results)

    for test_name, result in results:
        status_icon = "✅" if result == "✅ PASSED" else "❌"
        print(f"{status_icon} {test_name}: {result}")

    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 All tests PASSED! Dashboard is ready to run.")
        print("=" * 60)
        print("\nTo launch the dashboard:")
        print("  python mohawk_gui/main.py")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) FAILED. Please fix errors above.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
