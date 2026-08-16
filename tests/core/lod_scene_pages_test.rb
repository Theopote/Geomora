# frozen_string_literal: true

require_relative '../test_helper'

class LodScenePagesTest < Minitest::Test
  def test_page_names
    names = Geomora::Core::LodScenePages.page_names
    assert_equal 3, names.length
    assert_includes names, 'Geomora LOD 200'
  end

  def test_page_name_for_level
    assert_equal 'Geomora LOD 300', Geomora::Core::LodScenePages.page_name_for(300)
  end
end
