# frozen_string_literal: true

require_relative '../test_helper'

class LodVisibilityTest < Minitest::Test
  def test_lod_100_hides_openings_and_details
    hidden = Geomora::Core::LodVisibility.hidden_tags_for(100)
    assert_includes hidden, 'Geomora_Windows'
    assert_includes hidden, 'Geomora_Trim'
    assert_includes hidden, 'Geomora_InteriorWalls'
    refute_includes hidden, 'Geomora_Walls'
  end

  def test_lod_200_shows_openings_hides_details
    hidden = Geomora::Core::LodVisibility.hidden_tags_for(200)
    visible = Geomora::Core::LodVisibility.visible_tags_for(200)

    assert_includes visible, 'Geomora_Windows'
    assert_includes visible, 'Geomora_InteriorWalls'
    assert_includes visible, 'Geomora_Rooms'
    assert_includes hidden, 'Geomora_Trim'
    assert_includes hidden, 'Geomora_Eaves'
  end

  def test_lod_300_shows_all_geomora_tags
    hidden = Geomora::Core::LodVisibility.hidden_tags_for(300)
    assert_equal [], hidden
  end
end
