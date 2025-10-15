import os
import shutil
import random
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator, img_to_array, load_img

# Configuration
SOURCE_DIR = "raw_cards"
OUTPUT_DIR = "card_data"
TRAIN_DIR = os.path.join(OUTPUT_DIR, "train")
VALIDATION_DIR = os.path.join(OUTPUT_DIR, "validation")
IMG_WIDTH, IMG_HEIGHT = 150, 150
VALIDATION_SPLIT = 0.2
AUGMENTATION_FACTOR = 30  # Create 30 new images for each original image

def create_dataset_structure():
    """Creates the necessary train/validation directory structure."""
    print(f"Creating dataset structure in '{OUTPUT_DIR}'...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    
    os.makedirs(TRAIN_DIR, exist_ok=True)
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    
    card_classes = [d for d in os.listdir(SOURCE_DIR) if os.path.isdir(os.path.join(SOURCE_DIR, d))]
    for card_class in card_classes:
        os.makedirs(os.path.join(TRAIN_DIR, card_class), exist_ok=True)
        os.makedirs(os.path.join(VALIDATION_DIR, card_class), exist_ok=True)
    print("Directory structure created.")
    return card_classes

def split_data(card_classes):
    """Splits original images into training and validation sets."""
    print("Splitting original data into training and validation sets...")
    for card_class in card_classes:
        source_path = os.path.join(SOURCE_DIR, card_class)
        all_files = [f for f in os.listdir(source_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        random.shuffle(all_files)
        
        split_index = int(len(all_files) * VALIDATION_SPLIT)
        validation_files = all_files[:split_index]
        train_files = all_files[split_index:]
        
        # Copy files
        for f in train_files:
            shutil.copy(os.path.join(source_path, f), os.path.join(TRAIN_DIR, card_class, f))
        for f in validation_files:
            shutil.copy(os.path.join(source_path, f), os.path.join(VALIDATION_DIR, card_class, f))
    print("Data splitting complete.")

def augment_data():
    """Applies data augmentation to the training set."""
    print("Starting data augmentation...")
    
    # This ImageDataGenerator creates a wide variety of transformed images
    datagen = ImageDataGenerator(
        rotation_range=20,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.1,
        zoom_range=0.1,
        horizontal_flip=False, # Cards shouldn't be flipped
        vertical_flip=False,
        brightness_range=[0.8, 1.2],
        fill_mode='nearest'
    )
    
    card_classes = [d for d in os.listdir(TRAIN_DIR) if os.path.isdir(os.path.join(TRAIN_DIR, d))]
    
    for card_class in card_classes:
        class_path = os.path.join(TRAIN_DIR, card_class)

        # --- THIS IS THE FIX ---
        # Although create_dataset_structure already made this directory,
        # this line acts as a safeguard to prevent any subtle path handling
        # bugs in the Keras generator by ensuring the path is explicitly available.
        os.makedirs(class_path, exist_ok=True)
        # --- END OF FIX ---
        
        image_files = os.listdir(class_path)
        print(f"  Augmenting {card_class} ({len(image_files)} originals)...")
        
        for image_file in image_files:
            img_path = os.path.join(class_path, image_file)
            img = load_img(img_path)
            x = img_to_array(img)
            x = x.reshape((1,) + x.shape)
            
            # Generate batches of randomly transformed images
            i = 0
            for batch in datagen.flow(x, batch_size=1, save_to_dir=class_path, save_prefix='aug', save_format='jpg'):
                i += 1
                if i >= AUGMENTATION_FACTOR:
                    break  # Break the loop after creating enough augmentations
    print("Data augmentation complete.")


if __name__ == '__main__':
    if not os.path.isdir(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' not found.")
        print("Please create it and place your raw card images inside subdirectories (e.g., raw_cards/2_of_hearts/).")
    else:
        card_classes = create_dataset_structure()
        split_data(card_classes)
        augment_data()
        print("\nDataset successfully created and augmented!")