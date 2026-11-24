"""
AEGIS Visual Clicker & Computer Vision GUI Automation Module
Performs template matching on screen captures using OpenCV and executes precise PyAutoGUI mouse interactions.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

# Graceful dependency handling
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False


class VisualClicker:
    """
    Locates visual UI elements on screen using OpenCV template matching
    and triggers automated mouse interactions via PyAutoGUI.
    """

    def __init__(self):
        """Initializes the VisualClicker and checks dependency availability."""
        if not CV2_AVAILABLE:
            print("[VisualClicker Error] OpenCV (cv2) is not installed. Visual template matching will be unavailable.")
        if not NUMPY_AVAILABLE:
            print("[VisualClicker Error] NumPy is not installed. Array conversions will be unavailable.")
        if not PYAUTOGUI_AVAILABLE:
            print("[VisualClicker Error] PyAutoGUI is not installed. Screen capture and mouse actions will be unavailable.")

    @staticmethod
    def is_available() -> bool:
        """Returns True if all required dependencies (cv2, numpy, pyautogui) are available."""
        return CV2_AVAILABLE and NUMPY_AVAILABLE and PYAUTOGUI_AVAILABLE

    def find_on_screen(self, template_path: Union[str, Path], confidence: float = 0.8,
                       screen_image: Optional[Any] = None) -> Dict[str, Any]:
        """
        Takes a screenshot using pyautogui (or uses provided screen_image), converts it to a NumPy array,
        loads the template image, and uses cv2.matchTemplate with cv2.TM_CCOEFF_NORMED to find the best match.

        Args:
            template_path: Path to the reference image template.
            confidence: Minimum similarity threshold (0.0 to 1.0) required to consider a match found.
            screen_image: Optional pre-captured image (PIL Image or NumPy array) for testing or custom capture.

        Returns:
            Dict containing 'found' (bool), 'x' (int), 'y' (int), 'confidence' (float), and metadata.
        """
        if not self.is_available():
            missing = []
            if not CV2_AVAILABLE: missing.append("opencv-python (cv2)")
            if not NUMPY_AVAILABLE: missing.append("numpy")
            if not PYAUTOGUI_AVAILABLE: missing.append("pyautogui")
            err_msg = f"Missing required dependencies: {', '.join(missing)}."
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "found": False,
                "x": 0,
                "y": 0,
                "confidence": 0.0,
                "error": "DEPENDENCY_ERROR",
                "message": err_msg
            }

        template_str = str(template_path)
        if not os.path.exists(template_str):
            err_msg = f"Template image not found at path: '{template_str}'"
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "found": False,
                "x": 0,
                "y": 0,
                "confidence": 0.0,
                "error": "FILE_NOT_FOUND",
                "message": err_msg
            }

        try:
            # 1. Load template image in 3-channel BGR format
            template = cv2.imread(template_str, cv2.IMREAD_COLOR)
            if template is None:
                err_msg = f"Failed to decode template image at '{template_str}'."
                print(f"[VisualClicker Error] {err_msg}")
                return {
                    "found": False,
                    "x": 0,
                    "y": 0,
                    "confidence": 0.0,
                    "error": "DECODE_ERROR",
                    "message": err_msg
                }

            template_h, template_w = template.shape[:2]

            # 2. Capture screenshot and convert to BGR format for OpenCV
            if screen_image is not None:
                if isinstance(screen_image, np.ndarray):
                    if len(screen_image.shape) == 2:
                        screen_bgr = cv2.cvtColor(screen_image, cv2.COLOR_GRAY2BGR)
                    elif screen_image.shape[2] == 4:
                        screen_bgr = cv2.cvtColor(screen_image, cv2.COLOR_RGBA2BGR)
                    else:
                        screen_bgr = screen_image
                else:
                    screen_np = np.array(screen_image)
                    screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
            else:
                try:
                    screenshot = pyautogui.screenshot()
                    screen_np = np.array(screenshot)
                    screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
                except Exception as ss_err:
                    err_msg = f"Screen capture failed: {str(ss_err)}"
                    print(f"[VisualClicker Error] {err_msg}")
                    return {
                        "found": False,
                        "x": 0,
                        "y": 0,
                        "confidence": 0.0,
                        "error": "SCREENSHOT_FAILED",
                        "message": err_msg
                    }

            screen_h, screen_w = screen_bgr.shape[:2]

            # 3. Check if template exceeds screen dimensions
            if template_w > screen_w or template_h > screen_h:
                err_msg = (f"Template dimensions ({template_w}x{template_h}) exceed screen dimensions "
                           f"({screen_w}x{screen_h}).")
                print(f"[VisualClicker Error] {err_msg}")
                return {
                    "found": False,
                    "x": 0,
                    "y": 0,
                    "confidence": 0.0,
                    "error": "DIMENSION_MISMATCH",
                    "message": err_msg
                }

            # 4. Perform normalized cross-correlation template matching
            match_matrix = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_matrix)

            best_confidence = float(max_val)
            top_left_x, top_left_y = max_loc
            center_x = int(top_left_x + (template_w // 2))
            center_y = int(top_left_y + (template_h // 2))
            is_found = bool(best_confidence >= confidence)

            result: Dict[str, Any] = {
                "found": is_found,
                "x": center_x if is_found else 0,
                "y": center_y if is_found else 0,
                "confidence": round(best_confidence, 4),
                "threshold": confidence,
                "box": {
                    "left": int(top_left_x),
                    "top": int(top_left_y),
                    "width": int(template_w),
                    "height": int(template_h),
                    "right": int(top_left_x + template_w),
                    "bottom": int(top_left_y + template_h)
                } if is_found else None,
                "message": (
                    f"Template match found at ({center_x}, {center_y}) with confidence "
                    f"{round(best_confidence, 4):.4f} (threshold: {confidence})."
                    if is_found else
                    f"Template match not found. Best match confidence was "
                    f"{round(best_confidence, 4):.4f} (threshold: {confidence})."
                )
            }
            return result

        except Exception as e:
            err_msg = f"Visual match exception: {str(e)}"
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "found": False,
                "x": 0,
                "y": 0,
                "confidence": 0.0,
                "error": "EXECUTION_EXCEPTION",
                "message": err_msg
            }

    def find_and_click(self, template_path: Union[str, Path], confidence: float = 0.8,
                       clicks: int = 1, button: str = "left", duration: float = 0.0) -> Dict[str, Any]:
        """
        Finds the template image on screen and clicks at its center coordinates if found.

        Args:
            template_path: Path to the reference image template.
            confidence: Minimum similarity threshold (0.0 to 1.0).
            clicks: Number of clicks to perform (default 1).
            button: Mouse button to click ('left', 'right', 'middle').
            duration: Seconds to animate mouse movement before clicking.

        Returns:
            Dict containing 'success' (bool), 'found' (bool), 'x' (int), 'y' (int), and 'confidence'.
        """
        match_res = self.find_on_screen(template_path=template_path, confidence=confidence)

        if not match_res.get("found"):
            return {
                "success": False,
                "found": False,
                "x": match_res.get("x", 0),
                "y": match_res.get("y", 0),
                "confidence": match_res.get("confidence", 0.0),
                "box": None,
                "message": match_res.get("message", "Target template not found on screen.")
            }

        target_x = match_res["x"]
        target_y = match_res["y"]

        try:
            if not PYAUTOGUI_AVAILABLE:
                raise RuntimeError("PyAutoGUI is not available to execute mouse click.")

            pyautogui.click(x=target_x, y=target_y, clicks=clicks, button=button, duration=duration)

            return {
                "success": True,
                "found": True,
                "x": target_x,
                "y": target_y,
                "clicks": clicks,
                "button": button,
                "confidence": match_res.get("confidence", 0.0),
                "box": match_res.get("box"),
                "message": (
                    f"Successfully clicked target at coordinates ({target_x}, {target_y}) "
                    f"with match confidence {match_res.get('confidence', 0.0):.4f}."
                )
            }
        except Exception as e:
            err_msg = f"Failed to execute click at ({target_x}, {target_y}): {str(e)}"
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "success": False,
                "found": True,
                "x": target_x,
                "y": target_y,
                "confidence": match_res.get("confidence", 0.0),
                "box": match_res.get("box"),
                "message": err_msg
            }

    def highlight_match(self, template_path: Union[str, Path], confidence: float = 0.8,
                        output_path: Optional[Union[str, Path]] = None,
                        box_color: Tuple[int, int, int] = (0, 255, 0),
                        thickness: int = 2,
                        screen_image: Optional[Any] = None) -> Dict[str, Any]:
        """
        Locates the template match on the current screen, draws a highlighted rectangle and center marker
        around the match for visual debugging, and saves the annotated screenshot to disk.

        Args:
            template_path: Path to the reference image template.
            confidence: Minimum similarity threshold (0.0 to 1.0).
            output_path: Optional custom destination file path for annotated image.
            box_color: BGR color tuple for the bounding rectangle (default green: (0, 255, 0)).
            thickness: Line thickness in pixels.
            screen_image: Optional pre-captured image (PIL Image or NumPy array) for testing or custom capture.

        Returns:
            Dict containing match details and 'output_path' of the highlighted image.
        """
        if not self.is_available():
            err_msg = "Highlight match aborted: OpenCV, NumPy, and PyAutoGUI are required."
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "found": False,
                "output_path": None,
                "confidence": 0.0,
                "message": err_msg
            }

        template_str = str(template_path)
        if not os.path.exists(template_str):
            err_msg = f"Template image not found: '{template_str}'"
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "found": False,
                "output_path": None,
                "confidence": 0.0,
                "message": err_msg
            }

        try:
            template = cv2.imread(template_str, cv2.IMREAD_COLOR)
            if template is None:
                err_msg = f"Failed to load template: '{template_str}'"
                print(f"[VisualClicker Error] {err_msg}")
                return {
                    "found": False,
                    "output_path": None,
                    "confidence": 0.0,
                    "message": err_msg
                }

            template_h, template_w = template.shape[:2]

            if screen_image is not None:
                if isinstance(screen_image, np.ndarray):
                    if len(screen_image.shape) == 2:
                        screen_bgr = cv2.cvtColor(screen_image, cv2.COLOR_GRAY2BGR)
                    elif screen_image.shape[2] == 4:
                        screen_bgr = cv2.cvtColor(screen_image, cv2.COLOR_RGBA2BGR)
                    else:
                        screen_bgr = screen_image.copy()
                else:
                    screen_np = np.array(screen_image)
                    screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
            else:
                try:
                    screenshot = pyautogui.screenshot()
                    screen_np = np.array(screenshot)
                    screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
                except Exception as ss_err:
                    err_msg = f"Screen capture failed: {str(ss_err)}"
                    print(f"[VisualClicker Error] {err_msg}")
                    return {
                        "found": False,
                        "output_path": None,
                        "confidence": 0.0,
                        "error": "SCREENSHOT_FAILED",
                        "message": err_msg
                    }

            match_matrix = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_matrix)

            best_confidence = float(max_val)
            top_left = max_loc
            bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
            center_x = int(top_left[0] + (template_w // 2))
            center_y = int(top_left[1] + (template_h // 2))
            is_found = bool(best_confidence >= confidence)

            # Draw bounding box on screenshot image
            rect_color = box_color if is_found else (0, 0, 255) # Green if found, Red if below threshold
            cv2.rectangle(screen_bgr, top_left, bottom_right, rect_color, thickness)
            cv2.circle(screen_bgr, (center_x, center_y), 5, (0, 0, 255), -1)

            label = f"{'MATCH' if is_found else 'LOW_CONF'}: {best_confidence:.3f} (Req: {confidence:.2f})"
            label_y = max(20, top_left[1] - 8)
            cv2.putText(screen_bgr, label, (top_left[0], label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, rect_color, 2, cv2.LINE_AA)

            # Resolve destination output path
            if output_path:
                dest_file = Path(output_path)
            else:
                dest_file = Path(tempfile.gettempdir()) / "aegis_visual_clicker_debug.png"

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(dest_file), screen_bgr)

            return {
                "found": is_found,
                "x": center_x,
                "y": center_y,
                "confidence": round(best_confidence, 4),
                "threshold": confidence,
                "output_path": str(dest_file),
                "box": {
                    "left": top_left[0],
                    "top": top_left[1],
                    "width": template_w,
                    "height": template_h,
                    "right": bottom_right[0],
                    "bottom": bottom_right[1]
                },
                "message": (
                    f"Annotated screenshot saved to '{dest_file}'. "
                    f"Match status: {'Found' if is_found else 'Below threshold'} "
                    f"(Confidence: {best_confidence:.4f}, Target: ({center_x}, {center_y}))."
                )
            }

        except Exception as e:
            err_msg = f"Failed to highlight visual match: {str(e)}"
            print(f"[VisualClicker Error] {err_msg}")
            return {
                "found": False,
                "output_path": None,
                "confidence": 0.0,
                "message": err_msg
            }

    def move_to(self, template_path: Union[str, Path], confidence: float = 0.8,
                duration: float = 0.2) -> Dict[str, Any]:
        """
        Finds the template on screen and moves the mouse cursor to its center without clicking.
        """
        match_res = self.find_on_screen(template_path=template_path, confidence=confidence)
        if not match_res.get("found"):
            return {
                "success": False,
                "found": False,
                "x": match_res.get("x", 0),
                "y": match_res.get("y", 0),
                "confidence": match_res.get("confidence", 0.0),
                "message": match_res.get("message", "Target template not found on screen.")
            }

        target_x = match_res["x"]
        target_y = match_res["y"]
        try:
            if not PYAUTOGUI_AVAILABLE:
                raise RuntimeError("PyAutoGUI is not available.")
            pyautogui.moveTo(x=target_x, y=target_y, duration=duration)
            return {
                "success": True,
                "found": True,
                "x": target_x,
                "y": target_y,
                "confidence": match_res.get("confidence", 0.0),
                "message": f"Cursor moved to ({target_x}, {target_y})."
            }
        except Exception as e:
            err_msg = f"Failed to move cursor: {str(e)}"
            print(f"[VisualClicker Error] {err_msg}")
            return {"success": False, "found": True, "x": target_x, "y": target_y, "message": err_msg}


if __name__ == "__main__":
    print("=== AEGIS VisualClicker Test Suite ===")
    clicker = VisualClicker()
    print(f"Dependencies available: {clicker.is_available()}")

    if clicker.is_available():
        temp_dir = tempfile.gettempdir()
        test_template_path = os.path.join(temp_dir, "aegis_test_template.png")
        test_debug_path = os.path.join(temp_dir, "aegis_test_highlight.png")

        try:
            # 1. Create a synthetic canvas and embedded template
            canvas_w, canvas_h = 800, 600
            canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
            # Fill background with distinct pattern
            canvas[:] = (240, 240, 240)
            cv2.putText(canvas, "AEGIS Visual Test Screen", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (50, 50, 50), 2)

            # Draw synthetic target button at (300, 200) with size 120x40
            button_x, button_y, button_w, button_h = 300, 200, 120, 40
            cv2.rectangle(canvas, (button_x, button_y),
                          (button_x + button_w, button_y + button_h), (0, 128, 255), -1)
            cv2.putText(canvas, "SUBMIT", (button_x + 15, button_y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Extract exact template
            template_crop = canvas[button_y:button_y + button_h, button_x:button_x + button_w]
            cv2.imwrite(test_template_path, template_crop)
            print(f"[Test] Created synthetic template at: {test_template_path}")

            # Test find_on_screen with synthetic screen_image
            find_res = clicker.find_on_screen(test_template_path, confidence=0.85, screen_image=canvas)
            print(f"[Test] find_on_screen result: {find_res}")
            assert find_res["found"] is True, "find_on_screen failed to find matching button!"
            expected_cx = button_x + button_w // 2
            expected_cy = button_y + button_h // 2
            assert find_res["x"] == expected_cx, f"Expected X={expected_cx}, got {find_res['x']}"
            assert find_res["y"] == expected_cy, f"Expected Y={expected_cy}, got {find_res['y']}"
            assert find_res["confidence"] >= 0.95, f"Confidence too low: {find_res['confidence']}"

            # Test highlight_match
            hl_res = clicker.highlight_match(test_template_path, confidence=0.85,
                                            output_path=test_debug_path, screen_image=canvas)
            print(f"[Test] highlight_match result: {hl_res}")
            assert hl_res["found"] is True, "highlight_match failed to find match!"
            assert os.path.exists(test_debug_path), "highlight_match did not generate output file!"

            # Test live screen grab if available in active session
            try:
                screenshot = pyautogui.screenshot()
                screen_test = np.array(screenshot)
                if screen_test.shape[0] > 100 and screen_test.shape[1] > 100:
                    live_template_path = os.path.join(temp_dir, "aegis_live_test.png")
                    live_crop = screen_test[20:70, 20:70]
                    cv2.imwrite(live_template_path, cv2.cvtColor(live_crop, cv2.COLOR_RGB2BGR))
                    live_find = clicker.find_on_screen(live_template_path, confidence=0.8)
                    print(f"[Test] Live screen grab match result: found={live_find['found']}, conf={live_find['confidence']}")
                    if os.path.exists(live_template_path):
                        os.remove(live_template_path)
            except Exception as live_err:
                print(f"[Test Note] Live desktop grab skipped (headless/non-desktop session: {live_err})")

            print("\n[Test] >>> All VisualClicker unit tests PASSED successfully! <<<")

        except Exception as e:
            print(f"[Test Error] Test failed with exception: {e}")
            raise e
        finally:
            if os.path.exists(test_template_path):
                os.remove(test_template_path)
            if os.path.exists(test_debug_path):
                os.remove(test_debug_path)
    else:
        print("[Test] Skipping tests because dependencies are missing.")
