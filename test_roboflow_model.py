import cv2
from roboflow import Roboflow
import time # Import time for FPS calculation (optional but good)

# --- 1. AUTHENTICATION ---
# Paste your NEW private API key here.
rf = Roboflow(api_key="E4GmFyFX8INFwjF1BOvw")

# --- 2. LOAD THE PROJECT AND GET CLASS NAMES ---
workspace_id = "augmented-startups"
project_id = "playing-cards-ow27d"
version_number = 4

# Load the project first
project = rf.workspace(workspace_id).project(project_id)

# Get the class names dictionary
class_names_dict = project.classes

# Get the specific version
version = project.version(version_number)

# Load the model
model = version.model

print("Model loaded successfully!")
print("Class names dictionary:", class_names_dict)

# --- 3. SETUP WEBCAM AND OPTIMIZATIONS ---
cap = cv2.VideoCapture(0)

# --- FPS OPTIMIZATION 1: Set Lower Resolution ---
desired_width = 640
desired_height = 480
cap.set(cv2.CAP_PROP_FRAME_WIDTH, desired_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, desired_height)
print(f"Attempting to set camera resolution to {desired_width}x{desired_height}")

# --- FPS OPTIMIZATION 2: Frame Skipping ---
frame_counter = 0
process_every_n_frames = 3 # Adjust this number (2, 3, 4...) to trade smoothness for detection frequency
latest_results = {'predictions': []} # Store the last valid detection results

# --- Optional: For displaying FPS ---
prev_frame_time = 0
new_frame_time = 0

print("Starting camera feed...")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame from camera.")
        break

    frame_counter += 1
    new_frame_time = time.time() # For FPS calculation

    # --- Run Prediction only on specified frames ---
    if frame_counter % process_every_n_frames == 0:
        # Run prediction on the live frame
        try:
            results = model.predict(frame, confidence=40, overlap=30).json()
            latest_results = results # Update the stored results
        except Exception as e:
            print(f"Error during prediction: {e}")
            results = latest_results # Keep using old results on error
    else:
        # Use the results from the last processed frame
        results = latest_results

    # --- 4. DRAW THE RESULTS (using the current 'results') ---
    for bounding_box in results.get('predictions', []): # Use .get() for safety
        try:
            x1 = int(bounding_box['x'] - bounding_box['width'] / 2)
            y1 = int(bounding_box['y'] - bounding_box['height'] / 2)
            x2 = int(bounding_box['x'] + bounding_box['width'] / 2)
            y2 = int(bounding_box['y'] + bounding_box['height'] / 2)
            
            label = bounding_box['class']
            confidence = bounding_box['confidence']
            
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            cv2.putText(frame, f"{label} ({confidence:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        except KeyError as e:
            print(f"Error processing bounding box data: Missing key {e}")
        except Exception as e:
            print(f"Error drawing box: {e}")

    # --- Optional: Calculate and Display FPS ---
    fps = 1 / (new_frame_time - prev_frame_time)
    prev_frame_time = new_frame_time
    cv2.putText(frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # --- 5. Show the frame ---
    cv2.imshow("Roboflow YOLOv8 Test (Optimized)", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
print("Script finished.")