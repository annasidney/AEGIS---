"""
AEGIS Outlook Email Reader
Provides safe, read-only access to local Microsoft Outlook emails via MAPI namespace.
"""

import os
from typing import List, Dict, Any, Optional, Union


class OutlookReader:
    """Reads and searches emails from local Microsoft Outlook client using win32com."""

    def __init__(self) -> None:
        self._outlook = None
        self._namespace = None
        self._is_available: Optional[bool] = None

    def is_available(self) -> bool:
        """Checks if Microsoft Outlook is installed, running on Windows, and accessible via COM."""
        if os.name != 'nt':
            return False
        if self._is_available is not None:
            return self._is_available
        try:
            import win32com.client
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            self._namespace = self._outlook.GetNamespace("MAPI")
            self._is_available = True
            return True
        except Exception as e:
            print(f"[OutlookReader Error] Outlook availability check failed: {e}")
            self._is_available = False
            return False

    def _get_inbox(self):
        """Retrieves the default Inbox folder (olFolderInbox = 6) from MAPI namespace."""
        if os.name != 'nt':
            return None, "Outlook integration is only supported on Windows operating systems."

        try:
            import win32com.client
            if not self._outlook or not self._namespace:
                self._outlook = win32com.client.Dispatch("Outlook.Application")
                self._namespace = self._outlook.GetNamespace("MAPI")
            # 6 corresponds to olFolderInbox in Outlook Object Model
            inbox = self._namespace.GetDefaultFolder(6)
            return inbox, None
        except Exception as e:
            print(f"[OutlookReader Error] Failed to connect to Outlook MAPI namespace: {e}")
            return None, f"Microsoft Outlook is not available or not installed on this system ({str(e)})."

    @staticmethod
    def _parse_email_item(item: Any) -> Optional[Dict[str, Any]]:
        """Extracts required fields from an Outlook COM item safely."""
        try:
            subject = str(getattr(item, "Subject", "") or "").strip()
            sender = (
                str(getattr(item, "SenderName", "") or "").strip()
                or str(getattr(item, "SenderEmailAddress", "") or "").strip()
                or "Unknown"
            )
            received_time = getattr(item, "ReceivedTime", None)
            date_str = str(received_time) if received_time is not None else ""

            body = str(getattr(item, "Body", "") or "")
            body_preview = body[:200]

            attachments = getattr(item, "Attachments", None)
            has_attachments = False
            if attachments is not None:
                try:
                    has_attachments = attachments.Count > 0
                except Exception:
                    has_attachments = False

            return {
                "subject": subject,
                "sender": sender,
                "date": date_str,
                "body_preview": body_preview,
                "has_attachments": has_attachments,
            }
        except Exception as e:
            print(f"[OutlookReader Error] Failed to parse email item: {e}")
            return None

    def get_recent_emails(self, count: int = 10) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves recent emails from the Outlook Inbox.

        Args:
            count: Number of recent emails to return (default 10).

        Returns:
            List of email dictionaries containing subject, sender, date, body_preview, has_attachments,
            or an error dictionary if Outlook is unavailable.
        """
        if os.name != 'nt':
            return {
                "error": "Outlook integration is only supported on Windows operating systems.",
                "success": False,
                "emails": []
            }

        inbox, err_msg = self._get_inbox()
        if inbox is None:
            return {
                "error": err_msg or "Microsoft Outlook is not available or not installed.",
                "success": False,
                "emails": []
            }

        try:
            messages = inbox.Items
            try:
                # Sort descending by ReceivedTime (most recent first)
                messages.Sort("[ReceivedTime]", True)
            except Exception as sort_err:
                print(f"[OutlookReader Error] Could not sort messages by ReceivedTime: {sort_err}")

            results: List[Dict[str, Any]] = []
            for item in messages:
                if len(results) >= count:
                    break
                parsed = self._parse_email_item(item)
                if parsed:
                    results.append(parsed)

            return results
        except Exception as e:
            print(f"[OutlookReader Error] Error fetching recent emails: {e}")
            return {
                "error": f"Failed to retrieve emails from Outlook: {str(e)}",
                "success": False,
                "emails": []
            }

    def search_emails(self, query: str, count: int = 10) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Searches emails where subject or body contains the query string.

        Args:
            query: The search term to look for in subject and body.
            count: Maximum number of matching emails to return (default 10).

        Returns:
            List of matching email dictionaries, or an error dictionary if Outlook is unavailable.
        """
        if os.name != 'nt':
            return {
                "error": "Outlook integration is only supported on Windows operating systems.",
                "success": False,
                "emails": []
            }

        if not query or not query.strip():
            return []

        inbox, err_msg = self._get_inbox()
        if inbox is None:
            return {
                "error": err_msg or "Microsoft Outlook is not available or not installed.",
                "success": False,
                "emails": []
            }

        try:
            query_clean = query.strip().lower()
            messages = inbox.Items
            try:
                messages.Sort("[ReceivedTime]", True)
            except Exception as sort_err:
                print(f"[OutlookReader Error] Could not sort messages by ReceivedTime: {sort_err}")

            results: List[Dict[str, Any]] = []
            max_scan = max(100, count * 10)  # Scan up to 100 or 10x count to stay performant
            scanned = 0

            for item in messages:
                if len(results) >= count or scanned >= max_scan:
                    break
                scanned += 1

                try:
                    subject = str(getattr(item, "Subject", "") or "")
                    body = str(getattr(item, "Body", "") or "")

                    if query_clean in subject.lower() or query_clean in body.lower():
                        parsed = self._parse_email_item(item)
                        if parsed:
                            results.append(parsed)
                except Exception as item_err:
                    print(f"[OutlookReader Error] Error reading item during search: {item_err}")
                    continue

            return results
        except Exception as e:
            print(f"[OutlookReader Error] Error searching emails: {e}")
            return {
                "error": f"Failed to search emails in Outlook: {str(e)}",
                "success": False,
                "emails": []
            }


if __name__ == "__main__":
    print("=== Testing OutlookReader Module ===")
    reader = OutlookReader()
    print(f"Is Outlook Available: {reader.is_available()}")

    print("\n--- Testing get_recent_emails(count=3) ---")
    recent = reader.get_recent_emails(count=3)
    print(f"Result: {recent}")

    print("\n--- Testing search_emails('test', count=3) ---")
    search_res = reader.search_emails(query="test", count=3)
    print(f"Result: {search_res}")
    print("\n=== Test Completed ===")
