# frozen_string_literal: true

require_relative '../test_helper'

class PerpendicularConstraintSolverTest < Minitest::Test
  def test_marks_perpendicular_partitions
    facade = {
      'semantic' => { 'join_role' => 'facade' },
      'geometry' => { 'baseline' => [[0, 0, 0], [9000, 0, 0]] }
    }
    partition = {
      'semantic' => { 'partition' => true },
      'geometry' => { 'baseline' => [[4500, 120, 0], [4500, 2880, 0]] }
    }
    params = { 'building_elements' => { 'perpendicular_constraints' => true } }

    result = Geomora::Core::PerpendicularConstraintSolver.apply!(
      [partition],
      params: params,
      facade_wall: facade
    )

    assert_equal true, result[0]['semantic']['perpendicular']
    assert_in_delta 90.0, result[0]['semantic']['angle_to_facade'], 0.1
  end

  def test_repairs_skewed_partitions
    facade = {
      'semantic' => { 'join_role' => 'facade' },
      'geometry' => { 'baseline' => [[0, 0, 0], [9000, 0, 0]] }
    }
    partition = {
      'semantic' => { 'partition' => true },
      'geometry' => { 'baseline' => [[2000, 500, 0], [6000, 2500, 0]] }
    }
    params = { 'building_elements' => { 'perpendicular_repair' => true } }

    result = Geomora::Core::PerpendicularConstraintSolver.apply!(
      [partition],
      params: params,
      facade_wall: facade
    )

    baseline = result[0]['geometry']['baseline']
    assert_in_delta baseline[0][0], baseline[1][0], 0.1
    assert_equal true, result[0]['semantic']['perpendicular']
    assert_equal true, result[0]['semantic']['repaired']
  end
end
