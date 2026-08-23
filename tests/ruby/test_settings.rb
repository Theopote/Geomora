# frozen_string_literal: true

require 'minitest/autorun'
require_relative '../../plugin/geomora/core/settings'

class SettingsTest < Minitest::Test
  def test_sanitize_keeps_only_supported_non_secret_values
    result = Geomora::Core::Settings.sanitize(
      'routing_mode' => 'cloud_enhanced', 'vlm_provider' => 'gemini',
      'vlm_model' => 'gemini-2.5-pro', 'cloud_upload_confirm' => false,
      'api_key' => 'must-not-be-stored'
    )
    assert_equal 'cloud_enhanced', result['routing_mode']
    assert_equal 'gemini', result['vlm_provider']
    assert_equal false, result['cloud_upload_confirm']
    refute result.key?('api_key')
  end

  def test_invalid_enums_fall_back_to_defaults
    result = Geomora::Core::Settings.sanitize('routing_mode' => 'unsafe', 'onnx_device' => 'magic')
    assert_equal 'automatic', result['routing_mode']
    assert_equal 'auto', result['onnx_device']
  end
end
