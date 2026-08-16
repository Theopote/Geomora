# frozen_string_literal: true

require_relative '../test_helper'

class GeometryDoctorHelpersTest < Minitest::Test
  def test_snap_coord_rounds_to_grid
    grid = Geomora::Geometry::Units.mm_to_length(10.0)
    snapped = Geomora::Core::GeometryDoctor::Helpers.snap_coord(0.37, grid)
    assert_in_delta 0.3937, snapped, 0.001
  end

  def test_face_vertex_signature_is_order_independent
    tolerance = 0.5
    vertices = [
      [100.0, 0.0, 0.0],
      [100.0, 3000.0, 0.0],
      [0.0, 3000.0, 0.0],
      [0.0, 0.0, 0.0]
    ]
    reversed = vertices.reverse

    sig_a = Geomora::Core::GeometryDoctor::Helpers.face_vertex_signature(vertices, tolerance_mm: tolerance)
    sig_b = Geomora::Core::GeometryDoctor::Helpers.face_vertex_signature(reversed, tolerance_mm: tolerance)

    assert_equal sig_a, sig_b
  end

  def test_plane_key_groups_coplanar_points
    normal = [0.0, 0.0, 1.0]
    point_a = [0.0, 0.0, 100.0]
    point_b = [500.0, 200.0, 100.2]

    key_a = Geomora::Core::GeometryDoctor::Helpers.plane_key(normal, point_a)
    key_b = Geomora::Core::GeometryDoctor::Helpers.plane_key(normal, point_b)

    assert_equal key_a, key_b
  end

  def test_empty_report_structure
    report = Geomora::Core::GeometryDoctor::Helpers.empty_report

    assert_equal 0, report['tiny_edges_removed']
    assert_equal({}, report['components'])
    assert_equal({}, report['issues_before'])
  end

  def test_merge_report_accumulates_counters
    report = Geomora::Core::GeometryDoctor::Helpers.empty_report
    delta = {
      'tiny_edges_removed' => 2,
      'components' => { 'wall' => 1 }
    }

    Geomora::Core::GeometryDoctor::Helpers.merge_report(report, delta)

    assert_equal 2, report['tiny_edges_removed']
    assert_equal 1, report['components']['wall']
  end
end
