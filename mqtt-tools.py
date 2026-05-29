"""
title: MQTT Tools (Chill-Loop / MCP Mitigation)
author: metaurus
version: 1.0
requirements: requests
"""

from pydantic import BaseModel


class Tools:

    class Valves(BaseModel):
        BASE_URL: str = "http://mcp-mitigation:8000"
        MQTT_HOST: str = "mqtt.local"
        MQTT_PORT: int = 1883
        MQTT_USER: str = "chillloop"
        MQTT_PASSWORD: str = ""

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def mqtt_publish(self, topic: str, payload: str, retain: bool = False) -> str:
        """
        Publish a message to an MQTT topic on the Chill-Loop broker.

        Relevant Chill-Loop topics:
          chillloop/audio/{room_id}/metrics      — audio RMS/peak
          chillloop/audio/{room_id}/event        — escalation_candidate
          chillloop/vision/{room_id}/presence    — person count/occupancy
          chillloop/family/{room_id}/state       — fused state (idle/normal/play/escalation_watch/escalation_active/cooldown)
          chillloop/nudge/+                      — nudge actuation events
          chillloop/health/nodes                 — node heartbeats

        :param topic: MQTT topic string (e.g. "chillloop/health/mcp-test").
        :param payload: Message payload as a string.
        :param retain: Whether the broker should retain the message (default: False).
        :return: Confirmation message or error.
        """
        import requests

        try:
            r = requests.post(
                f"{self.valves.BASE_URL}/mqtt/publish",
                json={
                    "host": self.valves.MQTT_HOST,
                    "port": self.valves.MQTT_PORT,
                    "user": self.valves.MQTT_USER,
                    "password": self.valves.MQTT_PASSWORD,
                    "topic": topic,
                    "payload": payload,
                    "retain": retain,
                },
                timeout=15,
            )
            r.raise_for_status()
            return r.json().get("message", "ok")
        except requests.exceptions.ConnectionError:
            return "Error: mcp-mitigation service is unreachable."
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            return f"Error: {detail}"
        except Exception as e:
            return f"Error: {str(e)}"

    def mqtt_read(self, topic: str, timeout: int = 5) -> str:
        """
        Subscribe to an MQTT topic and return the next message received, waiting up to timeout seconds.

        Relevant Chill-Loop topics:
          chillloop/audio/{room_id}/metrics      — audio RMS/peak
          chillloop/audio/{room_id}/event        — escalation_candidate
          chillloop/vision/{room_id}/presence    — person count/occupancy
          chillloop/family/{room_id}/state       — fused state (idle/normal/play/escalation_watch/escalation_active/cooldown)
          chillloop/nudge/+                      — nudge actuation events
          chillloop/health/nodes                 — node heartbeats

        :param topic: MQTT topic to subscribe to (wildcards + and # supported).
        :param timeout: Maximum seconds to wait for a message (default: 5).
        :return: Received message payload, or a timeout/error message.
        """
        import requests

        try:
            r = requests.post(
                f"{self.valves.BASE_URL}/mqtt/read",
                json={
                    "host": self.valves.MQTT_HOST,
                    "port": self.valves.MQTT_PORT,
                    "user": self.valves.MQTT_USER,
                    "password": self.valves.MQTT_PASSWORD,
                    "topic": topic,
                    "timeout": timeout,
                },
                timeout=timeout + 10,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("timed_out"):
                return f"No message received on '{topic}' within {timeout}s."
            return data.get("payload", "")
        except requests.exceptions.ConnectionError:
            return "Error: mcp-mitigation service is unreachable."
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            return f"Error: {detail}"
        except Exception as e:
            return f"Error: {str(e)}"
