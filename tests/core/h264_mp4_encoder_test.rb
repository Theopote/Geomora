# frozen_string_literal: true

require_relative '../test_helper'

class H264Mp4EncoderTest < Minitest::Test
  def test_writes_h264_mp4
    frames = [Geomora::Core::LodCapture.placeholder_rgb(32, 32)]
    path = File.join(Dir.tmpdir, "geomora_h264_#{Process.pid}.mp4")
    Geomora::Core::H264Mp4Encoder.encode(frames, path, fps: 1.0)
    header = File.binread(path, 8)
    assert_equal 'ftyp', header[4, 4]
    assert_operator File.size(path), :>, 200
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
