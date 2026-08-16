# frozen_string_literal: true

require_relative '../test_helper'

class JpegFrameEncoderTest < Minitest::Test
  def test_writes_jpeg_magic
    rgb = Geomora::Core::LodCapture.placeholder_rgb(16, 16)['rgb']
    bytes = Geomora::Core::JpegFrameEncoder.encode_rgb(rgb, 16, 16)
    assert_equal "\xFF\xD8", bytes[0, 2]
  end
end
