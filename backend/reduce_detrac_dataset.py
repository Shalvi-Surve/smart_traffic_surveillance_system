import os
import random
import shutil

# SOURCE dataset folders
train_folder = r"D:\smart_traffic_surveillance_system\backend\DETRAC_Upload\images\train"
val_folder = r"D:\smart_traffic_surveillance_system\backend\DETRAC_Upload\images\val"

# DESTINATION test images folder
dest_folder = r"D:\smart_traffic_surveillance_system\data\images"

os.makedirs(dest_folder, exist_ok=True)

# Collect all images
all_images = []

for root, dirs, files in os.walk(train_folder):
    for f in files:
        if f.endswith(".jpg"):
            all_images.append(os.path.join(root, f))

for root, dirs, files in os.walk(val_folder):
    for f in files:
        if f.endswith(".jpg"):
            all_images.append(os.path.join(root, f))

print("Total images found:", len(all_images))

# Randomly pick 20
sample_images = random.sample(all_images, 20)

# Copy them
for i, img_path in enumerate(sample_images):
    new_name = f"traffic{i+1:02d}.jpg"
    dest_path = os.path.join(dest_folder, new_name)

    shutil.copy(img_path, dest_path)

print("20 traffic images copied successfully!")