import cv2
import numpy as np

def debug_card_detection():
    """Simple debug script to test card detection"""
    
    # Initialize camera
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("Debug Card Detection")
    print("Press 's' to save current frame")
    print("Press 'q' to quit")
    print("Adjust these values if no cards detected:")
    
    # Adjustable parameters
    min_area = 3000      # Lower = detect smaller objects
    max_area = 80000     # Higher = detect larger objects
    min_aspect = 0.4     # Lower = detect more rectangular shapes
    max_aspect = 1.0     # Higher = detect more square shapes
    
    print(f"Current settings:")
    print(f"  Min area: {min_area}")
    print(f"  Max area: {max_area}")
    print(f"  Aspect ratio: {min_aspect} - {max_aspect}")
    
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Multiple threshold methods to see which works best
        
        # Method 1: Simple threshold
        _, thresh1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Method 2: Adaptive threshold
        thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Method 3: Otsu's threshold
        _, thresh3 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Try detection with each method
        for i, thresh in enumerate([thresh1, thresh2, thresh3], 1):
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            card_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if min_area < area < max_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = float(w) / h
                    
                    if min_aspect < aspect_ratio < max_aspect:
                        card_count += 1
                        # Draw rectangle around detected card
                        color = [(255, 0, 0), (0, 255, 0), (0, 0, 255)][i-1]  # Different color for each method
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        
                        # Add text
                        cv2.putText(frame, f"Method{i}: {int(area)}", (x, y-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Add info to frame
        cv2.putText(frame, "Blue=Simple, Green=Adaptive, Red=Otsu", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        total_contours = len(contours)
        cv2.putText(frame, f"Total contours found: {total_contours}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow('Card Detection Debug', frame)
        cv2.imshow('Grayscale', gray)
        cv2.imshow('Thresholded', thresh2)  # Show adaptive threshold
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite('debug_frame.jpg', frame)
            cv2.imwrite('debug_gray.jpg', gray)
            cv2.imwrite('debug_thresh.jpg', thresh2)
            print("Frames saved!")
    
    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_card_detection()