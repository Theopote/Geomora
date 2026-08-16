# frozen_string_literal: true

require_relative '../test_helper'

class ConstraintSolverTest < Minitest::Test
  def test_solves_equal_width_constraint
    params = {
      'wall_length' => 10_000,
      'windows' => [
        { 'offset' => 500, 'width' => 1400, 'height' => 1500, 'sill_height' => 900 },
        { 'offset' => 2500, 'width' => 1600, 'height' => 1500, 'sill_height' => 900 }
      ],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 },
      'constraints' => [
        { 'id' => 'c1', 'type' => 'equal_width', 'targets' => %w[w1 w2], 'priority' => 'hard' }
      ]
    }

    result = Geomora::Core::ConstraintSolver.solve(params)
    widths = result['windows'].map { |win| win['width'] }
    assert_equal widths.uniq.length, 1
    assert_includes result['constraint_solution']['constraints_solved'], 'equal_width'
  end
end
