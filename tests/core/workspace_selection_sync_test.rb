# frozen_string_literal: true

require_relative '../test_helper'
require File.join(PLUGIN, 'core', 'workspace_selection_sync')

class WorkspaceSelectionSyncTest < Minitest::Test
  FakeEntity = Struct.new(:children) do
    def initialize(children = nil)
      super(children)
      @attributes = {}
    end

    def set_attribute(dictionary, key, value)
      @attributes[[dictionary, key]] = value
    end

    def get_attribute(dictionary, key)
      @attributes[[dictionary, key]]
    end

    def entities
      children
    end
  end

  class FakeSelection
    attr_reader :observer, :items

    def initialize(items = [])
      @items = items
    end

    def add_observer(observer); @observer = observer; end
    def remove_observer(_observer); @observer = nil; end
    def to_a; @items; end
    def clear; @items.clear; end
    def add(entity); @items << entity; end
  end

  FakeModel = Struct.new(:entities, :selection)
  FakeDialog = Struct.new(:scripts) do
    def execute_script(script); scripts << script; end
  end

  def teardown
    Geomora::Core::WorkspaceSelectionSync.stop
  end

  def test_pushes_geomora_entity_evidence_and_selects_by_id
    entity = FakeEntity.new
    Geomora::Metadata::Attributes.write(entity, entity_id: 'window_01_01', entity_type: 'window', ai_source: 'auto')
    selection = FakeSelection.new([entity])
    model = FakeModel.new([entity], selection)
    dialog = FakeDialog.new([])

    assert Geomora::Core::WorkspaceSelectionSync.start(dialog, model: model)
    assert_includes dialog.scripts.last, 'window_01_01'

    selection.clear
    assert Geomora::Core::WorkspaceSelectionSync.select_entity('window_01_01', model: model)
    assert_equal [entity], selection.items
  end
end
