# frozen_string_literal: true

require_relative '../test_helper'

class LodPresentationTest < Minitest::Test
  def test_level_from_page_name
    assert_equal 300, Geomora::Core::LodPresentation.level_from_page_name('Geomora LOD 300')
  end
end
