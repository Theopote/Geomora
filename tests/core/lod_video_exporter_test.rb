# frozen_string_literal: true

require_relative '../test_helper'

class LodVideoExporterTest < Minitest::Test
  def test_writes_encode_script_when_ffmpeg_missing
    frames = [
      { 'path' => File.join(Dir.tmpdir, 'lod_frame_001.png') }
    ]
    File.write(frames.first['path'], 'png')
    output = File.join(Dir.tmpdir, "geomora_tour_#{Process.pid}.mp4")
    script = Geomora::Core::LodVideoExporter.write_encode_script(frames, output, format: 'mp4', fps: 0.5)
    assert File.exist?(script)
    content = File.read(script)
    assert_includes content, 'ffmpeg'
    assert_includes content, 'lod_frame_%03d.png'
  ensure
    File.delete(frames.first['path']) if frames && File.exist?(frames.first['path'])
    File.delete(script) if defined?(script) && script && File.exist?(script)
  end
end
