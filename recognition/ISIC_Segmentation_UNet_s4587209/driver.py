import glob
import os
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from sklearn.metrics import classification_report

from model import improved_unet

# Constants
ISIC2018_data_link = "https://cloudstor.aarnet.edu.au/sender/download.php?token=b66a9288-2f00-4330-82ea-9b8711d27643&files_ids=14200406"
download_directory = os.getcwd() + '\ISIC2018_Task1-2_Training_Data.zip'
num_display_examples = 3
training_split = 0.8
validation_split = 0.1
shuffle = False
shuffle_size = 50

img_height = img_width = 180
batch_size = 32
n_channels = 3


def process_images(file_path, is_mask):
    # Decodes the image at the given file location
    if is_mask:
        image = tf.image.decode_png(tf.io.read_file(file_path), channels=1)
    else:
        image = tf.image.decode_jpeg(tf.io.read_file(file_path), channels=3)
    # Converts the image to float32
    image_converted = tf.image.convert_image_dtype(image, tf.float32)
    # Resizes the image to fit the given dimensions
    image_resized = tf.image.resize(image_converted, size=(img_height, img_width))
    # Normalises input image
    if is_mask:
        image_final = tf.cast(image_resized, tf.float32) / 255.0
    else:
        image_final = image_resized
    return image_final


# Plots images to subplot given position
def plot_images(pic_array, rows, index, original, cols=2):
    title = ['Original Input', 'True Mask']
    for i in range(len(pic_array)):
        plt.subplot(rows, cols, index + 1)
        if index < 2:
            plt.title(title[index])
        if original:
            plt.imshow(mpimg.imread(pic_array[i]))
        else:
            plt.imshow(tf.keras.preprocessing.image.array_to_img(pic_array[i]))
        plt.axis('off')
        index += 1


# Displays a database ds given how many rows
def display(rows, ds, index=0):
    plt.figure(figsize=(5, 5))
    for images, masks in ds.take(rows):
        image, mask = images[0], masks[0]
        plot_images([image, mask], rows, index, False)
        index += 2
    plt.show()


# Displays original images as read into the program
def show_original_images(rows, index=0):
    plt.figure(figsize=(5, 5))
    for i in range(rows):
        image, mask = image_file_list[i], mask_file_list[i]
        plot_images([image, mask], rows, index, True)
        index += 2
    plt.show()


def soft_dice_loss(y_true, y_pred):
    """
    Code adapted from:
    "An overview of semantic image segmentation.", Jeremy Jordan, 2021.
    [Online]. Available: https://www.jeremyjordan.me/semantic-segmentation/. [Accessed: 26-Oct-2021].
    """
    y_true = tf.convert_to_tensor(y_true)
    y_pred = tf.convert_to_tensor(y_pred)

    axes = tuple(range(1, len(y_pred.shape) - 1))
    numerator = 2. * tf.math.reduce_sum(y_pred * y_true, axes)
    denominator = tf.math.reduce_sum(tf.math.square(y_pred) + tf.math.square(y_true), axes)

    return 1 - tf.reduce_mean(numerator / denominator)


# Downloads files if not present
tf.keras.utils.get_file(origin=ISIC2018_data_link, fname=download_directory, extract=True, cache_dir=os.getcwd())
# Segments folders into arrays
image_file_list = list(glob.glob('datasets/ISIC2018_Task1-2_Training_Input_x2/*.jpg'))
mask_file_list = list(glob.glob('datasets/ISIC2018_Task1_Training_GroundTruth_x2/*.png'))

# Show original images and masks
print("Size of Training Pictures: %d\nSize of Segmented Pictures: %d\n"
      % (len(list(image_file_list)), len(list(mask_file_list))))
# Prints the original photos
show_original_images(num_display_examples)
# Creates a dataset that contains all the files
data_dir = os.getcwd() + '/datasets'
files_ds = tf.data.Dataset.from_tensor_slices((image_file_list, mask_file_list))
files_ds = files_ds.map(lambda x, y: (process_images(x, False), process_images(y, True))).batch(1)

# Prints the normalised images and masks
display(num_display_examples, files_ds)

# Shuffles the dataset if specified
if shuffle:
    files_ds = files_ds.shuffle(shuffle_size)

# Calculates the size of each test, train, and validation subset
files_ds_size = len(list(files_ds))
train_ds_size = int(training_split * files_ds_size)
val_ds_size = int(validation_split * files_ds_size)
test_ds_size = files_ds_size - train_ds_size - val_ds_size
# Prints the size of all the subsets
print("Training size: %d" % train_ds_size)
print("Validation size: %d" % val_ds_size)
print("Testing size: %d" % test_ds_size)
# Splits the dataset into test, validate, and train subsets
train_ds = files_ds.take(train_ds_size)
val_ds = files_ds.skip(train_ds_size).take(val_ds_size)
test_ds = files_ds.skip(train_ds_size).skip(val_ds_size)

# Creates the improved UNet model
inputs, outputs = improved_unet(img_height, img_width, n_channels)
model = tf.keras.Model(inputs=[inputs], outputs=[outputs])
# Sets the training parameters for the model
model.compile(optimizer="adam", loss=soft_dice_loss, metrics=["accuracy"])
# Prints a summary of the model compiled
model.summary()
