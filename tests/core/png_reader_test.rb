# frozen_string_literal: true

require_relative '../test_helper'

class PngReaderTest < Minitest::Test
  def test_reads_placeholder_png_rgb
    path = File.join(Dir.tmpdir, "geomora_png_#{Process.pid}.png")
    Geomora::Core::LodCapture.write_placeholder_png(path, width: 2, height: 2)
    data = Geomora::Core::PngReader.read_rgb(path)
    assert_equal 2, data['width']
    assert_equal 2, data['height']
    assert_equal 12, data['rgb'].bytesize
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
