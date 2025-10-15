"""
Improved Card Detection System
Based on research of successful OpenCV playing card detectors
Key improvements:
- Perspective correction for angled cards
- Proper corner extraction with rank/suit isolation
- Template-based matching with difference scoring
- Better preprocessing and filtering
"""

import cv2
import numpy as np
import os
from typing import List, Tuple, Optional, Dict

class ImprovedCardDetector:
    """Enhanced card detection with perspective correction and template matching"""

    # Detection constants
    BKG_THRESH = 60
    CARD_THRESH = 30

    # Card dimensions after perspective correction
    CARD_WIDTH = 200
    CARD_HEIGHT = 300

    # Corner region dimensions (where rank and suit are located)
    CORNER_WIDTH = 32
    CORNER_HEIGHT = 84

    # Template dimensions
    RANK_WIDTH = 70
    RANK_HEIGHT = 125
    SUIT_WIDTH = 70
    SUIT_HEIGHT = 100

    # Area thresholds for card detection
    CARD_MAX_AREA = 120000
    CARD_MIN_AREA = 25000

    # Matching thresholds
    RANK_DIFF_MAX = 2000
    SUIT_DIFF_MAX = 700

    def __init__(self, templates_dir='card_templates'):
        self.templates_dir = templates_dir
        self.rank_templates = {}
        self.suit_templates = {}
        self.load_templates()

    def load_templates(self):
        """Load rank and suit templates from directory"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            print(f"Created templates directory: {self.templates_dir}")
            return

        # Load rank templates
        rank_dir = os.path.join(self.templates_dir, 'ranks')
        if os.path.exists(rank_dir):
            for filename in os.listdir(rank_dir):
                if filename.endswith('.jpg') or filename.endswith('.png'):
                    rank_name = filename.split('.')[0]
                    template = cv2.imread(os.path.join(rank_dir, filename), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self.rank_templates[rank_name] = template

        # Load suit templates
        suit_dir = os.path.join(self.templates_dir, 'suits')
        if os.path.exists(suit_dir):
            for filename in os.listdir(suit_dir):
                if filename.endswith('.jpg') or filename.endswith('.png'):
                    suit_name = filename.split('.')[0]
                    template = cv2.imread(os.path.join(suit_dir, filename), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self.suit_templates[suit_name] = template

        print(f"Loaded {len(self.rank_templates)} rank templates and {len(self.suit_templates)} suit templates")

    def preprocess_image(self, frame):
        """
        Preprocess image for card detection
        Returns: grayscale and thresholded images
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive threshold for better edge detection under varying lighting
        # This handles different backgrounds better than fixed threshold
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 1
        )

        return gray, thresh

    def find_cards(self, thresh_image):
        """
        Find all card contours in the thresholded image
        Returns: list of valid card contours with metadata
        """
        # Find contours
        contours, hierarchy = cv2.findContours(
            thresh_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        # Sort contours by area (largest first)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        card_contours = []

        # Find cards by filtering contours
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            # Filter by area
            if self.CARD_MIN_AREA < area < self.CARD_MAX_AREA:
                # Approximate to polygon
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.01 * peri, True)

                # Cards should have 4 corners
                if len(approx) == 4:
                    # Get bounding rect
                    x, y, w, h = cv2.boundingRect(contour)

                    # Check aspect ratio (cards are rectangular)
                    aspect_ratio = float(w) / h

                    # Cards typically have aspect ratio between 0.5 and 0.9
                    if 0.4 < aspect_ratio < 1.0:
                        card_contours.append({
                            'contour': contour,
                            'approx': approx,
                            'area': area,
                            'bbox': (x, y, w, h),
                            'aspect_ratio': aspect_ratio
                        })

        return card_contours

    def order_points(self, pts):
        """
        Order points in consistent order: top-left, top-right, bottom-right, bottom-left
        This is CRITICAL for proper perspective transformation
        """
        rect = np.zeros((4, 2), dtype="float32")

        # Top-left point has smallest sum, bottom-right has largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Top-right has smallest difference, bottom-left has largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    def flatten_card(self, image, corners):
        """
        Apply perspective transform to get flat, top-down view of card
        This is the KEY to handling angled/tilted cards
        """
        # Order the corner points consistently
        pts = corners.reshape(4, 2)
        rect = self.order_points(pts)

        # Destination points for flattened card (standard card size)
        dst = np.array([
            [0, 0],
            [self.CARD_WIDTH - 1, 0],
            [self.CARD_WIDTH - 1, self.CARD_HEIGHT - 1],
            [0, self.CARD_HEIGHT - 1]
        ], dtype="float32")

        # Calculate perspective transform matrix
        M = cv2.getPerspectiveTransform(rect, dst)

        # Warp the image
        warped = cv2.warpPerspective(image, M, (self.CARD_WIDTH, self.CARD_HEIGHT))

        return warped

    def extract_and_process_corner(self, card_image):
        """
        Extract corner region from card and prepare for recognition
        Returns: rank image, suit image
        """
        # Extract top-left corner (where rank and suit are)
        corner = card_image[0:self.CORNER_HEIGHT, 0:self.CORNER_WIDTH]

        # Zoom in 4x for better detail (IMPORTANT for small text/symbols)
        corner_zoom = cv2.resize(corner, (0, 0), fx=4, fy=4)

        # Blur to reduce noise
        corner_blur = cv2.GaussianBlur(corner_zoom, (5, 5), 0)

        # Sample white level from center of corner to adapt threshold
        white_level = corner_zoom[15, int((self.CORNER_WIDTH * 4) / 2)]
        thresh_level = white_level - self.CARD_THRESH
        if thresh_level <= 0:
            thresh_level = 1

        # Threshold the corner
        _, corner_thresh = cv2.threshold(
            corner_blur, thresh_level, 255, cv2.THRESH_BINARY_INV
        )

        # Split corner into rank (top) and suit (bottom)
        # Rank is in top portion
        rank_img = corner_thresh[20:185, 0:128]

        # Suit is in bottom portion
        suit_img = corner_thresh[186:336, 0:128]

        return rank_img, suit_img

    def isolate_rank_and_suit(self, rank_img, suit_img):
        """
        Isolate the actual rank and suit from their regions
        Returns: isolated rank, isolated suit (properly sized)
        """
        # Find and isolate rank contour
        rank_cnts, _ = cv2.findContours(
            rank_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if rank_cnts:
            # Get largest contour (the rank)
            rank_cnts = sorted(rank_cnts, key=cv2.contourArea, reverse=True)
            x, y, w, h = cv2.boundingRect(rank_cnts[0])
            rank_roi = rank_img[y:y+h, x:x+w]

            # Resize to standard size for template matching
            rank_sized = cv2.resize(rank_roi, (self.RANK_WIDTH, self.RANK_HEIGHT))
        else:
            rank_sized = np.zeros((self.RANK_HEIGHT, self.RANK_WIDTH), dtype=np.uint8)

        # Find and isolate suit contour
        suit_cnts, _ = cv2.findContours(
            suit_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if suit_cnts:
            # Get largest contour (the suit)
            suit_cnts = sorted(suit_cnts, key=cv2.contourArea, reverse=True)
            x, y, w, h = cv2.boundingRect(suit_cnts[0])
            suit_roi = suit_img[y:y+h, x:x+w]

            # Resize to standard size for template matching
            suit_sized = cv2.resize(suit_roi, (self.SUIT_WIDTH, self.SUIT_HEIGHT))
        else:
            suit_sized = np.zeros((self.SUIT_HEIGHT, self.SUIT_WIDTH), dtype=np.uint8)

        return rank_sized, suit_sized

    def match_rank(self, rank_img):
        """
        Match rank image against templates using difference method
        Returns: best_match name, difference score
        """
        if not self.rank_templates:
            return "Unknown", float('inf')

        best_match = "Unknown"
        best_diff = float('inf')

        for rank_name, template in self.rank_templates.items():
            # Calculate difference (sum of absolute pixel differences)
            diff = cv2.absdiff(rank_img, template)
            rank_diff = int(np.sum(diff) / 255)

            if rank_diff < best_diff:
                best_diff = rank_diff
                best_match = rank_name

        # Only return match if difference is below threshold
        if best_diff < self.RANK_DIFF_MAX:
            return best_match, best_diff
        else:
            return "Unknown", best_diff

    def match_suit(self, suit_img):
        """
        Match suit image against templates using difference method
        Returns: best_match name, difference score
        """
        if not self.suit_templates:
            return "Unknown", float('inf')

        best_match = "Unknown"
        best_diff = float('inf')

        for suit_name, template in self.suit_templates.items():
            # Calculate difference
            diff = cv2.absdiff(suit_img, template)
            suit_diff = int(np.sum(diff) / 255)

            if suit_diff < best_diff:
                best_diff = suit_diff
                best_match = suit_name

        # Only return match if difference is below threshold
        if best_diff < self.SUIT_DIFF_MAX:
            return best_match, best_diff
        else:
            return "Unknown", best_diff

    def detect_and_identify_cards(self, frame):
        """
        Main detection pipeline - finds and identifies all cards in frame
        Returns: list of detected cards with identifications
        """
        # Preprocess
        gray, thresh = self.preprocess_image(frame)

        # Find card contours
        card_contours = self.find_cards(thresh)

        detected_cards = []

        for card_info in card_contours:
            try:
                # Flatten the card using perspective transform
                flattened = self.flatten_card(gray, card_info['approx'])

                # Extract and process corner
                rank_img, suit_img = self.extract_and_process_corner(flattened)

                # Isolate rank and suit
                rank_sized, suit_sized = self.isolate_rank_and_suit(rank_img, suit_img)

                # Match against templates
                rank, rank_diff = self.match_rank(rank_sized)
                suit, suit_diff = self.match_suit(suit_sized)

                # Store results
                detected_cards.append({
                    'rank': rank,
                    'suit': suit,
                    'rank_confidence': 1.0 - (rank_diff / self.RANK_DIFF_MAX),
                    'suit_confidence': 1.0 - (suit_diff / self.SUIT_DIFF_MAX),
                    'contour': card_info['contour'],
                    'bbox': card_info['bbox'],
                    'center': (
                        card_info['bbox'][0] + card_info['bbox'][2] // 2,
                        card_info['bbox'][1] + card_info['bbox'][3] // 2
                    ),
                    'flattened': flattened,
                    'rank_img': rank_sized,
                    'suit_img': suit_sized
                })

            except Exception as e:
                print(f"Error processing card: {e}")
                continue

        return detected_cards

    def annotate_frame(self, frame, detected_cards):
        """Draw detection results on frame"""
        annotated = frame.copy()

        for i, card in enumerate(detected_cards):
            # Draw contour
            cv2.drawContours(annotated, [card['contour']], 0, (0, 255, 0), 3)

            # Draw bounding box
            x, y, w, h = card['bbox']
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Draw center point
            cv2.circle(annotated, card['center'], 5, (0, 0, 255), -1)

            # Add label
            rank_conf = card['rank_confidence']
            suit_conf = card['suit_confidence']

            label = f"{card['rank']} of {card['suit']}"
            conf_label = f"R:{rank_conf:.0%} S:{suit_conf:.0%}"

            # Color based on confidence
            if rank_conf > 0.7 and suit_conf > 0.7:
                color = (0, 255, 0)  # Green - confident
            elif rank_conf > 0.5 and suit_conf > 0.5:
                color = (0, 255, 255)  # Yellow - uncertain
            else:
                color = (0, 0, 255)  # Red - low confidence

            cv2.putText(annotated, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(annotated, conf_label, (x, y + h + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Add detection info
        info_text = f"Cards detected: {len(detected_cards)}"
        cv2.putText(annotated, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        return annotated


class TemplateCollector:
    """Helper class for collecting card templates"""

    def __init__(self, detector: ImprovedCardDetector):
        self.detector = detector

    def collect_templates(self):
        """Interactive template collection"""
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Cards to collect
        ranks = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King']
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']

        print("\n=== TEMPLATE COLLECTION ===")
        print("This will guide you through collecting templates for all cards.")
        print("Place ONE card clearly visible on a dark background.")
        print("Press SPACE to capture, ESC to skip\n")

        # Collect ranks
        for rank in ranks:
            print(f"\n>>> Place a {rank} card (any suit)")
            self._collect_single_template(camera, rank, 'rank')

        # Collect suits
        for suit in suits:
            print(f"\n>>> Place any card with {suit} suit")
            self._collect_single_template(camera, suit, 'suit')

        camera.release()
        cv2.destroyAllWindows()

        print("\n=== Template collection complete! ===")
        self.detector.load_templates()

    def _collect_single_template(self, camera, name, template_type):
        """Collect a single template (rank or suit)"""
        while True:
            ret, frame = camera.read()
            if not ret:
                continue

            gray, thresh = self.detector.preprocess_image(frame)
            cards = self.detector.find_cards(thresh)

            display = frame.copy()

            if len(cards) == 1:
                # Draw the detected card
                cv2.drawContours(display, [cards[0]['contour']], 0, (0, 255, 0), 3)
                cv2.putText(display, "Card detected - Press SPACE to capture",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                key = cv2.waitKey(1) & 0xFF

                if key == ord(' '):  # Space to capture
                    # Flatten the card
                    flattened = self.detector.flatten_card(gray, cards[0]['approx'])

                    # Extract corner
                    rank_img, suit_img = self.detector.extract_and_process_corner(flattened)
                    rank_sized, suit_sized = self.detector.isolate_rank_and_suit(rank_img, suit_img)

                    # Save template
                    if template_type == 'rank':
                        save_dir = os.path.join(self.detector.templates_dir, 'ranks')
                        template_img = rank_sized
                    else:
                        save_dir = os.path.join(self.detector.templates_dir, 'suits')
                        template_img = suit_sized

                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, f"{name}.jpg")
                    cv2.imwrite(save_path, template_img)

                    print(f"✓ Saved {name} template")

                    # Show what was captured
                    cv2.imshow('Captured Template', template_img)
                    cv2.waitKey(1000)
                    break

                elif key == 27:  # ESC to skip
                    print(f"✗ Skipped {name}")
                    break
            else:
                cv2.putText(display, f"Place ONE {name} card on dark background",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(display, f"Detected {len(cards)} cards",
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                cv2.waitKey(1)

            cv2.imshow('Template Collection', display)


def demo_improved_detection():
    """Demo the improved detection system"""
    print("=== Improved Card Detection Demo ===\n")

    detector = ImprovedCardDetector()

    # Check if templates exist
    if not detector.rank_templates or not detector.suit_templates:
        print("No templates found!")
        response = input("Would you like to collect templates now? (y/n): ")
        if response.lower() == 'y':
            collector = TemplateCollector(detector)
            collector.collect_templates()
        else:
            print("Template collection cancelled. Detection may not work well.")

    # Start detection
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n=== Card Detection Active ===")
    print("Place cards on a dark background")
    print("Press 'q' to quit")
    print("Press 't' to collect templates")

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        # Detect cards
        detected_cards = detector.detect_and_identify_cards(frame)

        # Annotate frame
        annotated = detector.annotate_frame(frame, detected_cards)

        # Show result
        cv2.imshow('Improved Card Detection', annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('t'):
            collector = TemplateCollector(detector)
            collector.collect_templates()

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    demo_improved_detection()