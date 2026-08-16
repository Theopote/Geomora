# frozen_string_literal: true

require_relative '../test_helper'

class Mp4EncoderTest < Minitest::Test
  def test_writes_mp4_header
    frames = [Geomora::Core::LodCapture.placeholder_rgb(16, 16)]
    path = File.join(Dir.tmpdir, "geomora_test_#{Process.pid}.mp4")
    Geomora::Core::Mp4Encoder.encode(frames, path, fps: 1.0)
    header = File.binread(path, 8)
    assert_equal 'ftyp', header[4, 4]
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
