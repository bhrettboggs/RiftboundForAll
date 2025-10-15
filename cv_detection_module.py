import cv2
import numpy as np
import time
from typing import List, Tuple, Dict, Optional

class CardDetector:
    """Advanced card detection and tracking system optimized for speed and stability."""
    
    def __init__(self, camera_index: int = 0):
        self.frame_resize_width = 640
        self.frame_resize_height = 480
        self.max_card_area = 200000
        self.min_card_area = 5000
        self.card_aspect_ratio_range = (0.45, 0.95)
        self.tracking_id = 0
        self.previous_detections = []
        self.tracking_params = {'stability_frames': 5, 'max_movement_threshold': 50}
        self.camera = self._setup_camera(camera_index)
        self.fps_counter = FPSCounter()

    def _setup_camera(self, camera_index):
        camera = cv2.VideoCapture(camera_index)
        if not camera.isOpened():
            print("Failed to open camera")
            return None
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_resize_width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_resize_height)
        camera.set(cv2.CAP_PROP_FPS, 30)
        return camera

    def cleanup(self):
        if self.camera and self.camera.isOpened():
            self.camera.release()
        cv2.destroyAllWindows()

    def capture_frame(self) -> Optional[np.ndarray]:
        if not self.camera or not self.camera.isOpened(): return None
        ret, frame = self.camera.read()
        if not ret: return None
        self.fps_counter.update()
        return frame

    def _preprocess_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        return gray, thresh

    def _find_card_contours(self, thresh_image: np.ndarray) -> List[Dict]:
        contours, _ = cv2.findContours(thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        card_candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_card_area < area < self.max_card_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if self.card_aspect_ratio_range[0] < aspect_ratio < self.card_aspect_ratio_range[1]:
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    if len(approx) >= 4:
                        card_candidates.append({
                            'contour': contour, 'bbox': (x, y, w, h), 'area': area,
                            'center': (x + w // 2, y + h // 2), 'id': -1
                        })
        card_candidates.sort(key=lambda x: x['area'], reverse=True)
        return card_candidates[:10]

    def _get_next_id(self):
        self.tracking_id += 1
        return self.tracking_id

    def _track_cards_between_frames(self, current_detections: List[Dict]) -> List[Dict]:
        tracked_cards = []
        max_dist_sq = self.tracking_params['max_movement_threshold'] ** 2
        previous_map = {d['id']: d for d in self.previous_detections if d.get('id') is not None}
        for current_card in current_detections:
            current_center = np.array(current_card['center'])
            best_match_id, best_distance = None, float('inf')
            for prev_id, prev_card in previous_map.items():
                prev_center = np.array(prev_card['center'])
                distance_sq = np.sum((current_center - prev_center)**2)
                if distance_sq < best_distance and distance_sq < max_dist_sq:
                    best_distance, best_match_id = distance_sq, prev_id
            if best_match_id is not None:
                best_prev = previous_map.pop(best_match_id)
                current_card['id'] = best_prev['id']
                current_card['stable_frames'] = best_prev.get('stable_frames', 0) + 1
            else:
                current_card['id'] = self._get_next_id()
                current_card['stable_frames'] = 1
            tracked_cards.append(current_card)
        self.previous_detections = tracked_cards
        return tracked_cards

    def get_stable_detections(self) -> List[Dict]:
        required_stable = self.tracking_params['stability_frames']
        return [card for card in self.previous_detections if card.get('stable_frames', 0) >= required_stable]

    def detect_cards_in_frame(self, frame: np.ndarray) -> Tuple[List[Dict], Dict]:
        gray, thresh = self._preprocess_frame(frame)
        card_contours = self._find_card_contours(thresh)
        self._track_cards_between_frames(card_contours) # Updates internal state
        stable_cards = self.get_stable_detections()
        debug_info = {'fps': self.fps_counter.get_fps(), 'stable_count': len(stable_cards)}
        return stable_cards, debug_info
    
    def annotate_frame(self, frame: np.ndarray, stable_cards: List[Dict]) -> np.ndarray:
        annotated = frame.copy()
        for card in self.previous_detections:
            x, y, w, h = card['bbox']
            is_stable = any(c['id'] == card['id'] for c in stable_cards)
            color = (0, 255, 0) if is_stable else (0, 165, 255)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            status_text = f"ID:{card['id']} Stable:{card.get('stable_frames', 0)}"
            cv2.putText(annotated, status_text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        fps = self.fps_counter.get_fps()
        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(annotated, f"Stable Cards: {len(stable_cards)}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        return annotated


class CardRegionExtractor:
    """Specialized class for extracting and processing card regions for recognition."""
    def __init__(self):
        self.standard_card_size = (150, 150) # Match CNN input size

    def extract_card_roi(self, frame: np.ndarray, card_info: Dict) -> np.ndarray:
        """Extracts the region of interest for a detected card for the CNN."""
        x, y, w, h = card_info['bbox']
        roi = frame[y:y+h, x:x+w]
        return roi

# Helper class for FPS calculation
class FPSCounter:
    def __init__(self, buffer_size: int = 30):
        self.timestamps = []
        self.buffer_size = buffer_size
    def update(self):
        self.timestamps.append(time.time())
        if len(self.timestamps) > self.buffer_size: self.timestamps.pop(0)
    def get_fps(self) -> float:
        if len(self.timestamps) < 2: return 0.0
        time_diff = self.timestamps[-1] - self.timestamps[0]
        return (len(self.timestamps) - 1) / time_diff if time_diff > 0 else 0.0