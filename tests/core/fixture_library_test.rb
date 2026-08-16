# frozen_string_literal: true

require_relative '../test_helper'

class FixtureLibraryTest < Minitest::Test
  def test_kitchen_set_includes_fixtures
    items = Geomora::Core::FixtureLibrary.items_for('kitchen')
    kinds = items.map { |item| item[:kind] }
    assert_includes kinds, 'sink'
    assert_includes kinds, 'stove'
    assert_includes kinds, 'fridge'
  end

  def test_bathroom_set_includes_fixtures
    items = Geomora::Core::FixtureLibrary.items_for('bathroom')
    kinds = items.map { |item| item[:kind] }
    assert_includes kinds, 'toilet'
    assert_includes kinds, 'shower'
  end
end
