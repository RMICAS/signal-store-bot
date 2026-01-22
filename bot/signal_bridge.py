"""
Signal Bridge - Interface with signal-cli for messaging
"""
import subprocess
import json
import logging
import threading
import time
import os
import sys
import re
from typing import Optional, Callable
from pathlib import Path

try:
    from config.settings import ENABLE_SIGNAL_JSON_RECEIVE
except Exception:
    ENABLE_SIGNAL_JSON_RECEIVE = None

class SignalBridge:
    def __init__(self, bot_phone_number: str, signal_cli_path: str = None, error_callback: Optional[Callable] = None):
        """
        Initialize Signal Bridge
        
        Args:
            bot_phone_number: Bot's Signal phone number (E.164 format, e.g., +1234567890)
            signal_cli_path: Path to signal-cli executable. On macOS this will default to the
                            bundled Unix binary in signal-cli-0.13.22/bin/signal-cli.
        """
        import platform

        self.bot_phone_number = bot_phone_number

        # Prefer explicit path if provided by caller
        if signal_cli_path:
            self.signal_cli_path = signal_cli_path
        else:
            # On macOS, use the bundled Unix signal-cli binary, not the Windows .bat launcher
            if platform.system().lower() == "darwin":
                self.signal_cli_path = "/Users/mutchisigas/Downloads/signal-store-bot/signal-cli-0.13.22/bin/signal-cli"
            else:
                self.signal_cli_path = self._find_signal_cli()
        self.logger = logging.getLogger(__name__)
        self.is_listening = False
        self.listening_thread = None
        self.message_callback: Optional[Callable] = None
        self.daemon_process: Optional[subprocess.Popen] = None
        self.daemon_socket = None
        self.contact_cache = {}  # Cache for contact name/UUID to phone number mapping
        self.receive_supports_json = False
        self.error_callback = error_callback
        
        # Check if signal-cli is available
        if not self._check_signal_cli():
            raise RuntimeError("signal-cli not found. Please install signal-cli first. See scripts/install_signal_cli.sh or install_signal_cli.ps1")
        
        # Detect whether this signal-cli build supports JSON receive output
        if ENABLE_SIGNAL_JSON_RECEIVE is False:
            self.logger.info("Plain-text receive mode forced by config/settings.py; skipping JSON receive probe.")
        else:
            supports_json = self._check_receive_json_support()
            if supports_json:
                self.receive_supports_json = True
            elif ENABLE_SIGNAL_JSON_RECEIVE is True:
                self.logger.warning("signal-cli JSON receive was requested but is unavailable; falling back to plain text parsing.")
    
    def _find_signal_cli(self) -> str:
        """Find signal-cli executable path"""
        import platform
        
        # Try common names
        candidates = ["signal-cli", "signal-cli.exe"]
        
        # Check if signal-cli is in PATH
        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5
                )
                if result.returncode == 0:
                    return candidate
            except:
                continue
        
        # Check local signal-cli directory (from installation script)
        script_dir = Path(__file__).parent.parent
        
        # First, check in root directory for signal-cli-* folders (manual installation)
        for version_dir in script_dir.glob("signal-cli-*"):
            if version_dir.is_dir():
                bin_dir = version_dir / "bin"
                if bin_dir.exists():
                    # Try Windows batch file, .exe, and regular executable
                    for exe_name in ["signal-cli.bat", "signal-cli.exe", "signal-cli"]:
                        exe_path = bin_dir / exe_name
                        if exe_path.exists():
                            return str(exe_path)
        
        # Also check in signal-cli subdirectory (from installation script)
        signal_cli_dir = script_dir / "signal-cli"
        if signal_cli_dir.exists():
            # Look for signal-cli-* directories
            for version_dir in signal_cli_dir.glob("signal-cli-*"):
                bin_dir = version_dir / "bin"
                if bin_dir.exists():
                    # Try Windows batch file, .exe, and regular executable
                    for exe_name in ["signal-cli.bat", "signal-cli.exe", "signal-cli"]:
                        exe_path = bin_dir / exe_name
                        if exe_path.exists():
                            return str(exe_path)
        
        # Fallback: try specific versions in order
        versions = ["0.13.22", "0.12.0", "0.11.6", "0.11.5", "0.11.4"]
        for version in versions:
            local_paths = [
                script_dir / f"signal-cli-{version}" / "bin" / "signal-cli.bat",
                script_dir / f"signal-cli-{version}" / "bin" / "signal-cli.exe",
                script_dir / f"signal-cli-{version}" / "bin" / "signal-cli",
                script_dir / "signal-cli" / f"signal-cli-{version}" / "bin" / "signal-cli.bat",
                script_dir / "signal-cli" / f"signal-cli-{version}" / "bin" / "signal-cli.exe",
                script_dir / "signal-cli" / f"signal-cli-{version}" / "bin" / "signal-cli",
            ]
            for path in local_paths:
                if path.exists():
                    return str(path)
        
        # Default fallback
        return "signal-cli"
    
    def _check_signal_cli(self) -> bool:
        """Check if signal-cli is available"""
        # First check if the file exists
        if not Path(self.signal_cli_path).exists():
            self.logger.error(f"❌ signal-cli not found at: {self.signal_cli_path}")
            return False
        
        # Try to run signal-cli to verify it works
        try:
            result = subprocess.run(
                [self.signal_cli_path, "--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if result.returncode == 0:
                self.logger.info(f"✅ signal-cli found: {result.stdout.strip()}")
                return True
            else:
                # Check if it's a Java version error
                error_output = result.stderr or result.stdout or ""
                if "UnsupportedClassVersionError" in error_output or "class file version" in error_output:
                    self.logger.error(f"❌ signal-cli found but requires Java 21. Current Java version is too old.")
                    self.logger.error(f"   Please upgrade to Java 21 from: https://adoptium.net/")
                    self.logger.error(f"   signal-cli path: {self.signal_cli_path}")
                    # Return True anyway since the file exists - user just needs to upgrade Java
                    return True
                else:
                    self.logger.warning(f"⚠️  signal-cli found but version check failed: {error_output}")
                    return True  # File exists, might work for other operations
        except FileNotFoundError:
            self.logger.error(f"❌ signal-cli not found: {self.signal_cli_path}")
            return False
        except (subprocess.TimeoutExpired, Exception) as e:
            self.logger.warning(f"⚠️  Could not verify signal-cli version: {e}")
            # File exists, so assume it might work
            return True
        return False
    
    def _check_receive_json_support(self) -> bool:
        """Detect if `signal-cli receive` supports the --json flag."""
        """
        Detect whether we can instruct signal-cli to produce JSON by using the
        global `-o json` output flag. Some releases document `receive --json`
        but only the global flag actually works, so we probe by running a
        no-op receive command that exits immediately.
        """
        try:
            probe_cmd = [
                self.signal_cli_path,
                "-o",
                "json",
                "-u",
                self.bot_phone_number,
                "receive",
                "--max-messages",
                "0"
            ]
            result = subprocess.run(
                probe_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5
            )
            if result.returncode == 0:
                self.logger.debug("signal-cli receive supports -o json output")
                return True
            else:
                self.logger.info("signal-cli receive JSON probe failed; using plain text parsing")
                return False
        except Exception as exc:
            self.logger.debug(f"Unable to verify JSON output support for signal-cli receive: {exc}")
            return False
    
    def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a message via Signal (Auto-corrects UUIDs and Phone Numbers)
        """
        try:
            # 1. Strip whitespace and handle accidental "+" on UUIDs
            target = recipient.strip()
            
            # Regex for a standard UUID
            uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
            
            # If it's a UUID (even if it has a + in front), extract just the UUID
            uuid_match = re.search(uuid_pattern, target, re.IGNORECASE)
            
            if uuid_match:
                recipient_to_use = uuid_match.group(0)
                self.logger.info(f"🎯 Target identified as UUID: {recipient_to_use}")
            else:
                # Treat as a phone number
                recipient_to_use = target
                if not recipient_to_use.startswith('+'):
                    recipient_to_use = '+' + recipient_to_use.lstrip('+')
                
                # Basic phone validation
                if len(recipient_to_use) < 8 or not recipient_to_use[1:].isdigit():
                    self.logger.error(f"❌ Invalid recipient format: {recipient}")
                    return False
            
            # 2. Build command
            cmd = [
                self.signal_cli_path,
                "-u", self.bot_phone_number,
                "send",
                recipient_to_use, 
                "-m", message
            ]
            
            self.logger.info(f"📤 Sending to {recipient_to_use}...")
            
            attempts = 3
            for attempt in range(1, attempts + 1):
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    encoding='utf-8', errors='replace', timeout=30
                )
                if result.returncode == 0:
                    self.logger.info(f"✅ Message sent successfully")
                    return True
                self.logger.error(f"❌ Failed to send (attempt {attempt}): {result.stderr or result.stdout}")
                time.sleep(1.5)

            self._report_error("send_failed", {
                "recipient": recipient,
                "message_preview": message[:80]
            })
            return False
                
        except Exception as e:
            self.logger.error(f"❌ Exception in send_message: {e}")
            return False
    
    def receive_messages(self, callback: Callable[[str, str], None]) -> bool:
        """
        Receive messages using signal-cli receive command (polling mode)
        
        Args:
            callback: Function to call with (phone_number, message) when message received
            
        Returns:
            bool: True if receiving started successfully
        """
        self.message_callback = callback
        self.is_listening = True
        
        def receive_loop():
            """Poll for new messages"""
            poll_count = 0
            while self.is_listening:
                try:
                    poll_count += 1
                    # Log every 12 polls (once per minute) to show it's alive
                    if poll_count % 12 == 0:
                        self.logger.info(f"🔄 Still polling for messages... (poll #{poll_count})")
                    
                    # Use receive command (prefer JSON flag when supported)
                    cmd = [self.signal_cli_path]
                    if self.receive_supports_json:
                        cmd.extend(["-o", "json"])
                    cmd.extend([
                        "-u", self.bot_phone_number,
                        "receive"
                    ])
                    
                    self.logger.debug(f"Running signal-cli receive command: {' '.join(cmd[:3])}...")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=10
                    )
                    
                    # Log the result for debugging
                    if result.returncode != 0:
                        # Some signal-cli builds refuse the JSON output flag. If that happens,
                        # immediately disable JSON mode and retry so we can keep parsing messages.
                        if self.receive_supports_json:
                            err_text = (result.stderr or "") + (result.stdout or "")
                            if "-o" in err_text or "json" in err_text:
                                if "unknown option" in err_text.lower() or "unrecognized" in err_text.lower():
                                    self.logger.warning("⚠️  signal-cli rejected the JSON output flag; falling back to plain text parsing.")
                                    self.receive_supports_json = False
                                    time.sleep(1)
                                    continue
                        
                        self.logger.warning(f"⚠️  signal-cli receive returned code {result.returncode}")
                        if result.stderr:
                            self.logger.warning(f"   stderr: {result.stderr[:300]}")
                        if result.stdout:
                            self.logger.warning(f"   stdout: {result.stdout[:300]}")
                    
                    if result.returncode == 0 and result.stdout.strip():
                        # Parse JSON or plain text output from signal-cli
                        self.logger.info(f"📥 Received output from signal-cli (length: {len(result.stdout)}): {result.stdout[:300]}")
                        self._parse_receive_output(result.stdout, is_json=self.receive_supports_json)
                    elif result.stderr and result.stderr.strip():
                        # Log stderr even if returncode is 0 (might contain warnings)
                        error_msg = result.stderr.strip()
                        if "ERROR" in error_msg.upper() or "Exception" in error_msg:
                            self.logger.error(f"❌ signal-cli error: {error_msg[:300]}")
                        else:
                            self.logger.debug(f"signal-cli stderr: {error_msg[:200]}")
                    
                    # Log when polling (even if no messages) - but less frequently
                    if result.returncode == 0 and not result.stdout.strip() and poll_count % 12 == 0:
                        self.logger.debug("Polling for messages... (no new messages)")
                    
                    # Poll every 5 seconds
                    time.sleep(5)
                    
                except subprocess.TimeoutExpired:
                    # Timeout is normal when no messages
                    self.logger.debug("signal-cli receive timed out (normal when no messages)")
                    time.sleep(5)
                except Exception as e:
                    self.logger.error(f"❌ Error in receive loop: {e}", exc_info=True)
                    time.sleep(5)
        
        self.listening_thread = threading.Thread(target=receive_loop, daemon=True)
        self.listening_thread.start()
        self.logger.info("👂 Started listening for Signal messages (polling mode)")
        return True
    
    def _parse_receive_output(self, output: str, is_json: bool = False):
        """Parse JSON or plain text output from signal-cli receive command"""
        try:
            if not output or not output.strip():
                return
            
            # Try JSON format first (easier to parse)
            if is_json:
                try:
                    # JSON output is one JSON object per line
                    parse_failed = False
                    for line in output.strip().split('\n'):
                        if not line.strip():
                            continue
                        try:
                            msg = json.loads(line)
                            self._process_json_message(msg)
                        except json.JSONDecodeError:
                            parse_failed = True
                            self.logger.debug(f"Failed to parse as JSON, trying plain text: {line[:100]}")
                            self._report_error("receive_parse_error", {
                                "mode": "json",
                                "line_preview": line[:120]
                            })
                            continue
                    if parse_failed:
                        self._parse_plain_text_output(output)
                    return
                except Exception as e:
                    self.logger.warning(f"Error parsing JSON output: {e}, falling back to plain text")
                    self._report_error("receive_parse_error", {
                        "mode": "json_exception",
                        "error": str(e)[:200]
                    })
            
            # Parse plain text format
            self._parse_plain_text_output(output)
            
        except Exception as e:
            self.logger.error(f"Error parsing receive output: {e}", exc_info=True)
            self.logger.debug(f"Output was: {output[:200]}")
            self._report_error("receive_parse_error", {
                "mode": "plain_text_exception",
                "error": str(e)[:200]
            })

    def _report_error(self, event_type: str, metadata: dict):
        if not self.error_callback:
            return
        try:
            self.error_callback(event_type, metadata)
        except Exception:
            self.logger.debug("Error callback failed", exc_info=True)
    
    def _process_json_message(self, msg: dict):
        """Process a JSON message from signal-cli"""
        try:
            envelope = msg.get("envelope", {})
            source = envelope.get("source", "")
            source_uuid = envelope.get("sourceUuid", "")
            source_name = envelope.get("sourceName", "")
            data_message = envelope.get("dataMessage", {})
            message_text = data_message.get("message", "").strip()
            
            # Ignore messages from ourselves
            if source == self.bot_phone_number:
                return
            
            # Only process text messages
            if not message_text:
                return
            
            # Use source phone number if available, otherwise try to look it up
            sender_phone = source
            if not sender_phone and source_uuid:
                # Try to get phone from contact list
                sender_phone = self._get_phone_from_contact(source_uuid, source_name, "")
            
            if not sender_phone:
                self.logger.warning(f"⚠️ Could not determine sender phone number for message from {source_name or source_uuid}")
                # Try using UUID as identifier (some systems can work with UUID)
                sender_phone = source_uuid if source_uuid else source
            
            # Call callback
            if self.message_callback and sender_phone:
                self.logger.info(f"📨 Received message from {sender_phone} ({source_name or 'unknown'}): {message_text[:50]}...")
                try:
                    self.message_callback(sender_phone, message_text)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}", exc_info=True)
                    
        except Exception as e:
            self.logger.error(f"Error processing JSON message: {e}", exc_info=True)
    
    def _parse_plain_text_output(self, output: str):
        try:
            # Split by envelope
            message_blocks = re.split(r'\n(?=Envelope from:)', output.strip())
            
            for block in message_blocks:
                if not block.strip():
                    continue
                
                # Skip typing noise
                if "typing message" in block:
                    continue

                self.logger.info(f"🔍 Analyzing Block:\n{block}") # DEBUG LINE
                
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                source = None
                message_text = None
                
                # 1. Get Source (UUID)
                uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', block, re.IGNORECASE)
                source = uuid_match.group(1) if uuid_match else None

                # 2. Get Message Body - Check every possible line
                for i, line in enumerate(lines):
                    if line.startswith('Body:'):
                        message_text = line.replace('Body:', '').strip()
                        break
                    elif "Message timestamp:" in line and i + 1 < len(lines):
                        # Look at the very next line
                        candidate = lines[i+1]
                        if "With profile key" not in candidate and ":" not in candidate:
                            message_text = candidate
                            break
                
                # 3. Process
                if source and message_text:
                    self.logger.info(f"📨 Success! Parsed: {message_text}")
                    self._process_plain_text_message({'source': source}, message_text)
                else:
                    self.logger.warning("⚠️ Source found but Body missing in this block.")
                    
        except Exception as e:
            self.logger.error(f"Error parsing: {e}")
    
    def _process_plain_text_message(self, msg_info: dict, message_text: str):
        """Process a message parsed from plain text output"""
        try:
            source = msg_info.get('source', '')
            if not source:
                # Try to extract from message info
                # If we can't find source, skip
                self.logger.warning("⚠️  No source phone number found in message")
                return
            
            # Log the source for debugging
            self.logger.debug(f"Processing message from source: {source}")
            
            # Ignore messages from ourselves
            if source == self.bot_phone_number:
                self.logger.debug("Ignoring message from bot itself")
                return
            
            # Only process text messages
            if not message_text or not message_text.strip():
                self.logger.debug("Ignoring empty message")
                return
            
            # Call callback
            if self.message_callback:
                self.logger.info(f"📨 Received message from {source}: {message_text[:50]}...")
                try:
                    self.message_callback(source, message_text.strip())
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}", exc_info=True)
            else:
                self.logger.warning("⚠️  No message callback registered")
                    
        except Exception as e:
            self.logger.error(f"Error processing plain text message: {e}", exc_info=True)
    
    def listen_for_messages(self, callback: Callable[[str, str], None]) -> bool:
        """
        Listen for messages using daemon mode (preferred method)
        Falls back to polling mode if daemon mode fails
        
        Args:
            callback: Function to call with (phone_number, message) when message received
            
        Returns:
            bool: True if listening started successfully
        """
        # Try daemon mode first
        if self._start_daemon_mode(callback):
            return True
        
        # Fall back to polling mode
        self.logger.warning("⚠️  Daemon mode failed, falling back to polling mode")
        return self.receive_messages(callback)
    
    def _start_daemon_mode(self, callback: Callable[[str, str], None]) -> bool:
        """
        Start signal-cli in daemon mode with JSON-RPC HTTP for real-time message receiving
        
        Args:
            callback: Function to call when message received
            
        Returns:
            bool: True if daemon started successfully
        """
        try:
            import socket
            # Find an available port for HTTP JSON-RPC
            http_port = self._find_free_port()
            if not http_port:
                self.logger.warning("Could not find free port for HTTP JSON-RPC, using polling mode")
                return False
            
            # Start daemon with JSON-RPC HTTP mode
            self.daemon_process = subprocess.Popen(
                [
                    self.signal_cli_path,
                    "-u", self.bot_phone_number,
                    "daemon",
                    "--http",
                    f"127.0.0.1:{http_port}"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            self.message_callback = callback
            self.is_listening = True
            self.http_port = http_port
            
            # Start thread to poll HTTP endpoint for messages
            def poll_http_messages():
                """Poll HTTP endpoint for new messages"""
                import urllib.request
                import json as json_lib
                import time
                
                # Give daemon time to start
                time.sleep(3)
                
                while self.is_listening:
                    try:
                        # Note: signal-cli HTTP mode requires subscribing to receive messages
                        # For now, we'll use polling mode which is simpler
                        # HTTP mode requires more complex setup with subscriptions
                        time.sleep(5)
                    except Exception as e:
                        self.logger.error(f"Error in HTTP polling: {e}")
                        time.sleep(5)
            
            # For now, HTTP mode is complex, so fall back to polling
            self.logger.info("HTTP JSON-RPC mode requires subscription setup, using polling mode instead")
            if self.daemon_process:
                self.daemon_process.terminate()
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error starting daemon mode: {e}")
            return False
    
    def _find_free_port(self, start_port=8080, max_port=8090):
        """Find a free port for HTTP server"""
        import socket
        for port in range(start_port, max_port + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return None
    
    def _get_phone_from_contact(self, uuid: Optional[str] = None, name: Optional[str] = None, envelope_line: str = "") -> Optional[str]:
        """Try to get phone number from contact list using UUID or name"""
        try:
            # If we have a cached mapping, use it
            if uuid and uuid in self.contact_cache:
                return self.contact_cache[uuid]
            if name and name in self.contact_cache:
                return self.contact_cache[name]
            
            # Try to query signal-cli for contact information
            if uuid:
                try:
                    # Try to get contact info using listContacts
                    cmd = [
                        self.signal_cli_path,
                        "-u", self.bot_phone_number,
                        "listContacts"
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout:
                        # Parse contact list (format: Name: +phone or JSON)
                        import re
                        # Look for the UUID in the output and extract associated phone
                        # This is a simplified approach - signal-cli contact format varies
                        for line in result.stdout.split('\n'):
                            if uuid.lower() in line.lower():
                                phone_matches = re.findall(r'(\+[\d]{7,15})', line)
                                if phone_matches:
                                    phone = phone_matches[0]
                                    if phone != self.bot_phone_number:
                                        self.contact_cache[uuid] = phone
                                        return phone
                except Exception as e:
                    self.logger.debug(f"Error querying contacts: {e}")
            
            # Fallback: Try to extract from envelope line
            if envelope_line:
                phone_matches = re.findall(r'(\+[\d]{7,15})', envelope_line)
                for phone in phone_matches:
                    if phone != self.bot_phone_number:
                        # Cache it
                        if uuid:
                            self.contact_cache[uuid] = phone
                        if name:
                            self.contact_cache[name] = phone
                        return phone
            
            return None
        except Exception as e:
            self.logger.debug(f"Error getting phone from contact: {e}")
            return None
    
    def _process_received_message(self, msg: dict):
        """
        Process a received message from signal-cli
        
        Args:
            msg: JSON message object from signal-cli
        """
        try:
            # Extract message data
            envelope = msg.get("envelope", {})
            source = envelope.get("source", "")
            data_message = envelope.get("dataMessage", {})
            message_text = data_message.get("message", "").strip()
            timestamp = envelope.get("timestamp", 0)
            
            # Ignore messages from ourselves
            if source == self.bot_phone_number:
                return
            
            # Only process text messages
            if not message_text:
                return
            
            # Call callback
            if self.message_callback:
                self.logger.info(f"📨 Received message from {source}: {message_text[:50]}...")
                try:
                    self.message_callback(source, message_text)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.is_listening = False
        
        # Stop daemon if running
        if self.daemon_process:
            try:
                self.daemon_process.terminate()
                self.daemon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping daemon: {e}")
            finally:
                self.daemon_process = None
        
        # Wait for listening thread to finish
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=5)
        
        self.logger.info("🛑 Stopped listening for Signal messages")
    
    def test_connection(self) -> bool:
        """
        Test Signal connection by checking account status
        """
        try:
            # Check status of the bot's own number
            result = subprocess.run(
                [self.signal_cli_path, "-u", self.bot_phone_number, "getUserStatus", self.bot_phone_number],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15
            )
            
            # If the command succeeds, we are registered and connected
            if result.returncode == 0:
                self.logger.info("✅ Signal connection test successful")
                return True
            else:
                self.logger.warning(f"⚠️ Signal connection test failed: {result.stderr.strip()}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Error testing Signal connection: {e}")
            return False

