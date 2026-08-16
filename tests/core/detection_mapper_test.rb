# frozen_string_literal: true

require_relative '../test_helper'

class DetectionMapperTest < Minitest::Test
  def detection(elements)
    Struct.new(:elements).new(elements)
  end

  def test_filters_low_confidence_and_tiny_boxes
    result = Geomora::Core::DetectionMapper.to_facade_params(
      detection([
        {
          'type' => 'door',
          'confidence' => 0.26,
          'bbox_norm' => [0.4, 0.5, 0.43, 0.6]
        },
        {
          'type' => 'window',
          'confidence' => 0.8,
          'bbox_norm' => [0.1, 0.2, 0.25, 0.55]
        }
      ]),
      wall_length: 10_000,
      wall_height: 3300,
      wall_thickness: 240
    )

    assert_equal 1, result['windows'].length
    assert_equal 0, result['door']['width']
  end
end
