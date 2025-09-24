import cv2
import numpy as np
import pyttsx3
import time
import os

class HandheldCardDetector:
    def __init__(self):
        # Initialize text-to-speech
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 150)
        self.tts.setProperty('volume', 0.9)
        
        # Initialize camera
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Enhanced detection parameters for handheld cards
        self.min_card_area = 5000   # Smaller minimum for distant cards
        self.max_card_area = 200000 # Larger maximum for close cards
        self.min_aspect_ratio = 0.4
        self.max_aspect_ratio = 1.0
        
        # Template storage
        self.templates_dir = "card_templates"
        os.makedirs(self.templates_dir, exist_ok=True)
        self.templates = {}
        self.load_templates()
        
        # Card tracking
        self.last_cards = []
        self.stable_count = 0
        self.required_stable_frames = 5  # Faster response for handheld
        
        self.speak("Handheld card detector started! You can hold cards up to the camera.")
        
        if not self.templates:
            self.speak("No templates found. Press 1 to train cards first.")
        else:
            self.speak(f"Loaded {len(self.templates)} card templates.")
    
    def speak(self, text):
        print(f"Speaking: {text}")
        self.tts.say(text)
        self.tts.runAndWait()
    
    def load_templates(self):
        """Load saved card templates"""
        if not os.path.exists(self.templates_dir):
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.png'):
                card_name = filename[:-4]
                template_path = os.path.join(self.templates_dir, filename)
                template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    self.templates[card_name] = template
    
    def detect_cards_in_frame(self, frame):
        """Enhanced card detection that works with any background"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Use Canny edge detection for better edge finding
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        cards = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if self.min_card_area < area < self.max_card_area:
                # Approximate contour to polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # Check aspect ratio and corner count
                if (self.min_aspect_ratio < aspect_ratio < self.max_aspect_ratio and 
                    len(approx) >= 4):  # Should have at least 4 corners
                    
                    # Calculate additional features for better filtering
                    hull = cv2.convexHull(contour)
                    hull_area = cv2.contourArea(hull)
                    solidity = area / hull_area if hull_area > 0 else 0
                    
                    # Cards should be relatively solid (rectangular)
                    if solidity > 0.7:
                        cards.append({
                            'contour': contour,
                            'bbox': (x, y, w, h),
                            'area': area,
                            'center': (x + w//2, y + h//2),
                            'aspect_ratio': aspect_ratio,
                            'solidity': solidity
                        })
        
        # Sort by area (largest first) and keep top candidates
        cards.sort(key=lambda x: x['area'], reverse=True)
        return cards[:5]  # Keep top 5 candidates
    
    def extract_corner_advanced(self, frame, card_info):
        """Extract corner with perspective correction for handheld cards"""
        contour = card_info['contour']
        
        # Get the four corners of the card
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(approx) >= 4:
            # Sort points to get consistent corner order
            points = approx.reshape(4, 2) if len(approx) == 4 else self.get_four_corners(approx)
            points = self.order_points(points)
            
            # Define the destination points for perspective correction
            width, height = 200, 280  # Standard card proportions
            dst_points = np.array([
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1]
            ], dtype="float32")
            
            # Get perspective transform matrix
            matrix = cv2.getPerspectiveTransform(points.astype("float32"), dst_points)
            
            # Apply perspective correction
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corrected = cv2.warpPerspective(gray_frame, matrix, (width, height))
            
            # Extract corner (top-left portion)
            corner_h, corner_w = 100, 80
            corner = corrected[0:corner_h, 0:corner_w]
            
            # Enhance corner contrast
            corner = cv2.equalizeHist(corner)
            
            return corner
        
        # Fallback to simple bounding box extraction
        x, y, w, h = card_info['bbox']
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        card_region = gray_frame[y:y+h, x:x+w]
        
        if card_region.size < 100:
            return None
        
        # Extract corner
        corner_h = min(h//3, 120)
        corner_w = min(w//3, 90)
        corner = card_region[0:corner_h, 0:corner_w]
        
        if corner.size < 100:
            return None
        
        # Resize to standard size
        corner = cv2.resize(corner, (80, 100))
        corner = cv2.equalizeHist(corner)
        
        return corner
    
    def get_four_corners(self, approx):
        """Get four corner points from approximated contour"""
        if len(approx) < 4:
            return approx.reshape(-1, 2)
        
        # If more than 4 points, find the 4 corners
        points = approx.reshape(-1, 2)
        
        # Find the extreme points
        top_left = points[np.argmin(points.sum(axis=1))]
        bottom_right = points[np.argmax(points.sum(axis=1))]
        top_right = points[np.argmin(np.diff(points, axis=1))]
        bottom_left = points[np.argmax(np.diff(points, axis=1))]
        
        return np.array([top_left, top_right, bottom_right, bottom_left])
    
    def order_points(self, pts):
        """Order points in consistent order: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sum and difference to find corners
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        rect[0] = pts[np.argmin(s)]      # top-left
        rect[2] = pts[np.argmax(s)]      # bottom-right
        rect[1] = pts[np.argmin(diff)]   # top-right
        rect[3] = pts[np.argmax(diff)]   # bottom-left
        
        return rect
    
    def identify_card(self, frame, card_info):
        """Identify card using enhanced template matching"""
        corner = self.extract_corner_advanced(frame, card_info)
        if corner is None or not self.templates:
            return "Unknown", 0.0
        
        best_match = None
        best_score = 0.0
        
        for card_name, template in self.templates.items():
            # Resize template to match corner size
            template_resized = cv2.resize(template, (corner.shape[1], corner.shape[0]))
            
            # Multiple template matching methods for better accuracy
            methods = [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]
            scores = []
            
            for method in methods:
                result = cv2.matchTemplate(corner, template_resized, method)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                scores.append(max_val)
            
            # Average the scores
            avg_score = np.mean(scores)
            
            if avg_score > best_score:
                best_score = avg_score
                best_match = card_name
        
        return best_match if best_match and best_score > 0.4 else "Unknown", best_score
    
    def save_template(self, card_name, corner_image):
        """Save card template"""
        template_path = os.path.join(self.templates_dir, f"{card_name}.png")
        cv2.imwrite(template_path, corner_image)
        self.templates[card_name] = corner_image.copy()
        print(f"Saved template: {card_name}")
    
    def training_mode(self):
        """Training mode optimized for handheld cards"""
        self.speak("Training mode. Hold ONE card steady in view and press C to capture. Press Q to quit.")
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            detected_cards = self.detect_cards_in_frame(frame)
            
            # Draw enhanced annotations
            annotated = frame.copy()
            
            for i, card in enumerate(detected_cards):
                x, y, w, h = card['bbox']
                
                # Draw the detected contour
                cv2.drawContours(annotated, [card['contour']], -1, (0, 255, 0), 2)
                
                # Draw bounding rectangle
                if len(detected_cards) == 1:
                    color = (0, 255, 0)
                    text = "READY - Press C"
                else:
                    color = (0, 255, 255)
                    text = f"Card {i+1}"
                
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                cv2.putText(annotated, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # Add quality info
                quality_text = f"Quality: {card['solidity']:.2f}"
                cv2.putText(annotated, quality_text, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Instructions
            cv2.putText(annotated, "TRAINING MODE - Hold card steady", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(annotated, f"Templates: {len(self.templates)}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(annotated, "C=Capture, Q=Quit", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            cv2.imshow('Training Mode - Hold Card Steady', annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                if len(detected_cards) >= 1:
                    # Use the best (largest) detected card
                    self.capture_template(detected_cards[0], frame)
                else:
                    self.speak("No card detected. Hold a card steady in view.")
        
        cv2.destroyAllWindows()
    
    def capture_template(self, card_info, frame):
        """Capture template with enhanced processing"""
        corner = self.extract_corner_advanced(frame, card_info)
        if corner is None:
            self.speak("Cannot extract card corner clearly. Try holding the card steadier.")
            return
        
        # Show what was captured
        cv2.imshow('Captured Corner - Press any key', corner)
        cv2.waitKey(2000)
        cv2.destroyWindow('Captured Corner - Press any key')
        
        self.speak("What card is this?")
        print("Enter card name (e.g., 'Ace of Hearts', '5 of Spades'): ")
        card_name = input().strip().title()
        
        if card_name:
            self.save_template(card_name, corner)
            self.speak(f"Saved {card_name}")
        else:
            self.speak("No name entered")
    
    def cards_are_stable(self, current_cards):
        """Check if cards are stable (adapted for handheld movement)"""
        if len(current_cards) != len(self.last_cards):
            self.stable_count = 0
            return False
        
        if not current_cards:
            self.stable_count = 0
            return False
        
        # More lenient stability check for handheld cards
        for i, current_card in enumerate(current_cards):
            if i < len(self.last_cards):
                current_center = current_card['center']
                last_center = self.last_cards[i]['center']
                
                distance = np.sqrt((current_center[0] - last_center[0])**2 + 
                                 (current_center[1] - last_center[1])**2)
                
                # Allow more movement for handheld cards
                if distance > 80:
                    self.stable_count = 0
                    return False
        
        self.stable_count += 1
        return self.stable_count >= self.required_stable_frames
    
    def announce_cards(self, cards, frame):
        """Announce detected cards"""
        if not cards:
            return
        
        self.speak(f"I see {len(cards)} card{'s' if len(cards) > 1 else ''}:")
        
        for i, card_info in enumerate(cards):
            card_name, confidence = self.identify_card(frame, card_info)
            
            if confidence > 0.6:
                self.speak(f"Card {i + 1}: {card_name}")
            elif confidence > 0.4:
                self.speak(f"Card {i + 1}: Probably {card_name}")
            else:
                self.speak(f"Card {i + 1}: Cannot identify clearly")
    
    def detection_mode(self):
        """Detection mode optimized for handheld cards"""
        if not self.templates:
            self.speak("No templates available. Train some cards first!")
            return
        
        self.speak(f"Detection mode ready! Hold cards up to the camera. I know {len(self.templates)} cards. Press Q to quit.")
        
        frame_count = 0
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            frame_count += 1
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            # Process every other frame for better performance
            if frame_count % 2 == 0:
                detected_cards = self.detect_cards_in_frame(frame)
                
                if self.cards_are_stable(detected_cards):
                    self.announce_cards(detected_cards, frame)
                    self.stable_count = 0
                    time.sleep(1.5)  # Shorter delay for handheld use
                
                self.last_cards = detected_cards
            else:
                detected_cards = self.last_cards
            
            # Draw enhanced annotations
            annotated = frame.copy()
            for i, card in enumerate(detected_cards):
                x, y, w, h = card['bbox']
                
                # Draw contour outline
                cv2.drawContours(annotated, [card['contour']], -1, (255, 0, 0), 2)
                
                # Identify card for display
                card_name, confidence = self.identify_card(frame, card)
                
                # Color based on confidence
                if confidence > 0.6:
                    color = (0, 255, 0)  # Green - confident
                elif confidence > 0.4:
                    color = (0, 255, 255)  # Yellow - maybe
                else:
                    color = (0, 0, 255)  # Red - unsure
                
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                cv2.putText(annotated, card_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(annotated, f"{confidence:.0%}", (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Status display
            cv2.putText(annotated, "DETECTION MODE - Hold cards up", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(annotated, f"Known cards: {len(self.templates)}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(annotated, f"Stability: {self.stable_count}/{self.required_stable_frames}", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(annotated, "Q=Quit", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            cv2.imshow('Detection Mode - Hold Cards Up', annotated)
        
        cv2.destroyAllWindows()
    
    def run(self):
        """Main program loop"""
        if not self.camera.isOpened():
            self.speak("Cannot open camera")
            return
        
        while True:
            print("\nHandheld Card Detector Menu:")
            print("1. Training Mode (teach cards by holding them up)")
            print("2. Detection Mode (identify cards you hold up)")
            print("3. Quit")
            
            choice = input("Choose (1/2/3): ").strip()
            
            if choice == '1':
                self.training_mode()
            elif choice == '2':
                self.detection_mode()
            elif choice == '3':
                break
            else:
                print("Invalid choice")
        
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.camera.release()
        cv2.destroyAllWindows()
        self.speak("Goodbye!")


def main():
    print("Handheld Card Detector")
    print("=" * 40)
    print("Hold cards up to the camera - no table needed!")
    print("Works with any background")
    print("=" * 40)
    
    detector = HandheldCardDetector()
    detector.run()


if __name__ == "__main__":
    main()