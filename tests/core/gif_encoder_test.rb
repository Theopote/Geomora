# frozen_string_literal: true

require_relative '../test_helper'

class GifEncoderTest < Minitest::Test
  def test_writes_gif_magic_bytes
    frames = [
      Geomora::Core::LodCapture.placeholder_rgb(8, 8),
      Geomora::Core::LodCapture.placeholder_rgb(8, 8)
    ]
    path = File.join(Dir.tmpdir, "geomora_test_#{Process.pid}.gif")
    Geomora::Core::GifEncoder.encode(frames, path, delay_centiseconds: 10)
    header = File.binread(path, 6)
    assert_equal 'GIF89a', header
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
