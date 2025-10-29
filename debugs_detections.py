import cv2
import numpy as np

# This is a helper function to create the sliders
def nothing(x):
    pass

def main():
    print("Starting detection debugger...")
    print("Place a card on a dark, non-reflective surface.")
    print("Adjust the sliders until the card is perfectly detected.")
    print("Press 'q' to quit.")

    # --- Setup Camera ---
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # --- Create Windows ---
    cv2.namedWindow('Settings')
    cv2.namedWindow('Original')
    cv2.namedWindow('Threshold')
    cv2.namedWindow('Annotated')
    
    # --- Create Sliders ---
    # These are the values we need to find!
    # Based on cv_detection_module.py
    cv2.createTrackbar('Min Area', 'Settings', 25000, 100000, nothing)
    cv2.createTrackbar('Aspect Min (x10)', 'Settings', 4, 10, nothing)
    cv2.createTrackbar('Aspect Max (x10)', 'Settings', 10, 10, nothing)
    
    # Sliders for adaptiveThreshold
    # Block size must be an odd number >= 3
    cv2.createTrackbar('Thresh Block Size', 'Settings', 11, 51, nothing) 
    cv2.createTrackbar('Thresh C', 'Settings', 1, 10, nothing)

    while True:
        # --- Get Settings from Sliders ---
        min_area = cv2.getTrackbarPos('Min Area', 'Settings')
        aspect_min = cv2.getTrackbarPos('Aspect Min (x10)', 'Settings') / 10.0
        aspect_max = cv2.getTrackbarPos('Aspect Max (x10)', 'Settings') / 10.0
        
        block_size = cv2.getTrackbarPos('Thresh Block Size', 'Settings')
        thresh_c = cv2.getTrackbarPos('Thresh C', 'Settings')
        
        # Ensure block_size is odd and >= 3
        if block_size < 3:
            block_size = 3
        if block_size % 2 == 0:
            block_size += 1
            
        # --- Pre-processing (from cv_detection_module.py) ---
        ret, frame = camera.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, block_size, thresh_c
        )

        # --- Detection (from cv_detection_module.py) ---
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        annotated_frame = frame.copy()
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                
                # Filter by aspect ratio
                if aspect_min < aspect_ratio < aspect_max:
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Filter by 4 corners
                    if len(approx) == 4:
                        cv2.drawContours(annotated_frame, [approx], 0, (0, 255, 0), 3)
                        status = f"DETECTED: Area={area}"
                        cv2.putText(annotated_frame, status, (x, y - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # --- Show the windows ---
        cv2.imshow('Original', frame)
        cv2.imshow('Threshold', thresh)
        cv2.imshow('Annotated', annotated_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()
    print("Debugger stopped.")
    print("\n--- FINAL SETTINGS ---")
    print(f"Min Area: {min_area}")
    print(f"Aspect Min (x10): {aspect_min * 10}")
    print(f"Aspect Max (x10): {aspect_max * 10}")
    print(f"Thresh Block Size: {block_size}")
    print(f"Thresh C: {thresh_c}")

if __name__ == "__main__":
    main()