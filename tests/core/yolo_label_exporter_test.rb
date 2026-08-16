# frozen_string_literal: true

require_relative '../test_helper'

class YoloLabelExporterTest < Minitest::Test
  def test_bbox_norm_to_yolo_line
    line = Geomora::Core::YoloLabelExporter.bbox_norm_to_yolo_line(
      0,
      [0.10, 0.23, 0.25, 0.53]
    )
    assert_equal '0 0.175000 0.380000 0.150000 0.300000', line
  end

  def test_build_lines_includes_door
    lines = Geomora::Core::YoloLabelExporter.build_lines(
      windows: [{ 'bbox_norm' => [0.10, 0.23, 0.25, 0.53] }],
      door_bbox: [0.01, 0.55, 0.09, 0.93]
    )
    assert_equal 2, lines.length
    assert lines[0].start_with?('0 ')
    assert lines[1].start_with?('1 ')
  end

  def test_export_writes_image_and_label
    rectified = File.join(Dir.mktmpdir, 'rectified.jpg')
    File.write(rectified, 'jpeg-bytes')

    dataset_root = File.join(Dir.mktmpdir, 'dataset')
    result = Geomora::Core::YoloLabelExporter.export!(
      rectified_path: rectified,
      dataset_root: dataset_root,
      split: 'train',
      windows: [{ 'bbox_norm' => [0.10, 0.23, 0.25, 0.53] }],
      door_bbox: [0.01, 0.55, 0.09, 0.93],
      stem: 'sample_001'
    )

    assert_equal 2, result.box_count
    assert File.exist?(result.image_path)
    assert File.exist?(result.label_path)
    assert_includes File.read(result.label_path), '0 0.175000'
    assert_includes File.read(result.label_path), '1 '
  end
end
