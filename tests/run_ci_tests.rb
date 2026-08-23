# frozen_string_literal: true

# Required, SketchUp-free reconstruction contracts. The full historical suite
# remains visible in a non-blocking CI debt job until its existing failures are
# repaired and migrated here.
FILES = %w[
  ir/validator_test.rb
  ir/rationalizer_test.rb
  core/constraint_solver_test.rb
  core/perpendicular_constraint_solver_test.rb
  core/structural_constraint_solver_test.rb
  core/detection_mapper_test.rb
  core/scale_estimator_test.rb
  core/structural_grid_test.rb
  core/geometry_doctor_test.rb
  core/workspace_selection_sync_test.rb
  generators/opening_evidence_test.rb
  generators/opening_generator_test.rb
  ruby/test_settings.rb
].freeze

FILES.each { |file| require File.join(__dir__, file) }
