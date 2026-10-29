"""Application entrypoint for SpellForce Simulator & Optimizer."""

import sys
from sfengine.gui.app import SpellForceSimulatorApp


def main():
    """Initializes and runs the desktop UI."""
    try:
        app = SpellForceSimulatorApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
