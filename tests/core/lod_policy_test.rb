# frozen_string_literal: true

require_relative '../test_helper'

class LodPolicyTest < Minitest::Test
  def test_lod_100_skips_openings_and_details
    assert_equal false, Geomora::Core::LodPolicy.include_openings?(100)
    assert_equal false, Geomora::Core::LodPolicy.include_element?('cornice', 100)
    assert_equal true, Geomora::Core::LodPolicy.include_element?('wall', 100)
  end

  def test_lod_200_includes_openings
    assert_equal true, Geomora::Core::LodPolicy.include_openings?(200)
    assert_equal true, Geomora::Core::LodPolicy.include_element?('window', 200)
    assert_equal false, Geomora::Core::LodPolicy.include_element?('trim', 200)
  end

  def test_lod_300_includes_details
    assert_equal true, Geomora::Core::LodPolicy.include_element?('trim', 300)
    assert_equal true, Geomora::Core::LodPolicy.include_element?('eaves', 300)
  end

  def test_lod_300_includes_furniture
    assert_equal true, Geomora::Core::LodPolicy.include_element?('furniture', 300)
    assert_equal true, Geomora::Core::LodPolicy.include_element?('fixture', 300)
    assert_equal false, Geomora::Core::LodPolicy.include_element?('furniture', 200)
  end
end
