import numpy as np
import tensorflow as tf
import cv2
import ast

class CNNRecognitionModule:
    """Handles loading the CNN model and making predictions."""

    def __init__(self, model_path='riftbound_card_recognition_model.h5', class_indices_path='cnn_class_indices.txt'):
        self.model_path = model_path
        self.class_indices_path = class_indices_path
        self.img_width, self.img_height = 150, 150
        
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            with open(self.class_indices_path, 'r') as f:
                self.class_indices = ast.literal_eval(f.read())
            
            # Create a reverse mapping from index to class name
            self.class_labels = {v: k for k, v in self.class_indices.items()}
            print("CNN model and class indices loaded successfully.")
        except Exception as e:
            self.model = None
            self.class_labels = None
            print(f"Error loading CNN model or class indices: {e}")

    def predict_card(self, card_image):
        """
        Predicts the card from an image.
        Returns: (card_name, confidence_score)
        """
        # We removed the print statement to reduce console clutter
        
        if self.model is None or card_image is None or card_image.size == 0:
            return "Unknown", 0.0

        try:
            # --- START OF FIX ---
            # The 'card_image' we receive is ALREADY the correct
            # 2D (150, 150) grayscale image. We must not convert it.
            # We just assign it to a new variable for clarity.
            img_resized = card_image
            # --- END OF FIX ---
            
            
            # --- START OF FIX ---
            # We replace img_to_array() with a manual reshape to guarantee
            # the (150, 150, 1) shape the model expects.
            img_array = img_resized.reshape(self.img_width, self.img_height, 1)
            # --- END OF FIX ---
            
            img_array = np.expand_dims(img_array, axis=0)
            
            # Rescale pixel values just like in training.
            img_array = img_array.astype('float32') / 255.0 # Also ensure it's float

            # Make the prediction.
            predictions = self.model.predict(img_array, verbose=0)
            score = tf.nn.softmax(predictions[0])
            
            predicted_index = np.argmax(score)
            confidence = np.max(score)
            card_name = self.class_labels[predicted_index]
            
            return card_name, float(confidence)
        
        except Exception as e:
            print(f"Error during card prediction: {e}")
            return "Error", 0.0