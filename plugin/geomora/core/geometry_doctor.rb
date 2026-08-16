# frozen_string_literal: true

require_relative '../geometry/units'
require_relative '../metadata/attributes'
require_relative '../transactions/operation'

module Geomora
  module Core
  module GeometryDoctor
    DEFAULT_TINY_EDGE_MM = 1.0
    DEFAULT_TINY_FACE_MM2 = 100.0
    DEFAULT_VERTEX_TOLERANCE_MM = 0.5
    DEFAULT_GRID_MM = 10.0

    module Helpers
      INCHES_PER_MM = 1.0 / 25.4
      SQ_INCHES_PER_SQ_MM = INCHES_PER_MM**2

      def self.snap_coord(value, grid_length)
        return value if grid_length.zero?

        (value / grid_length).round * grid_length
      end

      def self.length_to_mm(length)
        length.to_f * 25.4
      end

      def self.area_to_mm2(area)
        area.to_f * (25.4**2)
      end

      def self.round_mm(mm, tolerance_mm)
        (mm / tolerance_mm).round * tolerance_mm
      end

      def self.plane_key(normal, point, tolerance_mm: DEFAULT_VERTEX_TOLERANCE_MM)
        n = normalize_vector(normal)
        d = dot(n, point)
        [
          round_mm(n[0], tolerance_mm),
          round_mm(n[1], tolerance_mm),
          round_mm(n[2], tolerance_mm),
          round_mm(d, tolerance_mm)
        ]
      end

      def self.vertex_key(point, tolerance_mm: DEFAULT_VERTEX_TOLERANCE_MM)
        [
          round_mm(point[0], tolerance_mm),
          round_mm(point[1], tolerance_mm),
          round_mm(point[2], tolerance_mm)
        ]
      end

      def self.face_vertex_signature(vertices, tolerance_mm: DEFAULT_VERTEX_TOLERANCE_MM)
        keys = vertices.map { |v| vertex_key(v, tolerance_mm: tolerance_mm) }
        keys.sort.join('|')
      end

      def self.normalize_vector(v)
        len = Math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
        return [0.0, 0.0, 0.0] if len.zero?

        [v[0] / len, v[1] / len, v[2] / len]
      end

      def self.dot(a, b)
        a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
      end

      def self.empty_report
        {
          'tiny_edges_removed' => 0,
          'tiny_faces_removed' => 0,
          'coplanar_edges_merged' => 0,
          'duplicate_faces_removed' => 0,
          'duplicate_instances_removed' => 0,
          'normals_reversed' => 0,
          'vertices_snapped' => 0,
          'empty_groups_removed' => 0,
          'opening_gaps_found' => 0,
          'components' => {},
          'issues_before' => {},
          'issues_after' => {}
        }
      end

      def self.merge_report(report, delta)
        delta.each do |key, value|
          if key == 'components'
            report[key].merge!(value) { |_k, a, b| a + b }
          elsif key.end_with?('_found') || key.end_with?('_removed') || key.end_with?('_merged') ||
                key.end_with?('_reversed') || key.end_with?('_snapped')
            report[key] += value
          end
        end
        report
      end
    end

    class << self
      def audit(model: Sketchup.active_model, options: {})
        GeometryDoctorRunner.new(model, options).audit
      end

      def repair(model: Sketchup.active_model, options: {})
        Transactions::Operation.run('Geomora Geometry Doctor', model) do
          GeometryDoctorRunner.new(model, options).repair
        end
      end
    end

    class GeometryDoctorRunner
      extend Helpers

      def initialize(model, options = {})
        @model = model
        opts = options.is_a?(Hash) ? options : {}
        @project_id = opts['project_id'] || opts[:project_id]
        @options = normalize_options(opts['geometry_doctor'] || opts)
        @report = empty_report
      end

      def audit
        @repair_mode = false
        scan_project_containers
        @report
      end

      def repair
        @repair_mode = true
        scan_project_containers
        purge_empty_groups(project_roots)
        @report
      end

      private

      def normalize_options(opts)
        {
          tiny_edges: option_enabled?(opts, 'tiny_edges', true),
          tiny_faces: option_enabled?(opts, 'tiny_faces', true),
          coplanar_merge: option_enabled?(opts, 'coplanar_merge', true),
          duplicate_faces: option_enabled?(opts, 'duplicate_faces', true),
          duplicate_instances: option_enabled?(opts, 'duplicate_instances', true),
          normal_repair: option_enabled?(opts, 'normal_repair', true),
          alignment_repair: option_enabled?(opts, 'alignment_repair', false),
          opening_repair: option_enabled?(opts, 'opening_repair', true),
          tiny_edge_mm: numeric_option(opts, 'tiny_edge_mm', DEFAULT_TINY_EDGE_MM),
          tiny_face_mm2: numeric_option(opts, 'tiny_face_mm2', DEFAULT_TINY_FACE_MM2),
          grid_mm: numeric_option(opts, 'grid_mm', DEFAULT_GRID_MM),
          vertex_tolerance_mm: numeric_option(opts, 'vertex_tolerance_mm', DEFAULT_VERTEX_TOLERANCE_MM),
          expected_openings: Integer(opts['expected_openings'] || opts[:expected_openings] || 0)
        }
      end

      def option_enabled?(opts, key, default)
        value = opts[key] || opts[key.to_sym]
        return default if value.nil?

        value == true || value == 'true' || value == 'on' || value == 1 || value == '1'
      end

      def numeric_option(opts, key, default)
        raw = opts[key] || opts[key.to_sym]
        return default if raw.nil?

        Float(raw)
      end

      def scan_project_containers
        roots = project_roots
        if roots.empty?
          @report['issues_after']['no_geomora_project'] = 1
          return
        end

        roots.each do |root|
          collect_entity_sets(root).each do |entities|
            process_entities(entities)
          end
        end
      end

      def project_roots
        @model.active_entities.grep(Sketchup::Group).select do |group|
          Metadata::Attributes.read(group, 'entity_type') == 'project' &&
            (@project_id.nil? || Metadata::Attributes.project_id(group) == @project_id)
        end
      end

      def collect_entity_sets(root)
        sets = []
        walk_container(root, sets)
        sets
      end

      def walk_container(entity, sets)
        if entity.is_a?(Sketchup::Group)
          sets << entity.entities
          entity.entities.each { |child| walk_container(child, sets) }
        elsif entity.is_a?(Sketchup::ComponentInstance)
          sets << entity.definition.entities
          entity.definition.entities.each { |child| walk_container(child, sets) }
        end
      end

      def process_entities(entities)
        issues = audit_entities(entities)
        @report['issues_before'].merge!(issues) { |_k, a, b| a + b }

        if @repair_mode
          delta = repair_entities(entities)
          merge_report(@report, delta)
        end

        after_issues = audit_entities(entities)
        @report['issues_after'].merge!(after_issues) { |_k, a, b| a + b }
        tally_components(entities)
      end

      def audit_entities(entities)
        tiny_edge_threshold = Geometry::Units.mm_to_length(@options[:tiny_edge_mm])
        tiny_face_threshold = @options[:tiny_face_mm2] * SQ_INCHES_PER_SQ_MM
        tolerance = @options[:vertex_tolerance_mm]

        issues = {
          'tiny_edges' => 0,
          'tiny_faces' => 0,
          'coplanar_edges' => 0,
          'duplicate_faces' => 0,
          'duplicate_instances' => 0,
          'inverted_faces' => 0,
          'misaligned_vertices' => 0,
          'opening_gaps' => 0
        }

        edges = entities.grep(Sketchup::Edge)
        faces = entities.grep(Sketchup::Face)

        issues['tiny_edges'] = edges.count { |e| e.valid? && e.length < tiny_edge_threshold }
        issues['tiny_faces'] = faces.count { |f| f.valid? && f.area < tiny_face_threshold }

        issues['coplanar_edges'] = edges.count do |edge|
          edge.valid? && edge.faces.length == 2 && coplanar_faces?(edge.faces[0], edge.faces[1])
        end

        signatures = Hash.new(0)
        faces.each do |face|
          next unless face.valid?

          sig = face_vertex_signature(face.vertices.map { |v| vertex_coords(v) }, tolerance_mm: tolerance)
          signatures[sig] += 1
        end
        issues['duplicate_faces'] = signatures.values.sum { |count| count > 1 ? count - 1 : 0 }

        issues['duplicate_instances'] = duplicate_instance_count(entities)

        center = entities.bounds.center
        issues['inverted_faces'] = faces.count do |face|
          next false unless face.valid?

          inverted_face?(face, center)
        end

        grid = Geometry::Units.mm_to_length(@options[:grid_mm])
        issues['misaligned_vertices'] = misaligned_vertex_count(entities, grid)

        issues['opening_gaps'] = opening_gap_count(entities)

        issues
      end

      def repair_entities(entities)
        delta = {
          'tiny_edges_removed' => 0,
          'tiny_faces_removed' => 0,
          'coplanar_edges_merged' => 0,
          'duplicate_faces_removed' => 0,
          'duplicate_instances_removed' => 0,
          'normals_reversed' => 0,
          'vertices_snapped' => 0,
          'opening_gaps_found' => 0
        }

        if @options[:duplicate_instances]
          delta['duplicate_instances_removed'] = remove_duplicate_instances(entities)
        end

        if @options[:duplicate_faces]
          delta['duplicate_faces_removed'] = remove_duplicate_faces(entities)
        end

        if @options[:coplanar_merge]
          delta['coplanar_edges_merged'] = merge_coplanar_faces(entities)
        end

        if @options[:tiny_faces]
          delta['tiny_faces_removed'] = remove_tiny_faces(entities)
        end

        if @options[:tiny_edges]
          delta['tiny_edges_removed'] = remove_tiny_edges(entities)
        end

        if @options[:alignment_repair]
          delta['vertices_snapped'] = snap_vertices_to_grid(entities)
        end

        if @options[:normal_repair]
          delta['normals_reversed'] = repair_face_normals(entities)
        end

        if @options[:opening_repair]
          delta['opening_gaps_found'] = report_opening_gaps(entities)
        end

        delta
      end

      def tally_components(entities)
        entities.each do |entity|
          next unless entity.is_a?(Sketchup::Group) || entity.is_a?(Sketchup::ComponentInstance)

          type = Metadata::Attributes.read(entity, 'entity_type')
          next if type.nil?

          @report['components'][type] = @report['components'].fetch(type, 0) + 1
        end
      end

      def remove_tiny_edges(entities)
        threshold = Geometry::Units.mm_to_length(@options[:tiny_edge_mm])
        removed = 0
        entities.grep(Sketchup::Edge).each do |edge|
          next unless edge.valid?
          next unless edge.length < threshold

          begin
            edge.erase!
            removed += 1
          rescue StandardError
            # locked or structural edge
          end
        end
        removed
      end

      def remove_tiny_faces(entities)
        threshold = @options[:tiny_face_mm2] * SQ_INCHES_PER_SQ_MM
        removed = 0
        entities.grep(Sketchup::Face).each do |face|
          next unless face.valid?
          next unless face.area < threshold

          begin
            face.erase!
            removed += 1
          rescue StandardError
            # face may be protected
          end
        end
        removed
      end

      def merge_coplanar_faces(entities)
        merged = 0
        entities.grep(Sketchup::Edge).each do |edge|
          next unless edge.valid?
          next unless edge.faces.length == 2

          face_a, face_b = edge.faces
          next unless coplanar_faces?(face_a, face_b)

          begin
            edge.erase!
            merged += 1
          rescue StandardError
            # skip welded edges
          end
        end
        merged
      end

      def remove_duplicate_faces(entities)
        tolerance = @options[:vertex_tolerance_mm]
        removed = 0
        signatures = {}

        entities.grep(Sketchup::Face).each do |face|
          next unless face.valid?

          coords = face.vertices.map { |v| vertex_coords(v) }
          sig = face_vertex_signature(coords, tolerance_mm: tolerance)
          if signatures.key?(sig)
            begin
              face.erase!
              removed += 1
            rescue StandardError
              # skip
            end
          else
            signatures[sig] = true
          end
        end
        removed
      end

      def remove_duplicate_instances(entities)
        tolerance = @options[:vertex_tolerance_mm]
        removed = 0
        seen = {}

        entities.grep(Sketchup::ComponentInstance).each do |inst|
          next unless inst.valid?

          key = instance_signature(inst, tolerance)
          if seen.key?(key)
            begin
              inst.erase!
              removed += 1
            rescue StandardError
              # skip
            end
          else
            seen[key] = true
          end
        end
        removed
      end

      def snap_vertices_to_grid(entities)
        grid = Geometry::Units.mm_to_length(@options[:grid_mm])
        snapped = 0
        vertices = entities.grep(Sketchup::Edge).flat_map(&:vertices).uniq

        vertices.each do |vertex|
          next unless vertex.valid?

          pt = vertex.position
          nx = snap_coord(pt.x, grid)
          ny = snap_coord(pt.y, grid)
          nz = snap_coord(pt.z, grid)
          next if nx == pt.x && ny == pt.y && nz == pt.z

          vertex.position = Geom::Point3d.new(nx, ny, nz)
          snapped += 1
        end
        snapped
      end

      def repair_face_normals(entities)
        reversed = 0
        center = entities.bounds.center

        entities.grep(Sketchup::Face).each do |face|
          next unless face.valid?
          next unless inverted_face?(face, center)

          face.reverse!
          reversed += 1
        end
        reversed
      end

      def report_opening_gaps(entities)
        gaps = opening_gap_count(entities)
        return 0 unless gaps.positive? && @options[:expected_openings].positive?

        gaps
      end

      def opening_gap_count(entities)
        wall_groups = entities.grep(Sketchup::Group).select do |group|
          Metadata::Attributes.read(group, 'entity_type') == 'wall'
        end

        wall_groups.count do |wall|
          face_count = wall.entities.grep(Sketchup::Face).count { |f| f.valid? }
          opening_loops = wall.entities.grep(Sketchup::Face).sum { |f| f.loops.length - 1 }
          face_count <= 6 && opening_loops.zero?
        end
      end

      def duplicate_instance_count(entities)
        tolerance = @options[:vertex_tolerance_mm]
        seen = {}
        duplicates = 0

        entities.grep(Sketchup::ComponentInstance).each do |inst|
          next unless inst.valid?

          key = instance_signature(inst, tolerance)
          if seen.key?(key)
            duplicates += 1
          else
            seen[key] = true
          end
        end
        duplicates
      end

      def misaligned_vertex_count(entities, grid)
        return 0 if grid.zero?

        vertices = entities.grep(Sketchup::Edge).flat_map(&:vertices).uniq
        vertices.count do |vertex|
          next false unless vertex.valid?

          pt = vertex.position
          snap_coord(pt.x, grid) != pt.x ||
            snap_coord(pt.y, grid) != pt.y ||
            snap_coord(pt.z, grid) != pt.z
        end
      end

      def purge_empty_groups(roots)
        removed = 0
        roots.each do |root|
          removed += purge_empty_in(root.entities)
        end
        @report['empty_groups_removed'] += removed
        removed
      end

      def purge_empty_in(entities)
        removed = 0
        entities.grep(Sketchup::Group).each do |group|
          removed += purge_empty_in(group.entities)
          if group.entities.grep(Sketchup::Face).empty? && group.entities.grep(Sketchup::Edge).empty?
            begin
              group.erase!
              removed += 1
            rescue StandardError
              # skip
            end
          end
        end
        removed
      end

      def coplanar_faces?(face_a, face_b)
        return false unless face_a.valid? && face_b.valid?

        normal_a = face_a.normal
        normal_b = face_b.normal
        return false unless normal_a.parallel?(normal_b)

        plane = face_a.plane
        face_b.vertices.all? { |v| v.position.on_plane?(plane) }
      end

      def inverted_face?(face, center)
        face_center = face.bounds.center
        outward = Geom::Vector3d.new(
          face_center.x - center.x,
          face_center.y - center.y,
          face_center.z - center.z
        )
        return false if outward.length.zero?

        face.normal % outward < 0.0
      end

      def vertex_coords(vertex)
        pt = vertex.position
        mm = INCHES_PER_MM
        [pt.x / mm, pt.y / mm, pt.z / mm]
      end

      def instance_signature(inst, tolerance_mm)
        origin = inst.transformation.origin
        mm = INCHES_PER_MM
        origin_key = vertex_key([origin.x / mm, origin.y / mm, origin.z / mm], tolerance_mm: tolerance_mm)
        [inst.definition.name, origin_key]
      end
    end
  end
  end
end
