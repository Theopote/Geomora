# frozen_string_literal: true

require_relative '../test_helper'

class MetadataTest < Minitest::Test
  def setup
    @entity = FakeEntity.new
  end

  def test_write_and_read
    Geomora::Metadata::Attributes.write(@entity, {
      entity_id: 'wall_001',
      entity_type: 'wall',
      schema_version: '0.1',
      project_id: 'project_001'
    })

    assert_equal 'wall_001', Geomora::Metadata::Attributes.read(@entity, 'entity_id')
    assert_equal 'wall', Geomora::Metadata::Attributes.read(@entity, 'entity_type')
    assert Geomora::Metadata::Attributes.geomora_entity?(@entity)
    assert_equal 'project_001', Geomora::Metadata::Attributes.project_id(@entity)
  end

  class FakeEntity
    def initialize
      @attrs = {}
    end

    def set_attribute(dict, key, value)
      @attrs["#{dict}.#{key}"] = value
    end

    def get_attribute(dict, key)
      @attrs["#{dict}.#{key}"]
    end
  end
end
