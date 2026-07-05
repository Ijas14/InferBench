import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from inferbench.cli import safe_join, main

def test_safe_join_prevents_path_traversal():
    """
    Tests that safe_join raises a ValueError if the resolved path escapes
    the base directory (path traversal attempt).
    """
    base_dir = "/tmp/safe_base"
    
    # Normal subdirectories should be fine
    with patch('os.path.abspath', side_effect=lambda x: x), patch('os.path.realpath', side_effect=lambda x: x):
        result = safe_join(base_dir, "results/")
        assert result == "/tmp/safe_base/results/"
        
    # Traversal should raise ValueError
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_join(base_dir, "../../../etc/passwd")

@patch('sys.exit')
@patch('inferbench.cli.OpenAIAdapter')
@patch('inferbench.cli.argparse.ArgumentParser.parse_args')
@patch('inferbench.cli.get_default_config')
@patch('time.time')
@patch('time.sleep')
def test_cli_health_check_timeout(mock_sleep, mock_time, mock_get_config, mock_parse_args, mock_adapter_class, mock_sys_exit, tmp_path):
    """
    Tests that the CLI main loop correctly times out and calls sys.exit(1)
    if the inference server never becomes healthy.
    """
    # Mock CLI arguments
    mock_args = MagicMock()
    mock_args.command = "run"
    mock_args.config = None
    mock_args.target = "http://localhost:8000/v1"
    mock_args.model = "test"
    mock_parse_args.return_value = mock_args
    
    # Mock config to avoid loading real files
    mock_config = MagicMock()
    mock_config.target.endpoint = "http://localhost:8000/v1"
    mock_get_config.return_value = mock_config
    
    # Mock adapter to always return unhealthy
    mock_adapter = MagicMock()
    mock_adapter.health.return_value = False
    mock_adapter_class.return_value = mock_adapter
    
    # We need time.time() to simulate the passing of time so the while loop terminates
    # The deadline is 600 seconds. We'll return 0 on the first call (setting deadline to 600),
    # then 0 again for the loop check, then 601 to trigger the timeout.
    mock_time.side_effect = [0, 0, 601]
    
    main()
    
    # The server was never healthy and time exceeded the deadline, so it should abort
    mock_sys_exit.assert_called_once_with(1)
    
@patch('inferbench.cli.execute_standard_workload')
@patch('inferbench.cli.OpenAIAdapter')
@patch('inferbench.cli.argparse.ArgumentParser.parse_args')
@patch('inferbench.cli.get_default_config')
@patch('time.time')
@patch('inferbench.cli.os.makedirs')
@patch('inferbench.cli.get_hardware_fingerprint')
def test_cli_execution_loop(mock_fp, mock_makedirs, mock_time, mock_get_config, mock_parse_args, mock_adapter_class, mock_exec_standard):
    """
    Tests that the CLI executes the standard workload when health check passes.
    """
    mock_args = MagicMock()
    mock_args.command = "run"
    mock_args.config = None
    mock_args.target = "http://localhost:8000/v1"
    mock_args.model = "test"
    mock_parse_args.return_value = mock_args
    
    mock_config = MagicMock()
    mock_config.target.endpoint = "http://localhost:8000/v1"
    mock_config.workloads = ["single_long"]
    mock_config.output.formats = []
    mock_config.output.dir = "results"
    mock_get_config.return_value = mock_config
    
    mock_adapter = MagicMock()
    mock_adapter.health.return_value = True # Healthy immediately
    mock_adapter.get_max_model_len.return_value = 32000
    mock_adapter_class.return_value = mock_adapter
    
    mock_time.return_value = 0
    mock_fp.return_value = {}
    
    with patch('inferbench.cli.safe_join', return_value="/tmp/safe"):
        main()
        
    mock_exec_standard.assert_called_once()
