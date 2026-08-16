# frozen_string_literal: true

require_relative '../test_helper'

class ScaleEstimatorTest < Minitest::Test
  def test_estimates_from_door_bbox
    elements = [
      {
        'type' => 'door',
        'bbox_norm' => [0.05, 0.55, 0.12, 0.92],
        'confidence' => 0.9
      }
    ]
    hint = Geomora::Core::ScaleEstimator.from_detection(elements, image_width: 800, image_height: 600)
    assert hint
    assert_operator hint['wall_height_mm'], :>, 2000
    assert_operator hint['wall_length_mm'], :>, 3000
  end

  def test_apply_hint_updates_params
    params = { 'wall_length' => 10000, 'wall_height' => 3300 }
    hint = { 'wall_length_mm' => 12000, 'wall_height_mm' => 3600, 'confidence' => 0.8 }
    updated = Geomora::Core::ScaleEstimator.apply_hint!(params, hint)
    assert_equal 12000, updated['wall_length']
    assert_equal 3600, updated['wall_height']
  end
end
