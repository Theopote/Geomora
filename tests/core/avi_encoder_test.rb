# frozen_string_literal: true

require_relative '../test_helper'

class AviEncoderTest < Minitest::Test
  def test_writes_avi_header
    frames = [
      Geomora::Core::LodCapture.placeholder_rgb(8, 8),
      Geomora::Core::LodCapture.placeholder_rgb(8, 8)
    ]
    path = File.join(Dir.tmpdir, "geomora_test_#{Process.pid}.avi")
    Geomora::Core::AviEncoder.encode(frames, path, fps: 1.0)
    header = File.binread(path, 12)
    assert_equal 'RIFF', header[0, 4]
    assert_equal 'AVI ', header[8, 4]
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
