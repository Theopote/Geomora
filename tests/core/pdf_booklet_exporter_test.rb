# frozen_string_literal: true

require_relative '../test_helper'

class PdfBookletExporterTest < Minitest::Test
  def test_exports_booklet_pdf
    params = {
      'wall_length' => 9000,
      'building_depth' => 6000,
      'partition_count' => 1
    }
    path = File.join(Dir.tmpdir, "geomora_booklet_#{Process.pid}.pdf")
    Geomora::Core::PdfReportExporter.export_booklet(params, path)
    header = File.read(path, 8)
    assert_equal '%PDF-1.4', header
    assert_operator File.read(path).scan('/Type /Page').length, :>=, 2
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
