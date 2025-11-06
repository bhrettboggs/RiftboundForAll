import cv2
from roboflow import Roboflow
import time

class CardDetector:
    def __init__(self):
        """
        Initializes the Roboflow model and camera.
        """
        try:
            # --- 1. AUTHENTICATION & MODEL LOAD ---
            # Using the API key you provided
            api_key = "DiIME5kv2PXA6GJQWMI1" 
            rf = Roboflow(api_key=api_key)
            
            project = rf.workspace("augmented-startups").project("playing-cards-ow27d")
            self.model = project.version(4).model
            print("Roboflow model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None

        # --- 2. CAMERA SETUP ---
        self.cap = cv2.VideoCapture(0)
        self.desired_width = 640
        self.desired_height = 480
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.desired_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.desired_height)
        
        # --- 3. SPATIAL ZONES ---
        self.midpoint_y = int(self.desired_height / 2)
        self.DEALER_COLOR = (0, 0, 255) # Red
        self.PLAYER_COLOR = (0, 255, 0) # Green
        
        # --- 4. OPTIMIZATION ---
        self.latest_results = {'predictions': []}
        self.frame_counter = 0
        self.process_every_n_frames = 3

    def get_detected_cards(self):
        """
        This is the main function Evan's script will call.
        It captures one frame, finds the cards, and returns their data.
        
        Returns:
            - A list of dictionaries, e.g., [{'id': 'KS', 'owner': 'Player', 'confidence': 0.85}, ...]
            - The annotated video frame to be displayed.
        """
        if not self.cap.isOpened() or self.model is None:
            return [], None

        ret, frame = self.cap.read()
        if not ret:
            return [], None
            
        annotated_frame = frame.copy()
        detected_cards_list = [] # This is the raw list from Roboflow

        # --- Run Prediction only on specified frames ---
        self.frame_counter += 1
        if self.frame_counter % self.process_every_n_frames == 0:
            try:
                # Using the confidence/overlap from your file
                results = self.model.predict(frame, confidence=40, overlap=45).json()
                self.latest_results = results
            except Exception as e:
                print(f"Error during prediction: {e}")
                results = self.latest_results
        else:
            results = self.latest_results

        # --- Draw Zones (Reverted to simple line) ---
        cv2.line(annotated_frame, (0, self.midpoint_y), (self.desired_width, self.midpoint_y), (255, 255, 0), 2)
        cv2.putText(annotated_frame, "DEALER ZONE", (10, self.midpoint_y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.DEALER_COLOR, 2)
        cv2.putText(annotated_frame, "PLAYER ZONE", (10, self.midpoint_y + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.PLAYER_COLOR, 2)

        # --- Process Results ---
        for box in results.get('predictions', []):
            y_center = box['y']
            
            if y_center < self.midpoint_y:
                owner = "Dealer"
                color = self.DEALER_COLOR
            else:
                owner = "Player"
                color = self.PLAYER_COLOR
            
            # Add this card's data to our raw list
            detected_cards_list.append({
                'id': box['class'],
                'owner': owner,
                'confidence': box['confidence'],
                'bbox': (box['x'], box['y'], box['width'], box['height']) # Pass raw data
            })
            
            # --- Draw on the annotated frame ---
            x1 = int(box['x'] - box['width'] / 2)
            y1 = int(box['y'] - box['height'] / 2)
            x2 = int(box['x'] + box['width'] / 2)
            y2 = int(box['y'] + box['height'] / 2)
            
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{owner}: {box['class']} ({box['confidence']:.2f})"
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # --- START: New De-duplication Logic ---
        # This fixes the bug where both corners of a card are counted.
        final_cards_list = []
        # This set will track (card_id, owner) tuples, e.g., ('KS', 'Player')
        seen_cards = set() 

        # Sort by confidence so we keep the *best* detection
        detected_cards_list.sort(key=lambda c: c['confidence'], reverse=True)

        for card in detected_cards_list:
            # Create a unique key for each card in each zone
            seen_key = (card['id'], card['owner'])
            
            if seen_key not in seen_cards:
                final_cards_list.append(card)
                seen_cards.add(seen_key)
        # --- END: New De-duplication Logic ---

        # Return the *filtered* list to the game logic
        return final_cards_list, annotated_frame

    def cleanup(self):
        """Releases the camera."""
        self.cap.release()

# --- This part is just for testing YOUR script ---
if __name__ == "__main__":
    print("Running CardDetector in test mode...")
    detector = CardDetector()
    
    while True:
        # Get the data and the frame
        cards_data, frame_to_show = detector.get_detected_cards()
        
        if frame_to_show is None:
            break
            
        # Print the *final* filtered data
        if cards_data:
            print(cards_data)
            
        # Show the video feed
        cv2.imshow("Card Detector Test", frame_to_show)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.cleanup()
    cv2.destroyAllWindows()