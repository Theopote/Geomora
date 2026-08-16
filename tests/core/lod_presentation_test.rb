# frozen_string_literal: true

require_relative '../test_helper'

class LodPresentationTest < Minitest::Test
  def test_level_from_page_name
    assert_equal 300, Geomora::Core::LodPresentation.level_from_page_name('Geomora LOD 300')
  end

  def test_export_tour_html_writes_slideshow
    manifest = [
      { 'order' => 1, 'name' => 'Geomora LOD 100', 'lod_level' => 100 },
      { 'order' => 2, 'name' => 'Geomora LOD 200', 'lod_level' => 200 }
    ]
    model = Object.new
    original = Geomora::Core::LodPresentation.method(:tour_manifest)
    Geomora::Core::LodPresentation.define_singleton_method(:tour_manifest) { |_m| manifest }
    path = File.join(Dir.tmpdir, "geomora_tour_#{Process.pid}.html")
    Geomora::Core::LodPresentation.export_tour_html(model, path, step_seconds: 1.5)
    html = File.read(path)
    assert_includes html, 'Geomora LOD 100'
    assert_includes html, 'setInterval'
  ensure
    Geomora::Core::LodPresentation.define_singleton_method(:tour_manifest, original)
    File.delete(path) if path && File.exist?(path)
  end
end
