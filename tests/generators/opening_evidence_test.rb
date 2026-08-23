# frozen_string_literal: true

require_relative '../test_helper'
require File.join(PLUGIN, 'generators', 'storey_generator')

class OpeningEvidenceTest < Minitest::Test
  def test_matches_architect_review_to_generated_opening
    opening = Geomora::IR::Models::Opening.new(
      id: 'window_01_01', type: 'window', parent_id: 'wall_01_01',
      geometry: {}, confidence: 0.62,
      source: { 'type' => 'auto_fusion_v1', 'opening_index' => 0 }
    )
    document = Struct.new(:reconstruction).new(
      {
        'uncertainty_review' => {
          'decisions' => [
            {
              'decision' => 'manual_edit', 'opening_id' => 'pred_001',
              'model_opening_index' => 0, 'reviewer' => 'sketchup_user',
              'reviewed_at' => '2026-08-23T12:00:00Z'
            }
          ]
        }
      }
    )

    evidence = Geomora::Generators::StoreyGenerator.allocate.send(:opening_evidence, opening, document)

    assert_equal 'auto_fusion_v1', evidence[:source]
    assert_in_delta 0.62, evidence[:confidence]
    assert_equal 'manual_edit', evidence[:decision]
    assert_equal 'pred_001', evidence[:evidence_opening_id]
  end
end
