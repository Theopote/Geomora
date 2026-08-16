# frozen_string_literal: true

module Geomora
  module Core
    class PerpendicularConstraintSolver
      RIGHT_ANGLE = 90.0
      TOLERANCE_DEG = 1.0

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        validate?(config) || repair?(config)
      end

      def self.validate?(config)
        value = config['perpendicular_constraints'] || config[:perpendicular_constraints]
        value == true || value.to_s == 'true'
      end

      def self.repair?(config)
        value = config['perpendicular_repair'] || config[:perpendicular_repair]
        value == true || value.to_s == 'true'
      end

      def self.apply!(walls, params:, facade_wall: nil)
        config = params['building_elements'] || params[:building_elements] || {}
        return walls unless enabled?(params)

        facade = facade_wall || walls.find { |wall| facade_wall?(wall) }
        partitions = walls.select { |wall| partition_wall?(wall) }
        return walls if facade.nil? || partitions.empty?

        facade_axis = baseline_axis(facade)
        walls.map do |wall|
          next wall unless partition_wall?(wall)

          angle = angle_between(facade_axis, baseline_axis(wall))
          wall = StructuralConstraintSolver.send(:deep_dup_wall, wall)
          needs_repair = repair?(config) && (angle - RIGHT_ANGLE).abs > TOLERANCE_DEG
          wall = repair_partition_alignment(wall, facade_axis) if needs_repair
          repaired_angle = angle_between(facade_axis, baseline_axis(wall))
          semantic = wall['semantic'] || {}
          semantic['perpendicular'] = (repaired_angle - RIGHT_ANGLE).abs <= TOLERANCE_DEG
          semantic['angle_to_facade'] = repaired_angle.round(2)
          semantic['repaired'] = true if needs_repair
          wall['semantic'] = semantic
          wall
        end
      end

      def self.repair_partition_alignment(wall, facade_axis)
        baseline = wall.dig('geometry', 'baseline')
        return wall unless baseline.is_a?(Array) && baseline.length == 2

        if facade_axis[0].abs >= facade_axis[1].abs
          x = (baseline[0][0].to_f + baseline[1][0].to_f) / 2.0
          wall['geometry']['baseline'] = [
            [x, baseline[0][1].to_f, baseline[0][2].to_f],
            [x, baseline[1][1].to_f, baseline[1][2].to_f]
          ]
        else
          y = (baseline[0][1].to_f + baseline[1][1].to_f) / 2.0
          wall['geometry']['baseline'] = [
            [baseline[0][0].to_f, y, baseline[0][2].to_f],
            [baseline[1][0].to_f, y, baseline[1][2].to_f]
          ]
        end
        wall
      end

      def self.facade_wall?(wall)
        semantic = wall['semantic']
        return false unless semantic.is_a?(Hash)

        role = semantic['join_role'] || semantic[:join_role]
        role.to_s == 'facade' || semantic['exterior'] == true
      end

      def self.partition_wall?(wall)
        semantic = wall['semantic']
        semantic.is_a?(Hash) && semantic['partition'] == true
      end

      def self.baseline_axis(wall)
        baseline = wall.dig('geometry', 'baseline')
        return [1, 0] unless baseline.is_a?(Array) && baseline.length == 2

        dx = baseline[1][0].to_f - baseline[0][0].to_f
        dy = baseline[1][1].to_f - baseline[0][1].to_f
        length = Math.sqrt((dx * dx) + (dy * dy))
        return [1, 0] if length.zero?

        [dx / length, dy / length]
      end

      def self.angle_between(a, b)
        dot = (a[0] * b[0]) + (a[1] * b[1])
        dot = [[dot, -1.0].max, 1.0].min
        Math.acos(dot) * (180.0 / Math::PI)
      end
    end
  end
end
