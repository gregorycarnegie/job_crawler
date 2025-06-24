REM Move core files
move main.py src\claude_job_agent\main.py

REM Move monitoring files  
move health_checker.py src\claude_job_agent\monitoring\health_checker.py
move performance_monitor.py src\claude_job_agent\monitoring\performance_monitor.py
move backup_manager.py src\claude_job_agent\monitoring\backup_manager.py
move monitoring_service.py src\claude_job_agent\monitoring\monitoring_service.py
move monitoring_config.py src\claude_job_agent\monitoring\config.py

REM Move test files
move test_main.py tests\test_main.py
move test_monitor.py tests\test_monitoring.py
move run_tests.py scripts\run_tests.py

REM Move scripts
move monitor.py scripts\monitor.py