# Python 3.4
import sys
sys.path.append("/usr/local/lib/python3.4/site-packages/")
import cv2 as cv2
from os import listdir
from os.path import isfile, join
from os import walk
from shutil import copy
import numpy as np
import tensorflow as tf


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

def _int64_nparray(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value))

def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

# to get HAB and pOrig
def _float_nparray(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))

def _decode_byte_string(filename):
    """Decode and preprocess one filename.
    Args:
      filename: Binary string Tensor
    Returns:
      String Tensor containing the image in float32
    """
    tfname = tf.decode_raw(filename, tf.uint8)
    return tfname

def _decode_byte_image(image, height, width, depth):
    """Decode and preprocess one image for evaluation or training.
    Args:
      imageBuffer: Binary string Tensor
      Height, Widath, Channels <----- GLOBAL VARIABLES ARE USED DUE TO SET_SHAPE REQUIREMENTS
    Returns:
      3-D float Tensor containing the image in float32
    """
    image = tf.decode_raw(image, tf.uint8)
    image = tf.cast(image, dtype=tf.float32)
    image = tf.reshape(image, [height, width, depth])
    image.set_shape([height, width, depth])
    return image

def parse_example_proto(exampleSerialized, **kwargs):
    """Parses an Example proto containing a training example of an image.
    The output of the preprocessing script is a dataset
    containing serialized Example protocol buffers. Each Example proto contains
    the following fields:
        height: 128
        width: 128
        channels: 2  -> 2 images stacked
        HAB: [8]
        pOrig: [8]
        image/encoded: <bytes encoded string>

        'height': _int64_feature(rows),
        'width': _int64_feature(cols),
        'depth': _int64_feature(depth),
        'pOrig': _float_nparray(pOrigList),
        'HAB': _float_nparray(HABList), # 2D np array
        'image': _bytes_feature(flatImageList)

    Args:
        exampleSerialized: scalar Tensor tf.string containing a serialized
        Example protocol buffer.
    Returns:
      imageBuffer: Tensor tf.string containing the contents of a JPEG file.
      HAB: Tensor tf.int32 containing the homography.
      pOrig: Tensor tf.int32 contating the origianl square points
    """
    
    featureMap ={
        'fileID': tf.FixedLenFeature([2], dtype=tf.int64),
        'height': tf.FixedLenFeature([1], dtype=tf.int64),
        'width': tf.FixedLenFeature([1], dtype=tf.int64),
        'depth': tf.FixedLenFeature([1], dtype=tf.int64),
        'HAB': tf.FixedLenFeature([8], dtype=tf.float32),
        'image': tf.FixedLenFeature([], dtype=tf.string, default_value='')}

    features = tf.parse_single_example(exampleSerialized, featureMap)

    filename = _decode_byte_string(features['filename'])
    image = _decode_byte_image(features['image'], kwargs.get('imageHeight'), kwargs.get('imageWidth'), kwargs.get('imageChannels'))
    HAB = features['HAB']

    #validate_for_nan()

    return image, HAB, filename

def tfrecord_writer(imgPatchOrig, imgPatchPert, HAB, tfRecordFolder, tfFileName, fileID):
    """Converts a dataset to tfrecords."""
    #images = data_set.images
    #labels = data_set.labels
    #num_examples = data_set.num_examples
    tfRecordPath = tfRecordFolder + tfFileName

    rows = imgPatchOrig.shape[0]
    cols = imgPatchOrig.shape[1]
    depth = 2
    #OLD
    stackedImage = np.stack((imgPatchOrig, imgPatchPert), axis=2) #3D array (hieght, width, channels)
    flatImage = stackedImage.reshape(rows*cols*depth)
    #Stack Images
    #stackedImage = np.array([imgPatchOrig.reshape(imgPatchOrig.shape[0]*imgPatchOrig.shape[1]),
    #                imgPatchPert.reshape(imgPatchPert.shape[0]*imgPatchPert.shape[1])])
    #flatImage = stackedImage.reshape(stackedImage.shape[0]*stackedImage.shape[1])
    
    flatImageList = flatImage.tostring()

    HABRow = np.asarray([HAB[0][0], HAB[0][1], HAB[0][2], HAB[0][3],
                         HAB[1][0], HAB[1][1], HAB[1][2], HAB[1][3]], np.float32)
    HABList = HABRow.tolist()
    
    #print('Writing', filename)
    writer = tf.python_io.TFRecordWriter(tfRecordPath)
    example = tf.train.Example(features=tf.train.Features(feature={
        'fileID': _int64_nparray(fileID),
        'height': _int64_feature(rows),
        'width': _int64_feature(cols),
        'depth': _int64_feature(depth),
        'HAB': _float_nparray(HABList), # 2D np array
        'image': _bytes_feature(flatImageList)
        }))
    writer.write(example.SerializeToString())
    writer.close()

