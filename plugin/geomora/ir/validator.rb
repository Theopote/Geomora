# frozen_string_literal: true

require_relative '../geometry/units'

module Geomora
  module IR
    class Validator
      SUPPORTED_SCHEMA_VERSIONS = [Geomora::SCHEMA_VERSION].freeze
      SUPPORTED_CONSTRAINT_TYPES = %w[
        parallel perpendicular coplanar horizontal vertical
        equal_width equal_height equal_spacing symmetry align
        fixed_dimension grid
      ].freeze

      def self.validate(document)
        new(document).validate
      end

      def initialize(document)
        @doc = document
        @errors = []
      end

      def validate
        validate_schema_version
        validate_project
        collect_entity_ids
        validate_buildings
        validate_openings
        validate_constraints
        validate_components

        raise IRValidationError, @errors.join("\n") unless @errors.empty?

        Logger.info('Validation complete')
        true
      end

      private

      def collect_entity_ids
        @ids = {}
        register_id(@doc.project.id, 'project')

        @doc.buildings.each { |b| register_id(b.id, 'building') }
        @doc.buildings.flat_map(&:storeys).each { |s| register_id(s.id, 'storey') }
        @doc.buildings.flat_map(&:storeys).flat_map(&:elements).each do |e|
          register_id(e.id, e.type)
        end
        @doc.openings.each { |o| register_id(o.id, o.type) }
        @doc.components.each { |c| register_id(c.id, 'component') }
        @doc.constraints.each { |c| register_id(c.id, 'constraint') }
        @doc.sources.each { |s| register_id(s.id, 'source') }
      end

      def register_id(id, type)
        if @ids.key?(id)
          @errors << "Duplicate entity ID: #{id}"
        else
          @ids[id] = type
        end
      end

      def validate_schema_version
        unless SUPPORTED_SCHEMA_VERSIONS.include?(@doc.schema_version)
          @errors << "Unsupported schema version: #{@doc.schema_version}"
        end
      end

      def validate_project
        p = @doc.project
        @errors << 'Missing required field: project.id' if p.id.nil? || p.id.empty?
        @errors << 'Missing required field: project.name' if p.name.nil? || p.name.empty?
        @errors << 'Missing required field: project.unit' if p.unit.nil? || p.unit.empty?

        unless Geometry::Units::SUPPORTED_UNITS.include?(p.unit)
          @errors << "Unsupported unit: #{p.unit}"
        end
      end

      def validate_buildings
        @doc.buildings.each do |building|
          validate_storey_stack(building)
          validate_storeys(building)
        end
      end

      def validate_storey_stack(building)
        storeys = building.storeys
        return if storeys.empty?

        expected_elevation = 0.0
        storeys.each do |storey|
          elevation = storey.elevation.to_f
          if elevation != expected_elevation
            @errors << "Storey elevation mismatch for #{storey.id}: expected #{expected_elevation}, got #{elevation}"
          end
          expected_elevation += storey.height.to_f
        end
      end

      def validate_storeys(building)
        building.storeys.each do |storey|
          @errors << "Negative storey height: #{storey.id}" if storey.height.to_f.negative?

          storey.elements.each do |element|
            case element.type
            when 'wall'
              validate_wall(element, storey)
            when 'floor', 'roof'
              validate_polygon_element(element, storey)
            when 'column'
              validate_column(element, storey)
            when 'beam'
              validate_beam(element, storey)
            when 'stair'
              validate_stair(element, storey)
            when 'balcony'
              validate_balcony(element, storey)
            when 'parapet'
              validate_parapet(element, storey)
            when 'cornice'
              validate_cornice(element, storey)
            else
              @errors << "Unsupported element type: #{element.type}"
            end
          end
        end
      end

      def validate_wall(wall, storey)
        unless @ids[wall.storey_id]
          @errors << "Invalid storey_id for #{wall.id}: #{wall.storey_id}"
        end

        bl = wall.baseline
        if bl.nil? || bl.length != 2
          @errors << "Invalid baseline for #{wall.id}"
          return
        end

        length = wall.length
        @errors << "Zero-length wall baseline: #{wall.id}" if length.zero?

        %i[height thickness].each do |dim|
          val = wall.geometry[dim]
          @errors << "Negative #{dim} on #{wall.id}" if val.to_f.negative?
          @errors << "Zero #{dim} on #{wall.id}" if val.to_f.zero?
        end

        validate_wall_openings(wall, storey)
      end

      def validate_openings
        @doc.openings.each do |opening|
          unless @ids[opening.parent_id]
            @errors << "Invalid parent_id for #{opening.id}: #{opening.parent_id}"
            next
          end

          parent_type = @ids[opening.parent_id]
          unless parent_type == 'wall'
            @errors << "Invalid parent_id for #{opening.id}: parent must be a wall"
          end

          validate_opening_dimensions(opening)
        end
      end

      def validate_wall_openings(wall, _storey)
        openings = @doc.openings.select { |o| wall.opening_ids.include?(o.id) }

        wall.opening_ids.each do |oid|
          unless @ids[oid]
            @errors << "Invalid opening reference on #{wall.id}: #{oid}"
          end
        end

        wall_length = wall.length
        wall_height = wall.height.to_f

        openings.each do |opening|
          validate_opening_in_wall(opening, wall, wall_length, wall_height)
        end

        validate_opening_overlaps(openings, wall.id)
      end

      def validate_opening_dimensions(opening)
        %i[width height depth].each do |dim|
          val = opening.geometry[dim]
          next if val.nil?

          @errors << "Negative #{dim} on #{opening.id}" if val.to_f.negative?
          @errors << "Zero #{dim} on #{opening.id}" if val.to_f.zero?
        end
      end

      def validate_opening_in_wall(opening, wall, wall_length, wall_height)
        offset = opening.offset.to_f
        width = opening.width.to_f
        height = opening.height.to_f
        sill = opening.sill_height.to_f

        if offset.negative?
          @errors << "#{opening.id} has negative offset on #{wall.id}"
        end

        if offset + width > wall_length
          @errors << "#{opening.id} exceeds bounds of #{wall.id}"
        end

        top = sill + height
        if top > wall_height
          @errors << "#{opening.id} height exceeds wall #{wall.id}"
        end

        if sill.negative?
          @errors << "#{opening.id} has negative sill_height on #{wall.id}"
        end
      end

      def validate_opening_overlaps(openings, wall_id)
        openings.combination(2).each do |a, b|
          next unless openings_overlap?(a, b)

          @errors << "Opening overlap on #{wall_id}: #{a.id} and #{b.id}"
        end
      end

      def openings_overlap?(a, b)
        a_left = a.offset.to_f
        a_right = a_left + a.width.to_f
        b_left = b.offset.to_f
        b_right = b_left + b.width.to_f
        horizontal = a_left < b_right && b_left < a_right
        return false unless horizontal

        a_bottom = a.sill_height.to_f
        a_top = a_bottom + a.height.to_f
        b_bottom = b.sill_height.to_f
        b_top = b_bottom + b.height.to_f
        a_bottom < b_top && b_bottom < a_top
      end

      def validate_constraints
        @doc.constraints.each do |constraint|
          unless SUPPORTED_CONSTRAINT_TYPES.include?(constraint.type)
            @errors << "Unsupported constraint type: #{constraint.type}"
          end

          constraint.targets.each do |target|
            unless @ids[target]
              @errors << "Invalid constraint target in #{constraint.id}: #{target}"
            end
          end
        end
      end

      def validate_components
        @doc.components.each do |comp|
          @errors << "Missing component type: #{comp.id}" if comp.type.nil?
        end
      end

      def validate_polygon_element(element, storey)
        validate_storey_reference(element, storey)
        polygon = element.geometry[:polygon]
        @errors << "Invalid polygon for #{element.id}" if polygon.nil? || polygon.length < 3
        thickness = element.geometry[:thickness]
        @errors << "Zero thickness on #{element.id}" if thickness.to_f.zero?
      end

      def validate_column(element, storey)
        validate_storey_reference(element, storey)
        %i[width depth height].each do |dim|
          val = element.geometry[dim]
          @errors << "Zero #{dim} on #{element.id}" if val.to_f.zero?
        end
      end

      def validate_beam(element, storey)
        validate_storey_reference(element, storey)
        baseline = element.geometry[:baseline]
        @errors << "Invalid baseline for #{element.id}" if baseline.nil? || baseline.length != 2
        %i[width height].each do |dim|
          val = element.geometry[dim]
          @errors << "Zero #{dim} on #{element.id}" if val.to_f.zero?
        end
      end

      def validate_stair(element, storey)
        validate_storey_reference(element, storey)
        %i[width run rise steps].each do |dim|
          val = element.geometry[dim]
          @errors << "Zero #{dim} on #{element.id}" if val.to_f.zero?
        end
      end

      def validate_balcony(element, storey)
        validate_storey_reference(element, storey)
        %i[width depth thickness].each do |dim|
          val = element.geometry[dim]
          @errors << "Zero #{dim} on #{element.id}" if val.to_f.zero?
        end
      end

      def validate_parapet(element, storey)
        validate_storey_reference(element, storey)
        baseline = element.geometry[:baseline]
        @errors << "Invalid baseline for #{element.id}" if baseline.nil? || baseline.length != 2
        %i[height thickness].each do |dim|
          val = element.geometry[dim]
          @errors << "Zero #{dim} on #{element.id}" if val.to_f.zero?
        end
      end

      def validate_cornice(element, storey)
        validate_storey_reference(element, storey)
        baseline = element.geometry[:baseline]
        @errors << "Invalid baseline for #{element.id}" if baseline.nil? || baseline.length != 2
        %i[width height projection].each do |dim|
          val = element.geometry[dim]
          @errors << "Zero #{dim} on #{element.id}" if val.to_f.zero?
        end
      end

      def validate_storey_reference(element, storey)
        unless @ids[element.storey_id]
          @errors << "Invalid storey_id for #{element.id}: #{element.storey_id}"
        end
        return if element.storey_id == storey.id

        @errors << "Element #{element.id} storey_id does not match parent storey"
      end
    end
  end
end
