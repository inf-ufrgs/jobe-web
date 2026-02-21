# Changelog

All notable changes to this project will be documented in this file.

## [1.9] - 2026-02-20

### Added
- **Visual Colored Diff**: Integrated `diff2html` to display a side-by-side, visually colored diff of expected vs. actual output for student submissions, making debugging easier.
- **Background Repository Sync**: The grader application now autonomously detects new commits to the assignments git repository and updates itself periodically in the background.

### Fixed
- **Assignment Page Header**: Fixed the layout issues in the header of the assignments page.
- **Submission Raw Logs**: Hidden the raw execution logs by default on the results page, adding a toggle button to reveal them only when needed for a cleaner interface.
