import cv2
import numpy as np
from typing import List, Tuple, Optional
import os

class CardDetector:
    """Advanced card detection and recognition system"""
    
    def __init__(self):
        self.card_templates = self.load_card_templates()
        self.min_card_area = 5000
        self.max_card_area = 50000
        self.card_aspect_ratio_range = (0.5, 0.9)
        
        # Preprocessing parameters
        self.gaussian_blur_kernel = (5, 5)
        self.threshold_value = 127
        
    def load_card_templates(self):
        """Load card templates for template matching"""
        # In a real implementation, you would load actual card images
        # For now, we'll create a placeholder structure
        templates = {}
        
        # Card values and suits
        values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        
        # This would be replaced with actual template loading
        for value in values:
            for suit in suits:
                templates[f"{value}_{suit}"] = None
        
        return templates
    
    def preprocess_frame(self, frame):
        """Preprocess the frame for better card detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, self.gaussian_blur_kernel, 0)
        
        # Apply adaptive thresholding for better edge detection
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return gray, blurred, thresh
    
    def find_card_contours(self, thresh_image):
        """Find contours that could be cards"""
        # Find contours
        contours, _ = cv2.findContours(
            thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        card_contours = []
        
        for contour in contours:
            # Filter by area
            area = cv2.contourArea(contour)
            if self.min_card_area < area < self.max_card_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                
                # Check aspect ratio (cards are rectangular)
                if self.card_aspect_ratio_range[0] < aspect_ratio < self.card_aspect_ratio_range[1]:
                    # Approximate the contour to see if it's roughly rectangular
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Cards should have roughly 4 corners
                    if len(approx) >= 4:
                        card_contours.append({
                            'contour': contour,
                            'bbox': (x, y, w, h),
                            'area': area,
                            'aspect_ratio': aspect_ratio
                        })
        
        # Sort by area (largest first, typically more reliable)
        card_contours.sort(key=lambda x: x['area'], reverse=True)
        
        return card_contours
    
    def extract_card_roi(self, frame, card_info):
        """Extract the region of interest for a detected card"""
        x, y, w, h = card_info['bbox']
        
        # Add some padding around the card
        padding = 10
        x_start = max(0, x - padding)
        y_start = max(0, y - padding)
        x_end = min(frame.shape[1], x + w + padding)
        y_end = min(frame.shape[0], y + h + padding)
        
        roi = frame[y_start:y_end, x_start:x_end]
        return roi
    
    def identify_card_value_and_suit(self, card_roi):
        """Identify the card's value and suit from the ROI"""
        # This is where you would implement sophisticated card recognition
        # For now, we'll implement a simplified version
        
        # Convert to grayscale if needed
        if len(card_roi.shape) == 3:
            gray_roi = cv2.cvtColor(card_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray_roi = card_roi
        
        # Focus on the top-left corner where value and suit are typically located
        h, w = gray_roi.shape
        corner_roi = gray_roi[:h//3, :w//3]
        
        # For demonstration, we'll use a simplified heuristic approach
        # In reality, you'd use template matching or ML models
        value, suit = self.simple_card_recognition(corner_roi)
        
        return value, suit
    
    def simple_card_recognition(self, corner_roi):
        """Simplified card recognition (placeholder for real implementation)"""
        # This is a very basic implementation
        # In a real system, you would use template matching or machine learning
        
        # Analyze the corner region
        _, thresh = cv2.threshold(corner_roi, 127, 255, cv2.THRESH_BINARY)
        
        # Count white pixels (simplified heuristic)
        white_pixels = np.sum(thresh == 255)
        total_pixels = thresh.size
        white_ratio = white_pixels / total_pixels
        
        # Very simplified logic (this would need to be much more sophisticated)
        values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        
        # Use white pixel ratio to guess (very crude approach)
        value_index = int(white_ratio * len(values)) % len(values)
        suit_index = int(white_ratio * len(suits) * 2) % len(suits)
        
        return values[value_index], suits[suit_index]
    
    def template_match_card(self, card_roi):
        """Use template matching to identify cards (more accurate approach)"""
        # This would be the preferred method with actual card templates
        best_match = None
        best_score = 0
        
        if len(card_roi.shape) == 3:
            card_gray = cv2.cvtColor(card_roi, cv2.COLOR_BGR2GRAY)
        else:
            card_gray = card_roi
        
        # Resize card ROI to standard size for template matching
        standard_size = (200, 280)  # Standard card proportions
        card_resized = cv2.resize(card_gray, standard_size)
        
        # This is where you would compare against actual templates
        # For demonstration purposes, we'll return a placeholder
        return self.simple_card_recognition(card_gray)
    
    def detect_and_identify_cards(self, frame):
        """Main method to detect and identify all cards in the frame"""
        # Preprocess the frame
        gray, blurred, thresh = self.preprocess_frame(frame)
        
        # Find card contours
        card_contours = self.find_card_contours(thresh)
        
        detected_cards = []
        annotated_frame = frame.copy()
        
        for i, card_info in enumerate(card_contours):
            # Extract card ROI
            card_roi = self.extract_card_roi(gray, card_info)
            
            if card_roi.size > 0:
                # Identify the card
                value, suit = self.identify_card_value_and_suit(card_roi)
                
                # Store card information
                detected_cards.append({
                    'value': value,
                    'suit': suit,
                    'bbox': card_info['bbox'],
                    'confidence': 0.8,  # Placeholder confidence score
                    'area': card_info['area']
                })
                
                # Annotate the frame
                x, y, w, h = card_info['bbox']
                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Add text label
                label = f"{value} of {suit}"
                label_y = y - 10 if y > 20 else y + h + 20
                cv2.putText(annotated_frame, label, (x, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Add card number
                cv2.putText(annotated_frame, f"#{i+1}", (x + 5, y + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        
        return detected_cards, annotated_frame
    
    def get_card_positions(self, detected_cards):
        """Organize detected cards by their positions (useful for determining player vs dealer cards)"""
        if not detected_cards:
            return {'player': [], 'dealer': []}
        
        # Sort cards by y-coordinate (top to bottom)
        sorted_cards = sorted(detected_cards, key=lambda card: card['bbox'][1])
        
        # Simple heuristic: cards in top half are dealer's, bottom half are player's
        frame_height = 480  # Assuming standard camera resolution
        
        player_cards = []
        dealer_cards = []
        
        for card in sorted_cards:
            x, y, w, h = card['bbox']
            center_y = y + h // 2
            
            if center_y < frame_height // 2:
                dealer_cards.append(card)
            else:
                player_cards.append(card)
        
        return {'player': player_cards, 'dealer': dealer_cards}
    
    def validate_card_detection(self, detected_cards, expected_count=None):
        """Validate the detected cards for consistency"""
        if expected_count and len(detected_cards) != expected_count:
            return False, f"Expected {expected_count} cards, but detected {len(detected_cards)}"
        
        # Check for duplicate cards (same value and suit)
        card_signatures = []
        for card in detected_cards:
            signature = f"{card['value']}_{card['suit']}"
            if signature in card_signatures:
                return False, f"Detected duplicate card: {card['value']} of {card['suit']}"
            card_signatures.append(signature)
        
        # Check confidence scores
        low_confidence_cards = [card for card in detected_cards if card['confidence'] < 0.5]
        if low_confidence_cards:
            return False, f"Low confidence detection for {len(low_confidence_cards)} cards"
        
        return True, "Card detection validated successfully"


def test_card_detector():
    """Test the card detector with a live camera feed"""
    detector = CardDetector()
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("Error: Could not open camera")
        return
    
    print("Card Detector Test")
    print("Place cards in view of the camera")
    print("Press 'q' to quit, 's' to save current frame")
    
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        
        # Detect and identify cards
        detected_cards, annotated_frame = detector.detect_and_identify_cards(frame)
        
        # Display information
        info_text = f"Detected {len(detected_cards)} cards"
        cv2.putText(annotated_frame, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow('Card Detector Test', annotated_frame)
        
        # Print detected cards
        if detected_cards:
            print(f"Detected {len(detected_cards)} cards:")
            for i, card in enumerate(detected_cards):
                print(f"  {i+1}. {card['value']} of {card['suit']} (confidence: {card['confidence']:.2f})")
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite('detected_cards.jpg', annotated_frame)
            print("Frame saved as 'detected_cards.jpg'")
    
    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_card_detector()