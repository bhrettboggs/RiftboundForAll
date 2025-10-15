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
        print("--- EXECUTING THE CORRECT GRAYSCALE PREDICTION CODE ---")

        if self.model is None or card_image is None or card_image.size == 0:
            return "Unknown", 0.0

        try:
            # Convert the incoming color image to grayscale to match the model's training data.
            gray_image = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
            
            # Resize the grayscale image to the model's expected input size.
            img_resized = cv2.resize(gray_image, (self.img_width, self.img_height))
            
            
            # Convert the image to an array and reshape it for the model.
            img_array = tf.keras.preprocessing.image.img_to_array(img_resized)
            img_array = np.expand_dims(img_array, axis=0)
            
            # Rescale pixel values just like in training.
            img_array /= 255.0

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