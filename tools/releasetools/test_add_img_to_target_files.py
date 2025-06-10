#
# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import os.path
import tempfile
import zipfile

import common
import test_utils
from add_img_to_target_files import (
    AddPackRadioImages,
    GetCareMap,
    CheckAbOtaImages)
from rangelib import RangeSet


OPTIONS = common.OPTIONS


class AddImagesToTargetFilesTest(test_utils.ReleaseToolsTestCase):

  def setUp(self):
    OPTIONS.input_tmp = common.MakeTempDir()

  @staticmethod
  def _create_images(images, prefix):
    """Creates images under OPTIONS.input_tmp/prefix."""
    path = os.path.join(OPTIONS.input_tmp, prefix)
    if not os.path.exists(path):
      os.mkdir(path)

    for image in images:
      image_path = os.path.join(path, image + '.img')
      with open(image_path, 'wb') as image_fp:
        image_fp.write(image.encode())

    images_path = os.path.join(OPTIONS.input_tmp, 'IMAGES')
    if not os.path.exists(images_path):
      os.mkdir(images_path)
    return images, images_path

  def test_CheckAbOtaImages_imageExistsUnderImages(self):
    """Tests the case with existing images under IMAGES/."""
    images, _ = self._create_images(['aboot', 'xbl'], 'IMAGES')
    CheckAbOtaImages(None, images)

  def test_CheckAbOtaImages_imageExistsUnderRadio(self):
    """Tests the case with some image under RADIO/."""
    images, _ = self._create_images(['system', 'vendor'], 'IMAGES')
    radio_path = os.path.join(OPTIONS.input_tmp, 'RADIO')
    if not os.path.exists(radio_path):
      os.mkdir(radio_path)
    with open(os.path.join(radio_path, 'modem.img'), 'wb') as image_fp:
      image_fp.write('modem'.encode())
    CheckAbOtaImages(None, images + ['modem'])

  def test_CheckAbOtaImages_missingImages(self):
    images, _ = self._create_images(['aboot', 'xbl'], 'RADIO')
    self.assertRaises(
        AssertionError, CheckAbOtaImages, None, images + ['baz'])

  def test_AddPackRadioImages(self):
    images, images_path = self._create_images(['foo', 'bar'], 'RADIO')
    AddPackRadioImages(None, images)

    for image in images:
      self.assertTrue(
          os.path.exists(os.path.join(images_path, image + '.img')))

  def test_AddPackRadioImages_with_suffix(self):
    images, images_path = self._create_images(['foo', 'bar'], 'RADIO')
    images_with_suffix = [image + '.img' for image in images]
    AddPackRadioImages(None, images_with_suffix)

    for image in images:
      self.assertTrue(
          os.path.exists(os.path.join(images_path, image + '.img')))

  def test_AddPackRadioImages_zipOutput(self):
    images, _ = self._create_images(['foo', 'bar'], 'RADIO')

    # Set up the output zip.
    output_file = common.MakeTempFile(suffix='.zip')
    with zipfile.ZipFile(output_file, 'w', allowZip64=True) as output_zip:
      AddPackRadioImages(output_zip, images)

    with zipfile.ZipFile(output_file, 'r', allowZip64=True) as verify_zip:
      for image in images:
        self.assertIn('IMAGES/' + image + '.img', verify_zip.namelist())

  def test_AddPackRadioImages_imageExists(self):
    images, images_path = self._create_images(['foo', 'bar'], 'RADIO')

    # Additionally create images under IMAGES/ so that they should be skipped.
    images, images_path = self._create_images(['foo', 'bar'], 'IMAGES')

    AddPackRadioImages(None, images)

    for image in images:
      self.assertTrue(
          os.path.exists(os.path.join(images_path, image + '.img')))

  def test_AddPackRadioImages_missingImages(self):
    images, _ = self._create_images(['foo', 'bar'], 'RADIO')
    AddPackRadioImages(None, images)

    self.assertRaises(AssertionError, AddPackRadioImages, None,
                      images + ['baz'])


  def test_GetCareMap(self):
    sparse_image = test_utils.construct_sparse_image([
        (0xCAC1, 6),
        (0xCAC3, 4),
        (0xCAC1, 6)], "system")
    name, care_map = GetCareMap('system', sparse_image)
    self.assertEqual('system', name)
    self.assertEqual(RangeSet("0-5 10-15").to_string_raw(), care_map)

  def test_GetCareMap_invalidPartition(self):
    self.assertRaises(AssertionError, GetCareMap, 'oem', None)

  def test_GetCareMap_nonSparseImage(self):
    with tempfile.NamedTemporaryFile() as tmpfile:
      tmpfile.truncate(4096 * 13)
      test_utils.append_avb_footer(tmpfile.name, "system")
      name, care_map = GetCareMap('system', tmpfile.name)
      self.assertEqual('system', name)
      self.assertEqual(RangeSet("0-12").to_string_raw(), care_map)
