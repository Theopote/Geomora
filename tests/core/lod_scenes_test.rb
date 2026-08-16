# frozen_string_literal: true

require_relative '../test_helper'

class LodScenesTest < Minitest::Test
  def test_preset_levels
    assert_equal 100, Geomora::Core::LodScenes::PRESETS[:lod_100]
    assert_equal 300, Geomora::Core::LodScenes::PRESETS[:lod_300]
  end

  def test_hidden_tags_for_lod_100_preset
    hidden = Geomora::Core::LodVisibility.hidden_tags_for(
      Geomora::Core::LodScenes::PRESETS[:lod_100]
    )
    assert_includes hidden, 'Geomora_Rooms'
  end
end
