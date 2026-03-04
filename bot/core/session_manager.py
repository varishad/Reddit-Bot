"""
Session management utilities for RedditBotEngine.
"""
import atexit
import signal
import sys
class SessionManager:
    """Handle lifecycle tasks such as VPN cleanup and signal handling."""

    def __init__(self, engine: "RedditBotEngine"):
        self.engine = engine
        self._handlers_registered = False

    def register_exit_handlers(self) -> None:
        """Register atexit and signal handlers to ensure VPN cleanup."""
        if self._handlers_registered:
            return

        def cleanup():
            self.cleanup_vpn(reason="exit")

        atexit.register(cleanup)

        def signal_handler(signum, frame):
            self.engine.should_stop = True
            cleanup()
            try:
                sys.exit(0)
            except SystemExit:
                raise

        try:
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except (ValueError, OSError):
            pass

        self._handlers_registered = True

    def cleanup_vpn(self, reason: str = "exit") -> None:
        """Disconnect VPN safely."""
        vpn_manager = getattr(self.engine, "vpn_manager", None)
        if not vpn_manager:
            return

        message = (
            "🚫 Disconnecting ExpressVPN on bot stop..."
            if reason == "stop"
            else "🚫 Disconnecting ExpressVPN on exit..."
        )
        try:
            self.engine.log(message)
            self.engine._run_async(vpn_manager.disconnect())
        except Exception:
            pass

    def stop(self) -> None:
        """Stop the engine and cleanup VPN resources."""
        self.engine.should_stop = True
        self.cleanup_vpn(reason="stop")

