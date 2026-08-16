# frozen_string_literal: true

require_relative '../test_helper'

class StructuralConstraintSolverTest < Minitest::Test
  def test_snaps_partition_wall_to_grid
    walls = [
      {
        'id' => 'partition_01_01',
        'semantic' => { 'partition' => true },
        'geometry' => {
          'baseline' => [[4520, 120, 0], [4520, 2880, 0]],
          'height' => 3000,
          'thickness' => 240
        }
      }
    ]
    params = {
      'building_elements' => { 'structural_constraints' => true },
      'partition_grid_spacing' => 300
    }

    result = Geomora::Core::StructuralConstraintSolver.apply!(walls, params: params)
    x = result[0]['geometry']['baseline'][0][0]
    assert_equal 4500, x
    assert_equal true, result[0]['semantic']['parallel']
  end
end
