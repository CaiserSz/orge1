# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.1] - 2025-12-15

### Fixed
- PAUSED → CHARGING “resume” bounce durumlarında yalancı `CHARGE_STARTED`/resume kayıtlarını engellemek için meter power + debounce doğrulaması eklendi.

## [1.8.0] - 2025-12-09

### Added
- API Authentication implementation (`api/auth.py`)
- API Test Web Page (`api_test.html`) with modern responsive UI
- cURL command preview feature (editable before sending)
- Security audit and quick wins implementation
- Shell escape function for command injection protection
- Environment control (production/development) for test endpoints
- Debounce optimization (300ms) for curl preview updates
- Input validation enhancement (amperage 6-32A)
- User-friendly error messages

### Changed
- Security score improved: 6/10 → 8/10
- API test endpoint disabled in production (`ENVIRONMENT` check)
- Error handling improved with user-friendly messages

### Security
- API key exposure risk fixed (environment control)
- Shell command injection protection added
- Production security controls implemented

### Documentation
- Comprehensive documentation updates (project_info, checkpoint, project_state)
- Audit reports added (AUDIT_REPORT_20251209.md, DOCUMENTATION_UPDATE_AUDIT_20251209.md)
- Git and GitHub improvement plan added

## [1.7.0] - 2025-12-09

### Added
- Multi-expert deep dive analysis (6 expert perspectives)
- Single source of truth strategy implementation
- Consolidated recommendations and action plan

### Documentation
- MULTI_EXPERT_ANALYSIS.md referenced
- Expert scores and targets documented

## [1.6.0] - 2025-12-09

### Added
- Structured logging system (JSON format, log rotation, thread-safe)
- Critical fixes (singleton pattern, dependency injection, exception handling)
- Test infrastructure (pytest, 8 test files, ~70% coverage)

### Documentation
- LOGGING_AUDIT.md and PRE_LOGGING_AUDIT.md referenced

## [1.5.0] - 2025-12-09

### Added
- Documentation consolidation
- Charging Process Deep Dive Analysis
- State Logic Analysis and fixes
- ESP32 Logging and Session Management evaluation
- WiFi Failover System information
- API Commands and usage

### Changed
- All analysis and evaluation documents integrated into project_info

## [1.4.3] - 2025-12-08

### Added
- WiFi troubleshooting documentation (`WIFI_TROUBLESHOOTING.md`)
- System information updates: Debian 13 (Trixie), RPi Lite değil

## [1.4.2] - 2025-12-08

### Added
- Todo system (`todo/` folder)
- Project management files

## [1.4.1] - 2025-12-08

### Added
- Station management endpoints
- Station info form (`station_form.html`)

## [1.4.0] - 2025-12-08

### Added
- REST API implementation (FastAPI)
- 7 API endpoints
- ESP32-RPi bridge module
- Ngrok configuration

## [1.3.9] - 2025-12-08

### Added
- Ngrok configuration completed

## [1.3.8] - 2025-12-08

### Changed
- API endpoint updates

## [1.3.7] - 2025-12-08

### Added
- Git repository setup
- GitHub integration

## [1.3.6] - 2025-12-08

### Added
- Initial project structure

## [1.3.5] - 2025-12-08

### Added
- Ngrok configuration and external access

## [1.3.4] - 2025-12-08

### Added
- Ngrok configuration

## [1.3.3] - 2025-12-08

### Added
- Initial ESP32 communication

## [1.3.2] - 2025-12-08

### Added
- ESP32 protocol definitions

## [1.3.1] - 2025-12-08

### Added
- ESP32 bridge module

## [1.3.0] - 2025-12-08

### Added
- System architecture and task distribution
- OCPP support planning
- API development planning

## [1.2.2] - 2025-12-08

### Added
- API and endpoint planning

## [1.2.1] - 2025-12-08

### Added
- Initial system information

## [1.2.0] - 2025-12-08

### Added
- System architecture documentation
- Task distribution planning

## [1.1.2] - 2025-12-08

### Added
- ESP32 development tools information

## [1.1.1] - 2025-12-08

### Added
- ESP32 status information

## [1.1.0] - 2025-12-08

### Added
- ESP32 status information

## [1.0.9] - 2025-12-08

### Added
- ESP32-RPi communication protocol

## [1.0.8] - 2025-12-08

### Added
- Working principles documentation

## [1.0.7] - 2025-12-08

### Added
- Working directory and restrictions

## [1.0.6] - 2025-12-08

### Added
- Git setup and initial push

## [1.0.5] - 2025-12-08

### Added
- Version control and repository setup

## [1.0.4] - 2025-12-08

### Added
- ESP32 development tools

## [1.0.3] - 2025-12-08

### Added
- Development environment information

## [1.0.2] - 2025-12-08

### Added
- Critical files documentation

## [1.0.1] - 2025-12-08

### Added
- Initial project information

## [1.0.0] - 2025-12-08

### Added
- Initial project creation
- Project information file
- File structure and format

---

[Unreleased]: https://github.com/CaiserSz/orge1/compare/v1.8.0...HEAD
[1.8.0]: https://github.com/CaiserSz/orge1/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/CaiserSz/orge1/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/CaiserSz/orge1/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/CaiserSz/orge1/compare/v1.4.3...v1.5.0

