# frozen_string_literal: true

require_relative '../test_helper'

class LodCaptureTest < Minitest::Test
  def test_capture_pages_writes_frame_files
    page = Struct.new(:name).new('Geomora LOD 100')
    model = Object.new
    model.define_singleton_method(:pages) { [page] }
    model.define_singleton_method(:active_view) { nil }

    original_pages = Geomora::Core::LodPresentation.method(:geomora_pages)
    Geomora::Core::LodPresentation.define_singleton_method(:geomora_pages) { |_m| [page] }
    frames = Geomora::Core::LodCapture.capture_pages(model)
    assert_equal 1, frames.length
    assert File.exist?(frames.first['path'])
  ensure
    Geomora::Core::LodPresentation.define_singleton_method(:geomora_pages, original_pages)
    frames&.each do |frame|
      File.delete(frame['path']) if frame['path'] && File.exist?(frame['path'])
    end
  end
end
