import cv2
import numpy as np
import time
from typing import List, Tuple, Dict, Optional

class CardDetector:
    """Advanced card detection and tracking system optimized for speed and stability."""
    
    def __init__(self, camera_index: int = 0):
        self.frame_resize_width = 640
        self.frame_resize_height = 480
        
        # --- YOUR CUSTOM SETTINGS ---
        self.max_card_area = 120000 
        self.min_card_area = 38663
        self.card_aspect_ratio_range = (0.6, 1.0)
        
        # Your new threshold settings
        self.thresh_block_size = 15
        self.thresh_c = 1
        # --- END OF SETTINGS ---

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
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, self.thresh_block_size, self.thresh_c
        )
        
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
                    
                    if len(approx) == 4:
                        card_candidates.append({
                            'contour': contour, 'bbox': (x, y, w, h), 'area': area,
                            'center': (x + w // 2, y + h // 2), 'id': -1,
                            'approx': approx
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
        
        # --- START OF FIX ---
        # We must return the 'gray' frame so we can flatten it
        debug_info = {
            'fps': self.fps_counter.get_fps(), 
            'stable_count': len(stable_cards),
            'gray_frame': gray  # Add this line
        }
        # --- END OF FIX ---
        
        return stable_cards, debug_info
    
    def annotate_frame(self, frame: np.ndarray, stable_cards: List[Dict]) -> np.ndarray:
        annotated = frame.copy()
        for card in self.previous_detections:
            x, y, w, h = card['bbox']
            is_stable = any(c['id'] == card['id'] for c in stable_cards)
            color = (0, 255, 0) if is_stable else (0, 165, 255)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            # Draw the 4-corner polygon
            cv2.drawContours(annotated, [card['approx']], 0, (255, 0, 0), 2)

            status_text = f"ID:{card['id']} Stable:{card.get('stable_frames', 0)}"
            cv2.putText(annotated, status_text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        fps = self.fps_counter.get_fps()
        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(annotated, f"Stable Cards: {len(stable_cards)}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        return annotated


class CardRegionExtractor:
    """
    Specialized class for extracting and processing card regions for recognition.
    This version includes perspective correction ("flattening").
    """
    def __init__(self):
        # The size of the card after flattening (standard aspect ratio)
        self.flattened_width = 200
        self.flattened_height = 300
        
        # The final size to match the CNN input
        self.cnn_input_size = (150, 150) 
        
        # Destination points for the perspective transform
        self.dst_points = np.array([
            [0, 0],
            [self.flattened_width - 1, 0],
            [self.flattened_width - 1, self.flattened_height - 1],
            [0, self.flattened_height - 1]
        ], dtype="float32")

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Orders 4 points in top-left, top-right, bottom-right, bottom-left order."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] # Top-left
        rect[2] = pts[np.argmax(s)] # Bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] # Top-right
        rect[3] = pts[np.argmax(diff)] # Bottom-left
        return rect

    def _flatten_card(self, frame: np.ndarray, rect_points: np.ndarray) -> np.ndarray:
        """Applies perspective transform to get a flat, top-down view of the card."""
        # --- START OF FIX ---
        # Ensure the frame is 2D (grayscale) before warping
        # This check is a safeguard
        if len(frame.shape) == 3:
             # This shouldn't happen, but if it does, convert it
             frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # --- END OF FIX ---
        
        M = cv2.getPerspectiveTransform(rect_points, self.dst_points)
        warped = cv2.warpPerspective(frame, M, (self.flattened_width, self.flattened_height))
        return warped

    def extract_card_roi(self, frame: np.ndarray, card_info: Dict) -> np.ndarray:
        """
        Extracts the card region from the GRAYSCALE frame, flattens it, 
        and resizes it for the CNN.
        """
        try:
            # 1. Get the 4 corner points ('approx') found by the detector
            corners = card_info['approx']
            pts = corners.reshape(4, 2).astype("float32")
            
            # 2. Order the points
            rect = self._order_points(pts)
            
            # 3. Apply perspective warp to "flatten" the card
            #    'frame' is now the GRAYSCALE frame passed from the main loop
            warped = self._flatten_card(frame, rect)
            
            # 4. Resize the flattened (2D) image to the CNN's exact (2D) input size
            cnn_ready_img = cv2.resize(warped, self.cnn_input_size)
            
            return cnn_ready_img
        except Exception as e:
            print(f"Error flattening card (ID: {card_info.get('id', 'N/A')}): {e}")
            # Return a blank image on failure
            # --- START OF FIX ---
            # Return a 2D blank image to match what cnn_recognition_module expects
            blank_img_shape = (self.cnn_input_size[0], self.cnn_input_size[1])
            blank_img = np.zeros(blank_img_shape, dtype=np.uint8)
            # --- END OF FIX ---
            return blank_img


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